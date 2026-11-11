from __future__ import annotations

from ..schemas import EvidenceRef
from .kb import KnowledgeBase


def make_evidence_fn(kb: KnowledgeBase):
    """Adapter: AuditEngine evidence callback backed by the knowledge base."""
    def fn(code: str, supplier_id: str | None, product_code: str | None, ctx: dict) -> list[EvidenceRef]:
        return kb.evidence_for(code, supplier_id, product_code, product_desc=ctx.get("product_desc"), category=ctx.get("category"), agreement_id=ctx.get("agreement_id"))
    return fn
