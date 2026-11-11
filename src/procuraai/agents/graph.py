"""LangGraph workflow: ingest -> evidence -> audit -> (conditional) human_review -> report.

Shared state is ``AuditState``. Each node is wrapped for error handling: on an exception the error is recorded and the graph
routes to the report node so the caller always receives a (possibly partial) report. ``human_review`` only builds the review
queue -- it triggers no external action and no payment decision. If LangGraph is unavailable a sequential orchestrator with the same
nodes and state contract is used.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from ..schemas import InvoiceAuditResult
from ..services import Services
from .agents import (AuditState, DocumentIntelligenceAgent, ProcurementEvidenceAgent, ReconciliationAuditAgent, ReportingReviewAgent)

log = logging.getLogger("procuraai.graph")

try:
    from langgraph.graph import END, StateGraph
    HAVE_LANGGRAPH = True
except Exception:  # noqa: BLE001
    HAVE_LANGGRAPH = False


def _safe(name: str, fn: Callable[[AuditState], dict]) -> Callable[[AuditState], dict]:
    def node(state: AuditState) -> dict:
        try:
            return fn(state)
        except Exception as e:  # noqa: BLE001 - recorded, never swallowed silently
            log.exception("node %s failed", name)
            return dict(errors=list(state.get("errors", [])) + [f"{name}: {type(e).__name__}: {e}"], status="failed")
    return node


def human_review_node(state: AuditState) -> dict:
    q = [dict(invoice_id=r.invoice_id, invoice_number=r.invoice_number, supplier=r.supplier_name, status=r.overall_status, source_file=r.source_file,
              reasons=r.unresolved_questions[:6] or [f.message for f in r.findings if f.status != "PASSED"][:3])
         for r in state.get("results", []) if r.human_review_status == "PENDING"]
    return dict(review_queue=q)


def route_after_ingest(state: AuditState) -> str:
    return "evidence" if state.get("invoices") and not state.get("status") == "failed" else "report"


def route_after_audit(state: AuditState) -> str:
    if state.get("status") == "failed":
        return "report"
    return "human_review" if any(r.human_review_status == "PENDING" for r in state.get("results", [])) else "report"


def build_graph(svc: Services):
    ing, evi, aud, rep = (DocumentIntelligenceAgent(svc), ProcurementEvidenceAgent(svc), ReconciliationAuditAgent(svc), ReportingReviewAgent(svc))
    nodes = dict(ingest=_safe("ingest", ing.run), evidence=_safe("evidence", evi.run), audit=_safe("audit", aud.run), human_review=_safe("human_review", human_review_node), report=_safe("report", rep.run))
    if not HAVE_LANGGRAPH:
        return None, nodes
    g = StateGraph(AuditState)
    for k, v in nodes.items():
        g.add_node(k, v)
    g.set_entry_point("ingest")
    g.add_conditional_edges("ingest", route_after_ingest, {"evidence": "evidence", "report": "report"})
    g.add_edge("evidence", "audit")
    g.add_conditional_edges("audit", route_after_audit, {"human_review": "human_review", "report": "report"})
    g.add_edge("human_review", "report")
    g.add_edge("report", END)
    return g.compile(), nodes


def run_audit(svc: Services, input_mode: str = "documents", paths: list[str] | None = None, structured_dir: str | None = None, extraction_mode: str = "rule",
              outdir: str | None = None, workdir: str | None = None, use_llm_explanations: bool = False, audit_id: str | None = None, use_langgraph: bool = True) -> AuditState:
    state: AuditState = dict(audit_id=audit_id or f"AUD-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}", input_mode=input_mode, extraction_mode=extraction_mode, paths=[str(p) for p in (paths or [])],
                             structured_dir=structured_dir or str(svc.data_dir / "structured") if svc.data_dir else structured_dir, workdir=workdir or "processed/unzipped", outdir=outdir or "", use_llm_explanations=use_llm_explanations,
                             errors=[], timings={}, status="running")
    t0 = time.time()
    graph, nodes = build_graph(svc)
    if graph is not None and use_langgraph:
        final = graph.invoke(state)
    else:                                              # sequential fallback with identical node contract
        final = dict(state)
        order = ["ingest"]
        final.update(nodes["ingest"](final))
        if route_after_ingest(final) == "evidence":
            final.update(nodes["evidence"](final)); final.update(nodes["audit"](final))
            if route_after_audit(final) == "human_review":
                final.update(nodes["human_review"](final))
        final.update(nodes["report"](final))
    final["timings"] = dict(final.get("timings", {}), total_s=round(time.time() - t0, 3), orchestrator="langgraph" if (graph is not None and use_langgraph) else "sequential")
    if final.get("report"):
        final["report"]["metadata"]["timings"] = final["timings"]
    return final
