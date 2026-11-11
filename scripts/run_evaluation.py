#!/usr/bin/env python
"""Run the full labelled evaluation (structured path + document-extraction path + RAG) and write reports/evaluation/*."""
import argparse, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd

from procuraai import evaluation as E
from procuraai.agents import run_audit
from procuraai.extraction.structured import load_structured_dir
from procuraai.services import load_services


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="procuraai-data")
    ap.add_argument("--out", default="reports/evaluation")
    ap.add_argument("--skip-documents", action="store_true", help="skip the slow OCR/document path")
    a = ap.parse_args()
    data, out = Path(a.data), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    svc = load_services(data)
    gt = pd.read_csv(data / "ground_truth/ground_truth.csv")
    exp = pd.read_csv(data / "ground_truth/expected_values.csv")
    truth = load_structured_dir(data / "structured")
    report = {}
    # 1) structured path
    st = run_audit(svc, input_mode="structured", structured_dir=str(data / "structured"), outdir=str(out / "run_structured"))
    ev = E.evaluate_audit(st["results"], gt, exp)
    report["structured_path"] = {k: v for k, v in ev.items() if k != "code_confusion"}
    ev["code_confusion"].to_csv(out / "code_confusion_structured.csv")
    pd.DataFrame(ev["per_code"]).to_csv(out / "per_code_structured.csv", index=False)
    report["structured_path"]["citations"] = E.citation_integrity(st["results"], svc.kb)
    report["structured_path"]["timings"] = st["timings"]
    # 2) document path (OCR + extraction + audit on files)
    if not a.skip_documents:
        raw = data / "raw"
        paths = [str(p) for sub in ("invoices", "purchase_orders", "delivery_challans") for p in sorted((raw / sub).rglob("*.*"))]
        reg = data / "structured/document_registry.csv"
        paths.append(str(reg)) if reg.exists() else None
        t0 = time.time()
        sd = run_audit(svc, input_mode="documents", paths=paths, extraction_mode="rule", outdir=str(out / "run_documents"), workdir=str(out / "unzipped"))
        evd = E.evaluate_audit(sd["results"], gt, exp)
        report["document_path"] = {k: v for k, v in evd.items() if k != "code_confusion"}
        evd["code_confusion"].to_csv(out / "code_confusion_documents.csv")
        pd.DataFrame(evd["per_code"]).to_csv(out / "per_code_documents.csv", index=False)
        methods = {e["file"]: ("ocr" if "ocr" in str(e.get("text_method", "")) else "text-layer/plain") for e in sd["report"]["metadata"]["extraction_log"] if e.get("doc_type") == "INVOICE"}
        report["extraction_accuracy"] = E.evaluate_extraction(sd["invoices"], truth["invoices"], methods)
        log = [e for e in sd["report"]["metadata"]["extraction_log"] if "seconds" in e]
        tdf = pd.DataFrame(log)
        tdf["kind"] = tdf["text_method"].fillna("n/a").map(lambda s: "ocr" if "ocr" in s else "text-layer/plain")
        report["processing_time_per_document_s"] = {k: dict(mean=round(g.seconds.mean(), 3), max=round(g.seconds.max(), 3), n=int(len(g))) for k, g in tdf.groupby("kind")}
        report["document_path"]["wall_clock_s"] = round(time.time() - t0, 1)
        report["document_path"]["citations"] = E.citation_integrity(sd["results"], svc.kb)
        report["document_path"]["timings"] = sd["timings"]
        report["document_path"]["ingestion_errors"] = sd["ingestion_errors"]
    report["product_matching"] = E.evaluate_product_matching(svc.master.products, truth["invoices"])
    report["rag_retrieval"] = E.evaluate_rag(svc.kb, svc.master)
    report["api_usage"] = dict(llm_calls=0, note="No Gemini API key was configured in this run, so no LLM calls were made and no API cost was incurred.") if not svc.llm_available else svc.llm.usage
    (out / "evaluation_results.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps({k: (v if k in ("product_matching", "api_usage", "extraction_accuracy", "processing_time_per_document_s") else {x: y for x, y in v.items() if x in ("n_invoices", "tp", "fp", "fn", "precision", "recall", "f1", "invoice_level_confusion", "severity_agreement", "status_agreement", "exposure_invoices_within_1pkr", "exposure_mae", "low_confidence_invoices", "wall_clock_s")} if k.endswith("_path") else v) for k, v in report.items()}, indent=1, default=str))


if __name__ == "__main__":
    main()
