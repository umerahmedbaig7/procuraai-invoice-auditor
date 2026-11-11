import hashlib
import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from procuraai.agents.graph import HAVE_LANGGRAPH, run_audit
from procuraai.api.app import create_app
from procuraai.config import Settings
from procuraai.datagen.catalog import ELECTRICAL_PKR
from procuraai.datagen.export import DatasetIntegrityError, validate_dataset
from procuraai.datagen.generator import generate


@pytest.fixture()
def client(dataset_dir, tmp_path):
    s = Settings()
    s.data_dir, s.upload_dir, s.db_url, s.api_key = dataset_dir, tmp_path / "up", f"sqlite:///{tmp_path}/t.db", None
    return TestClient(create_app(s))


def test_17_api_returns_appropriate_errors(client, dataset_dir):
    assert client.get("/health").status_code == 200
    assert client.post("/documents/upload", files=[("files", ("x.exe", b"MZ"))]).status_code == 422
    assert client.post("/documents/upload", files=[("files", ("e.pdf", b""))]).status_code == 422
    assert client.post("/audits", json={"input_mode": "documents"}).status_code == 422
    assert client.post("/audits", json={"input_mode": "documents", "document_ids": ["nope"]}).status_code == 404
    assert client.post("/audits", json={"input_mode": "bogus"}).status_code == 422
    assert client.get("/audits/unknown").status_code == 404
    assert client.get("/audits/unknown/report").status_code == 404
    assert client.get("/knowledge-base/search").status_code == 422
    assert client.get("/knowledge-base/search?q=freight&supplier_id=bad").status_code == 422


def test_api_end_to_end_and_exports(client, dataset_dir):
    files = [("files", (p.name, p.read_bytes())) for p in sorted((dataset_dir / "raw/invoices/pdf").glob("INV-00[1-3]*")) + sorted((dataset_dir / "raw/purchase_orders/pdf").glob("PO-2025-000[1-3]*"))
             + sorted((dataset_dir / "raw/delivery_challans/pdf").glob("*-000[1-3]*"))]
    up = client.post("/documents/upload", files=files).json()
    r = client.post("/audits", json={"input_mode": "documents", "document_ids": [d["document_id"] for d in up["documents"]]})
    assert r.status_code == 202
    aid = r.json()["audit_id"]
    st = client.get(f"/audits/{aid}").json()
    assert st["status"] in ("completed", "completed_with_errors") and st["summary"]["invoices_processed"] >= 2
    assert client.get(f"/audits/{aid}/report").json()["audit_id"] == aid
    assert "# ProcuraAI Audit Report" in client.get(f"/audits/{aid}/report?format=markdown").text
    assert client.get(f"/audits/{aid}/report?format=xlsx").content[:2] == b"PK"
    assert client.get(f"/audits/{aid}/findings?severity=BAD").status_code == 422
    assert "uptime_s" in client.get("/metrics").json()
    assert client.get("/knowledge-base/search?q=tax rate cables").json()["results"][0]["source_file"].startswith("POL-")


def test_api_key_is_enforced_when_configured(dataset_dir, tmp_path):
    s = Settings(); s.data_dir, s.upload_dir, s.db_url, s.api_key = dataset_dir, tmp_path / "u", f"sqlite:///{tmp_path}/k.db", "dev-secret"
    c = TestClient(create_app(s))
    assert c.get("/health").status_code == 200
    assert c.get("/metrics").status_code == 401 and c.get("/metrics", headers={"X-API-Key": "wrong"}).status_code == 401
    assert c.get("/metrics", headers={"X-API-Key": "dev-secret"}).status_code == 200


def test_multi_agent_pipeline_end_to_end(services, dataset_dir, tmp_path):
    assert HAVE_LANGGRAPH
    st = run_audit(services, "structured", structured_dir=str(dataset_dir / "structured"), outdir=str(tmp_path / "out"))
    assert st["status"] == "completed" and st["timings"]["orchestrator"] == "langgraph"
    rep = st["report"]
    s = rep["summary"]
    assert s["invoices_processed"] == 72 and s["invoices_flagged"] > 20 and st["review_queue"]
    assert set(st["output_files"]) == {"json", "markdown", "findings_csv", "invoices_csv", "excel"} and all(Path(p).stat().st_size > 0 for p in st["output_files"].values())
    # sequential fallback gives the same answer
    st2 = run_audit(services, "structured", structured_dir=str(dataset_dir / "structured"), use_langgraph=False)
    assert st2["report"]["summary"]["estimated_exposure_total"] == s["estimated_exposure_total"]


def test_aggregate_exposure_is_not_double_counted(services, dataset_dir):
    st = run_audit(services, "structured", structured_dir=str(dataset_dir / "structured"))
    from decimal import Decimal
    total = sum(Decimal(i["total_exposure"]) for i in st["report"]["invoices"])
    assert Decimal(st["report"]["summary"]["estimated_exposure_total"]) == total
    naive = sum(Decimal(f["exposure_amount"]) for i in st["report"]["invoices"] for f in i["findings"] if f["status"] in ("CONFIRMED", "POTENTIAL"))
    assert total < naive


def test_pipeline_survives_a_node_failure(services, monkeypatch):
    from procuraai.agents import agents
    monkeypatch.setattr(agents.ReconciliationAuditAgent, "run", lambda self, state: (_ for _ in ()).throw(RuntimeError("boom")))
    st = run_audit(services, "structured")
    assert st["status"] == "completed_with_errors" or st["errors"]
    assert any("boom" in e for e in st["errors"]) and st["report"]["metadata"]["pipeline_errors"]


# ---------------------------------------------------------------- dataset
def test_dataset_is_reproducible_and_meets_requirements(ds):
    ds2 = generate(ELECTRICAL_PKR)
    h = lambda d: hashlib.sha256(json.dumps(d.gt, default=str, sort_keys=True).encode()).hexdigest()
    assert h(ds) == h(ds2)
    stats = validate_dataset(ds)
    assert stats["suppliers"] >= 8 and stats["purchase_orders"] >= 40 and stats["invoices"] >= 60 and stats["clean_invoices"] >= 20 and stats["anomalous_invoices"] >= 20
    scen = {g["scenario_no"] for g in ds.gt}
    assert set(range(1, 26)) <= scen


def test_dataset_integrity_check_fails_loudly_on_bad_reference(ds):
    import copy
    bad = copy.copy(ds)
    bad.invoices = [copy.deepcopy(i) for i in ds.invoices]
    clean = next(i for i in bad.invoices if ds.invoice_meta[i.invoice_id]["scenario_no"] == 1)
    clean.po_number = "PO-2025-9999"
    with pytest.raises(DatasetIntegrityError, match="MISSING_PO"):
        validate_dataset(bad)


def test_written_dataset_has_required_files(dataset_dir):
    for rel in ["structured/invoices.csv", "structured/purchase_orders.csv", "structured/delivery_challans.csv", "structured/supplier_master.csv", "structured/product_master.csv",
                "structured/supplier_price_list.csv", "structured/procurement_policies.csv", "structured/procurement_master_data.xlsx", "ground_truth/ground_truth.csv", "manifest/dataset_manifest.csv"]:
        assert (dataset_dir / rel).stat().st_size > 0, rel
    for d in ["raw/invoices/pdf", "raw/invoices/images", "raw/invoices/text", "raw/purchase_orders/pdf", "raw/purchase_orders/images", "raw/delivery_challans/pdf", "raw/delivery_challans/images", "raw/contracts", "raw/policies"]:
        assert any((dataset_dir / d).iterdir()), d
    assert len(list((dataset_dir / "raw/invoices/pdf").glob("*.pdf"))) >= 10
    assert len(list((dataset_dir / "raw/contracts").glob("*.pdf"))) == 8 and len(list((dataset_dir / "raw/policies").glob("*.pdf"))) == 5
    sheets = pd.ExcelFile(dataset_dir / "structured/procurement_master_data.xlsx").sheet_names
    assert {"Suppliers", "Products", "PriceList", "Invoice_Lines", "PO_Lines", "DC_Lines"} <= set(sheets)
    # ground truth is NOT inside the structured inputs or the workbook
    assert not any("anomal" in c.lower() or "expected" in c.lower() for c in pd.read_csv(dataset_dir / "structured/invoices.csv").columns)
    assert "ground_truth" not in " ".join(sheets).lower()


def test_storage_keeps_paths_not_file_contents(tmp_path):
    from procuraai.storage.db import DocumentRow, Store
    s = Store(f"sqlite:///{tmp_path}/s.db")
    p = tmp_path / "f.pdf"; p.write_bytes(b"%PDF-secret-contents")
    s.add_document("d1", "f.pdf", p, p.read_bytes())
    assert "secret" not in str({c.name for c in DocumentRow.__table__.columns}) and s.get_documents(["d1"])[0].size_bytes == 20
