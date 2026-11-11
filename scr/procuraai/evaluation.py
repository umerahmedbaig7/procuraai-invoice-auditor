"""Evaluation against the labelled ground truth. Ground truth is read here only -- never by agents or the engine."""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

import pandas as pd

from . import taxonomy as T
from .audit.money import to_decimal
from .normalization import ProductMatcher
from .rag.kb import KnowledgeBase
from .schemas import InvoiceAuditResult, InvoiceRecord

OPERATIONAL = {"EXTRACTION_LOW_CONFIDENCE"}
NON_INFO = {c for c, i in T.CODES.items() if i.severity != "INFO"}


def _prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


def evaluate_audit(results: list[InvoiceAuditResult], gt: pd.DataFrame, expected: pd.DataFrame) -> dict:
    G: dict[str, set] = defaultdict(set)
    gtrow: dict[tuple, dict] = {}
    for r in gt.to_dict("records"):
        if r["anomaly_code"] != "NONE":
            G[r["invoice_id"]].add(r["anomaly_code"])
            gtrow.setdefault((r["invoice_id"], r["anomaly_code"]), r)
    P: dict[str, set] = {}
    pf: dict[tuple, object] = {}
    for res in results:
        P[res.invoice_id] = {f.code for f in res.findings if f.code not in OPERATIONAL}
        for f in res.findings:
            pf.setdefault((res.invoice_id, f.code), f)
    ids = [r.invoice_id for r in results]
    tp = fp = fn = 0
    per = defaultdict(lambda: [0, 0, 0])
    fps, fns = [], []
    for i in ids:
        g, p = G.get(i, set()), P.get(i, set())
        for c in g & p: per[c][0] += 1
        for c in p - g: per[c][1] += 1; fps.append((i, c))
        for c in g - p: per[c][2] += 1; fns.append((i, c))
        tp += len(g & p); fp += len(p - g); fn += len(g - p)
    p_, r_, f_ = _prf(tp, fp, fn)
    byid = {r.invoice_id: r for r in results}
    fp_non_info = [(i, c) for i, c in fps if T.CODES[c].severity != "INFO"]
    fp_confirmed = [(i, c) for i, c in fps if pf[(i, c)].status == T.CONFIRMED]
    fp_hi_conf = [(i, c) for i, c in fp_non_info if byid[i].extraction_confidence >= 0.75]
    tp_i, fp_i, fn_i = tp, len(fp_non_info), fn
    p_ni, r_ni, f_ni = _prf(tp_i, fp_i, fn_i)
    per_code = []
    for c, (a, b, d) in sorted(per.items()):
        pp, rr, ff = _prf(a, b, d)
        per_code.append(dict(code=c, tp=a, fp=b, fn=d, precision=pp, recall=rr, f1=ff, scenario=T.CODES[c].category))
    # invoice-level binary confusion (anomalous = any non-INFO code)
    cm = Counter()
    for i in ids:
        ga = bool(G.get(i, set()) & NON_INFO)
        pa = any(f.status != T.PASSED and f.code not in OPERATIONAL for f in next(r for r in results if r.invoice_id == i).findings)
        cm[("anomalous" if ga else "clean", "flagged" if pa else "not_flagged")] += 1
    # code confusion (multi-label co-occurrence)
    codes = sorted({c for s in list(G.values()) + list(P.values()) for c in s}) + ["NONE"]
    mat = pd.DataFrame(0, index=codes, columns=codes)
    for i in ids:
        g = G.get(i, set()) or {"NONE"}
        p = P.get(i, set()) or {"NONE"}
        for a in g:
            for b in p:
                mat.loc[a, b] += 1
    # agreement on matched pairs
    sev_ok = stat_ok = line_ok = line_n = n_m = 0
    for (i, c), row in gtrow.items():
        f = pf.get((i, c))
        if f is None:
            continue
        n_m += 1
        sev_ok += row["severity"] == f.severity
        stat_ok += row["expected_status"] == f.status
        if pd.notna(row["line_no"]):
            line_n += 1
            line_ok += f.line_no == int(row["line_no"])
    # exposure
    ex = expected.set_index("invoice_id")["expected_exposure"].to_dict()
    ok_expo = 0
    abs_err = Decimal(0)
    exp_total = eng_total = Decimal(0)
    expo_bad = []
    for r in results:
        e = to_decimal(ex.get(r.invoice_id), Decimal(0))
        d = abs(e - r.total_exposure)
        abs_err += d
        exp_total += e
        eng_total += r.total_exposure
        if d <= Decimal("1.00"):
            ok_expo += 1
        else:
            expo_bad.append((r.invoice_id, str(e), str(r.total_exposure)))
    clean_ids = [i for i in ids if not G.get(i)]
    false_clean = sum(1 for i in clean_ids if any(c not in OPERATIONAL for c in P.get(i, set()) if c in NON_INFO or T.CODES[c].severity != "INFO"))
    return dict(n_invoices=len(ids), tp=tp, fp=fp, fn=fn, precision=p_, recall=r_, f1=f_, fp_non_info=len(fp_non_info), fp_info_only=len(fps) - len(fp_non_info), fp_status_confirmed=len(fp_confirmed),
                fp_non_info_on_high_confidence_invoices=len(fp_hi_conf), precision_excl_info_fp=p_ni, f1_excl_info_fp=f_ni, per_code=per_code, invoice_level_confusion={f"{a}->{b}": v for (a, b), v in cm.items()},
                code_confusion=mat, false_positives=fps, false_negatives=fns, severity_agreement=round(sev_ok / n_m, 4) if n_m else None, status_agreement=round(stat_ok / n_m, 4) if n_m else None,
                line_attribution_accuracy=round(line_ok / line_n, 4) if line_n else None, exposure_invoices_within_1pkr=ok_expo, exposure_mae=str((abs_err / max(1, len(results))).quantize(Decimal("0.01"))),
                exposure_expected_total=str(exp_total), exposure_engine_total=str(eng_total), exposure_mismatches=expo_bad, clean_invoices=len(clean_ids), clean_invoices_with_anomaly_labels=false_clean,
                low_confidence_invoices=sum(1 for r in results if r.extraction_confidence < 0.75))


def evaluate_extraction(extracted: list[InvoiceRecord], truth: list[InvoiceRecord], methods: dict[str, str]) -> dict:
    T_ = {t.source_file: t for t in truth}
    fields = ["invoice_number", "invoice_date", "supplier_name", "po_number", "dc_reference", "currency", "subtotal", "tax_total", "grand_total", "supplier_tax_id", "due_date", "payment_terms"]
    lf = ["product_code", "quantity", "unit_price", "discount_pct", "line_amount", "tax_rate", "tax_amount"]
    acc: dict = defaultdict(lambda: [0, 0])
    per_doc_ok = defaultdict(lambda: [0, 0])
    for e in extracted:
        t = T_.get(e.source_file)
        if not t:
            continue
        m = methods.get(e.source_file, "unknown")
        ok_doc = True
        for f in fields:
            a, b = getattr(e, f), getattr(t, f)
            acc[(m, f)][0] += a == b; acc[(m, f)][1] += 1
            ok_doc &= a == b
        for i, tl in enumerate(t.lines):
            el = e.lines[i] if i < len(e.lines) else None
            for f in lf:
                a = getattr(el, f) if el else None
                b = getattr(tl, f)
                acc[(m, "line." + f)][0] += a == b; acc[(m, "line." + f)][1] += 1
                ok_doc &= a == b
        ok_doc &= len(e.lines) == len(t.lines) and len(e.charges) == len(t.charges)
        per_doc_ok[m][0] += ok_doc; per_doc_ok[m][1] += 1
    out = {}
    for m in sorted({k[0] for k in acc}):
        n = sum(v[1] for k, v in acc.items() if k[0] == m)
        c = sum(v[0] for k, v in acc.items() if k[0] == m)
        out[m] = dict(field_accuracy=round(c / n, 4), documents=per_doc_ok[m][1], documents_fully_correct=per_doc_ok[m][0],
                      by_field={k[1]: round(v[0] / v[1], 4) for k, v in acc.items() if k[0] == m})
    return out


def evaluate_product_matching(products, truth: list[InvoiceRecord], cfg=None) -> dict:
    pm = ProductMatcher(products, cfg)
    n = ok_desc = rev_desc = wrong_desc = ok_full = 0
    wrong = []
    for inv in truth:
        for l in inv.lines:
            if not l.product_code or l.product_code not in pm.products:
                continue
            n += 1
            m = pm.match(None, l.description)                   # description only (code hidden)
            if m.matched_id == l.product_code and not m.needs_review:
                ok_desc += 1
            elif m.needs_review or m.matched_id is None:
                rev_desc += 1
            else:
                wrong_desc += 1
                wrong.append((inv.invoice_id, l.line_no, l.product_code, m.matched_id))
            mf = pm.match(l.product_code, l.description)
            ok_full += mf.matched_id == l.product_code and not mf.needs_review
    return dict(lines=n, description_only_correct=ok_desc, description_only_routed_to_review=rev_desc, description_only_wrong_auto_match=wrong_desc,
                description_only_accuracy=round(ok_desc / n, 4) if n else None, auto_match_precision=round(ok_desc / (ok_desc + wrong_desc), 4) if ok_desc + wrong_desc else None,
                code_plus_description_accuracy=round(ok_full / n, 4) if n else None, wrong=wrong[:10])


RAG_QA = [
    ("What tax rate applies to cables?", "POL-002.txt", "2.4"), ("What is the tax rate for lighting products?", "POL-002.txt", "2.2"),
    ("Must an invoice state tax per line?", "POL-002.txt", "2.7"), ("Is a missing delivery challan proof that goods were not delivered?", "POL-001.txt", "1.4"),
    ("How are partial deliveries treated in three-way matching?", "POL-001.txt", "1.3"), ("What is the quantity tolerance for invoices?", "POL-001.txt", "1.2"),
    ("When is an invoice an exact duplicate?", "POL-004.txt", "4.1"), ("Who may approve or release payments?", "POL-004.txt", "4.3"),
    ("Are fuel surcharges allowed?", "POL-003.txt", "3.3"), ("In what currency must invoices be issued?", "POL-003.txt", "3.4"),
    ("What happens with invoices from suppliers not in the master?", "POL-005.txt", "5.1"), ("Which agreement applies when the purchase order date is outside the term?", "POL-005.txt", "5.2"),
    ("What if a line matches several catalogue products?", "POL-005.txt", "5.5"), ("What if the received quantity exceeds the ordered quantity?", "POL-001.txt", "1.5"),
]


def evaluate_rag(kb: KnowledgeBase, master, ks=(1, 3, 5), seed: int = 7, n_price: int = 40) -> dict:
    rng = random.Random(seed)
    cases = []   # (query, supplier filter, predicate on chunk)
    for q, f, sec in RAG_QA:
        cases.append(("policy", q, None, lambda c, f=f, sec=sec: c.source_file == f and (c.section or "").endswith(sec)))
    for s in master.suppliers:
        sid = s.supplier_id
        ag = next(a for a in master.agreements if a.supplier_id == sid)
        cases.append(("contract_clause", "Is freight or any additional charge allowed under this agreement?", sid, lambda c, sid=sid: c.source_file == f"CONTRACT_{sid}.txt" and "Freight" in (c.section or "")))
        cases.append(("contract_clause", "Is a volume discount given for large ordered quantities?", sid, lambda c, sid=sid: c.source_file == f"CONTRACT_{sid}.txt" and "Discount" in (c.section or "")))
    pl = [e for e in master.price_list]
    for e in rng.sample(pl, min(n_price, len(pl))):
        p = master.product_by_code[e.product_code]
        cases.append(("price_row", f"contract price of {p.description}", e.supplier_id, lambda c, e=e: c.source_file == f"CONTRACT_{e.supplier_id}.txt" and e.product_code in c.text))
    out = {}
    for mode in ("dense", "keyword", "hybrid"):
        rec = {k: defaultdict(list) for k in ks}
        rr = defaultdict(list)
        for kind, q, sid, pred in cases:
            hits = kb.search(q, k=max(ks), mode=mode, supplier_id=sid)
            first = next((h.rank for h in hits if pred(h.chunk)), None)
            for k in ks:
                rec[k][kind].append(first is not None and first <= k)
            rr[kind].append(1 / first if first else 0.0)
        res = {}
        for kind in sorted({c[0] for c in cases}):
            res[kind] = {**{f"recall@{k}": round(sum(rec[k][kind]) / len(rec[k][kind]), 4) for k in ks}, "mrr": round(sum(rr[kind]) / len(rr[kind]), 4), "n": len(rec[ks[0]][kind])}
        allv = {k: [x for v in rec[k].values() for x in v] for k in ks}
        res["ALL"] = {**{f"recall@{k}": round(sum(allv[k]) / len(allv[k]), 4) for k in ks}, "mrr": round(sum(x for v in rr.values() for x in v) / sum(len(v) for v in rr.values()), 4), "n": len(cases)}
        out[mode] = res
    return out


def citation_integrity(results: list[InvoiceAuditResult], kb: KnowledgeBase) -> dict:
    n = ok = 0
    bad = []
    for r in results:
        for f in r.findings:
            for e in f.evidence:
                n += 1
                v = kb.verify_citation(e)
                ok += v
                if not v:
                    bad.append((r.invoice_id, f.code, e.source_file))
    with_ev = sum(1 for r in results for f in r.findings if f.status != T.PASSED and f.evidence)
    total = sum(1 for r in results for f in r.findings if f.status != T.PASSED)
    return dict(citations=n, verified=ok, invalid=bad[:5], findings_with_evidence=with_ev, findings_total=total)


def md_table(rows: list[dict], cols: list[str] | None = None) -> str:
    if not rows:
        return "_none_"
    cols = cols or list(rows[0])
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(out)
