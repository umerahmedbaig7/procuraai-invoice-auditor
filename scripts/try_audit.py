#!/usr/bin/env python
"""Run two example audits and print clear diagnostics.  Usage (from the project root):  python scripts/try_audit.py [--data procuraai-data]"""
import argparse, shutil, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ap = argparse.ArgumentParser()
ap.add_argument("--data", default=str(ROOT / "procuraai-data"))
ap.add_argument("--out", default=str(ROOT / "my_reports"))
a = ap.parse_args()
data, out = Path(a.data), Path(a.out)
print("project root:", ROOT, "\ndataset:", data, "| exists:", (data / "structured").exists())
if not (data / "structured").exists():
    sys.exit("Dataset not found. Generate it first:  python scripts/generate_synthetic_data.py --out procuraai-data")
print("tesseract on PATH:", shutil.which("tesseract") or "NOT FOUND (scanned/image documents cannot be read)")
try:
    from procuraai.services import load_services
    from procuraai.agents import run_audit
    svc = load_services(data)
    print("\n".join(svc.notes))
    st = run_audit(svc, "structured", structured_dir=str(data / "structured"), outdir=str(out / "structured"))
    print("A) structured:", st["status"], st["timings"], {k: v for k, v in st["report"]["summary"].items() if k.startswith(("invoices_", "estimated"))}, "\n   errors:", st.get("errors"))
    import re
    import pandas as pd
    raw = data / "raw"
    inv_tbl = pd.read_csv(data / "structured/invoices.csv", dtype=str, keep_default_na=False).drop_duplicates("invoice_id")
    chosen = inv_tbl.head(4)                                    # first 4 invoices
    paths = []
    for _, r in chosen.iterrows():
        refs = [r["po_number"]] + [x.strip() for x in re.split(r"[,;]", r["dc_reference"]) if x.strip()]
        paths += [str(f) for f in (raw / "invoices").rglob(r["source_file"])]
        for sub in ("purchase_orders", "delivery_challans"):
            paths += [str(f) for f in (raw / sub).rglob("*.*") if f.stem in refs]          # the invoice's OWN PO and delivery documents
    paths = sorted(set(paths))
    print("B) documents:", len(paths), "files")
    st2 = run_audit(svc, "documents", paths=paths, extraction_mode="rule", outdir=str(out / "documents"), workdir=str(out / "unz"))
    print("   ", st2["status"], "| errors:", st2.get("errors"), "| ingestion errors:", st2.get("ingestion_errors"))
    print("   ", len(st2["report"]["invoices"]), "invoices;", st2["report"]["summary"]["findings_by_code"])
    print("\nReports written under:", out)
except Exception:
    print("\n=== FAILED - copy everything below this line when asking for help ===")
    traceback.print_exc()
    sys.exit(1)
