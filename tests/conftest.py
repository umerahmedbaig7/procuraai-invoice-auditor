import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from procuraai.audit.engine import AuditEngine, DocumentStore, MasterData  # noqa: E402
from procuraai.datagen.catalog import ELECTRICAL_PKR, POLICY_DOCS  # noqa: E402
from procuraai.datagen.export import write_dataset  # noqa: E402
from procuraai.datagen.generator import generate  # noqa: E402
from procuraai.schemas import PolicyRule  # noqa: E402


@pytest.fixture(scope="session")
def ds():
    return generate(ELECTRICAL_PKR)


@pytest.fixture(scope="session")
def master(ds):
    pol = [PolicyRule(policy_id=p, rule_key=k, rule_value=v, text=t, source_file=f"{p}.txt") for p, (_, rows) in POLICY_DOCS.items() for _s, k, v, t in rows]
    return MasterData([s.info for s in ELECTRICAL_PKR.suppliers], ELECTRICAL_PKR.products, ds.agreements, ds.price_list, pol)


def new_engine(ds, master, **kw):
    return AuditEngine(master, DocumentStore.from_lists(ds.pos, ds.dcs), **kw)


@pytest.fixture(scope="session")
def results(ds, master):
    """Structured-path audit of the whole dataset (ground truth is used only by tests as an oracle)."""
    eng = new_engine(ds, master)
    return {r.invoice_id: r for r in eng.audit_batch([copy.deepcopy(i) for i in ds.invoices], "TEST")}


@pytest.fixture(scope="session")
def gt_codes(ds):
    out = {}
    for g in ds.gt:
        out.setdefault(g["invoice_id"], set()).add(g["anomaly_code"])
    return out


@pytest.fixture(scope="session")
def by_code(gt_codes):
    """invoice ids whose labels contain exactly one code (isolated scenarios) keyed by code."""
    d = {}
    for i, cs in gt_codes.items():
        if len(cs) == 1:
            d.setdefault(next(iter(cs)), []).append(i)
    return d


@pytest.fixture(scope="session")
def dataset_dir(ds, tmp_path_factory):
    root = tmp_path_factory.mktemp("data") / "procuraai-data"
    write_dataset(ds, root, make_zip=False)
    return root


@pytest.fixture(scope="session")
def services(dataset_dir):
    from procuraai.services import load_services
    return load_services(dataset_dir)


def codes(res, include_info=True):
    return {f.code for f in res.findings if include_info or f.severity != "INFO"}
