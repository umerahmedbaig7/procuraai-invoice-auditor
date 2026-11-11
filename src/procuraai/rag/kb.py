"""RAG knowledge base over supplier contracts, price lists and procurement policies.

Pipeline: load -> clean -> section-aware chunking (size/overlap configurable) -> embeddings -> FAISS index
(+ BM25 keyword index) -> dense / keyword / hybrid (reciprocal-rank-fusion) retrieval -> citations.

Embeddings: the default ``TfidfEmbedder`` runs fully offline (lexical baseline). ``SentenceTransformerEmbedder``
(local model, needs the model files from the Hugging Face hub on first use) can be selected with ``embedder=``.
Retrieved text is UNTRUSTED DATA: it is never executed or obeyed, only quoted as evidence.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from ..ingestion.loader import load_file
from ..schemas import EvidenceRef

INJECTION_PATTERNS = [r"ignore (all |any )?(previous|prior|above) (instructions|rules)", r"disregard (the )?(system|previous)", r"you are now", r"approve (this )?payment",
                      r"release (the )?payment", r"system prompt", r"<\s*/?\s*(system|assistant|untrusted_document)\s*>"]
_INJ = re.compile("|".join(INJECTION_PATTERNS), re.I)


def scan_untrusted(text: str) -> list[str]:
    """Return the instruction-like patterns found in a document (flagged, never obeyed)."""
    return sorted({m.group(0).lower() for m in _INJ.finditer(text)})


def clean_text(t: str) -> str:
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_file: str
    doc_type: str
    supplier_id: str | None = None
    section: str | None = None
    page: int | None = None
    flags: list[str] = field(default_factory=list)


@dataclass
class Hit:
    chunk: Chunk
    score: float
    rank: int
    method: str


# ---------------------------------------------------------------------------------------------
# chunking
# ---------------------------------------------------------------------------------------------
def _split_words(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if len(" ".join(words)) <= size:
        return [text]
    out, cur = [], []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) >= size:
            out.append(" ".join(cur))
            keep, n = [], 0
            for x in reversed(cur):
                n += len(x) + 1
                if n > overlap:
                    break
                keep.insert(0, x)
            cur = keep
    if cur and (not out or len(" ".join(cur)) > overlap):
        out.append(" ".join(cur))
    return out


def chunk_document(text: str, source_file: str, doc_type: str, supplier_id: str | None, chunk_size: int = 700, overlap: int = 100, page: int | None = None) -> list[Chunk]:
    """Sections start with '## heading' (our contract/policy text format) or a numbered/capitalised heading line. Price-schedule
    sections (lines containing ' | ') are split by lines so each chunk carries whole price rows plus the section heading."""
    text = clean_text(text)
    parts = re.split(r"(?m)^##\s+", text)
    sections: list[tuple[str | None, str]] = []
    if len(parts) > 1:
        sections.append((None, parts[0]))
        for p in parts[1:]:
            head, _, body = p.partition("\n")
            sections.append((head.strip(), body.strip()))
    else:
        sections.append((None, text))
    chunks: list[Chunk] = []
    for head, body in sections:
        if not body.strip():
            continue
        prefix = f"[{head}] " if head else ""
        if body.count(" | ") >= 3:
            rows = [r for r in body.split("\n") if r.strip()]
            for i in range(0, len(rows), 8):
                pieces = [prefix + "\n".join(rows[i:i + 8])]
                for pc in pieces:
                    chunks.append(Chunk(f"{source_file}#{len(chunks):03d}", pc, source_file, doc_type, supplier_id, head, page))
        else:
            for pc in _split_words(body, chunk_size, overlap):
                chunks.append(Chunk(f"{source_file}#{len(chunks):03d}", prefix + pc, source_file, doc_type, supplier_id, head, page))
    for c in chunks:
        c.flags = scan_untrusted(c.text)
    return chunks


# ---------------------------------------------------------------------------------------------
# embeddings
# ---------------------------------------------------------------------------------------------
class Embedder(Protocol):
    name: str
    def fit(self, texts: list[str]) -> None: ...
    def encode(self, texts: list[str]) -> np.ndarray: ...


class TfidfEmbedder:
    """Offline lexical embedding (word 1-2 grams, sublinear tf, L2-normalised dense vectors)."""
    name = "tfidf-1-2gram (offline lexical baseline)"

    def __init__(self):
        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b[\w\-\.]{2,}\b", lowercase=True, min_df=1)

    def fit(self, texts: list[str]) -> None:
        self.vec.fit(texts)

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.vec.transform(texts).astype(np.float32).toarray()


class SentenceTransformerEmbedder:
    """Local semantic embeddings (no paid API). Requires `pip install sentence-transformers` and one-time model download."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # lazy: heavy optional dependency
        self.model = SentenceTransformer(model_name)
        self.name = model_name

    def fit(self, texts: list[str]) -> None:
        return None

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)


def make_embedder(prefer_semantic: bool = False, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    """Try the local semantic model first when asked; fall back (visibly) to the offline TF-IDF baseline."""
    if prefer_semantic:
        try:
            return SentenceTransformerEmbedder(model_name), None
        except Exception as e:  # noqa: BLE001
            return TfidfEmbedder(), f"semantic embedder unavailable ({type(e).__name__}); using offline TF-IDF baseline"
    return TfidfEmbedder(), None


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = docs
        self.avg = sum(len(d) for d in docs) / max(1, len(docs))
        df: Counter = Counter()
        for d in docs:
            df.update(set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(d) for d in docs]

    def scores(self, q: list[str]) -> np.ndarray:
        out = np.zeros(len(self.docs), dtype=np.float32)
        for i, tf in enumerate(self.tf):
            dl = sum(tf.values())
            s = 0.0
            for t in q:
                if t in tf:
                    s += self.idf.get(t, 0) * tf[t] * (self.k1 + 1) / (tf[t] + self.k1 * (1 - self.b + self.b * dl / self.avg))
            out[i] = s
        return out


def tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9\-\.]*", s.lower())


# ---------------------------------------------------------------------------------------------
# knowledge base
# ---------------------------------------------------------------------------------------------
QUERY_TEMPLATES = {
    "PRICE_ABOVE_CONTRACT": ("price schedule {product} contract price", ("CONTRACT",)),
    "NO_CONTRACT_PRICE": ("price schedule {product} contract price", ("CONTRACT",)),
    "DISCOUNT_ERROR": ("volume discount ordered quantity units or more", ("CONTRACT",)),
    "UNAUTHORIZED_CHARGE": ("freight additional charges permitted surcharge", ("CONTRACT", "POLICY")),
    "CONTRACT_NOT_EFFECTIVE": ("agreement effective term period purchase order date", ("CONTRACT", "POLICY")),
    "TAX_RATE_POLICY_MISMATCH": ("synthetic policy tax rate {category}", ("POLICY",)),
    "TAX_CALC_ERROR": ("tax calculated on the line amount after discount", ("POLICY",)),
    "MISSING_TAX_INFO": ("invoice must state the tax rate and tax amount for each line", ("POLICY",)),
    "QTY_EXCEEDS_RECEIVED": ("invoiced quantity must not exceed received quantity three-way matching", ("POLICY",)),
    "QTY_EXCEEDS_ORDERED": ("invoiced quantity must not exceed ordered quantity", ("POLICY",)),
    "PO_DC_QTY_CONFLICT": ("received quantity exceeds ordered quantity over-delivery", ("POLICY",)),
    "PARTIAL_DELIVERY_RECONCILED": ("several deliveries received quantities aggregated", ("POLICY",)),
    "MISSING_DC": ("missing delivery record is not proof of non-delivery", ("POLICY",)),
    "MISSING_PO": ("invoice matched to its purchase order before payment", ("POLICY",)),
    "DUPLICATE_EXACT": ("exact duplicate supplier normalized invoice number", ("POLICY",)),
    "POSSIBLE_DUPLICATE": ("possible duplicate different number same purchase order", ("POLICY",)),
    "UNKNOWN_SUPPLIER": ("approved supplier master unlisted suppliers onboarding", ("POLICY",)),
    "SUPPLIER_DETAILS_INCONSISTENT": ("supplier tax identification must match the supplier master", ("POLICY",)),
    "CURRENCY_MISMATCH": ("invoices must be issued in Pakistani Rupees PKR", ("POLICY",)),
    "DATE_REFERENCE_INCONSISTENT": ("invoice date should not precede delivery date references", ("POLICY",)),
    "AMBIGUOUS_PRODUCT": ("line cannot be resolved to a single catalogue product manual review", ("POLICY",)),
    "UNKNOWN_PRODUCT_CODE": ("line cannot be resolved to a single catalogue product manual review", ("POLICY",)),
}


class KnowledgeBase:
    def __init__(self, chunk_size: int = 700, overlap: int = 100, embedder: Embedder | None = None, min_score: float = 0.08):
        self.chunk_size, self.overlap, self.min_score = chunk_size, overlap, min_score
        self.embedder = embedder or TfidfEmbedder()
        self.chunks: list[Chunk] = []
        self.index: faiss.Index | None = None
        self.bm25: BM25 | None = None
        self._cache: dict = {}
        self.source_text: dict[str, str] = {}

    # -------- build
    def add_directory(self, raw_dir: str | Path, prefer_txt: bool = True) -> int:
        """Load contracts and policies. If both PDF and TXT exist for a document, the TXT (structured headings) is used."""
        raw = Path(raw_dir)
        files: dict[str, Path] = {}
        for sub in ("contracts", "policies"):
            d = raw / sub
            if not d.exists():
                continue
            for f in sorted(d.iterdir()):
                if f.suffix.lower() in (".txt", ".md", ".pdf"):
                    key = f"{sub}/{f.stem}"
                    if key in files and prefer_txt and files[key].suffix.lower() in (".txt", ".md"):
                        continue
                    if key in files and f.suffix.lower() == ".pdf" and prefer_txt:
                        continue
                    files[key] = f
        n0 = len(self.chunks)
        for key, f in files.items():
            if f.stem == "procurement_policies_summary":
                continue
            self.add_file(f)
        return len(self.chunks) - n0

    def add_file(self, f: str | Path) -> int:
        f = Path(f)
        doc = load_file(f, ocr=False)
        stem = f.stem
        doc_type = "CONTRACT" if stem.upper().startswith("CONTRACT") else "POLICY" if stem.upper().startswith("POL") else "OTHER"
        sup = None
        m = re.search(r"(SUP-\d{3})", stem)
        if m:
            sup = m.group(1)
        before = len(self.chunks)
        for p in doc.pages:
            self.chunks += chunk_document(p.text, f.name, doc_type, sup, self.chunk_size, self.overlap, page=p.page if f.suffix.lower() == ".pdf" else None)
        self.source_text[f.name] = doc.text
        self.index = None
        return len(self.chunks) - before

    def build(self) -> None:
        if not self.chunks:
            raise ValueError("knowledge base is empty")
        texts = [c.text for c in self.chunks]
        self.embedder.fit(texts)
        emb = self.embedder.encode(texts)
        faiss.normalize_L2(emb)
        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(emb)
        self.bm25 = BM25([tok(t) for t in texts])
        self._cache.clear()

    # -------- search
    def _allowed(self, supplier_id, doc_types, include_global) -> np.ndarray:
        ok = np.ones(len(self.chunks), dtype=bool)
        for i, c in enumerate(self.chunks):
            if doc_types and c.doc_type not in doc_types:
                ok[i] = False
            elif supplier_id and c.supplier_id and c.supplier_id != supplier_id:
                ok[i] = False
            elif supplier_id and c.supplier_id is None and not include_global and c.doc_type == "CONTRACT":
                ok[i] = False
        return ok

    def search(self, query: str, k: int = 5, mode: str = "hybrid", supplier_id: str | None = None, doc_types: tuple[str, ...] | None = None, include_global: bool = True) -> list[Hit]:
        if self.index is None:
            self.build()
        ok = self._allowed(supplier_id, doc_types, include_global)
        q = self.embedder.encode([query])
        faiss.normalize_L2(q)
        dense = np.full(len(self.chunks), -1.0, dtype=np.float32)
        sims, ids = self.index.search(q, len(self.chunks))
        dense[ids[0]] = sims[0]
        kw = self.bm25.scores(tok(query))
        def ranks(arr):
            order = [i for i in np.argsort(-arr) if ok[i]]
            return {i: r for r, i in enumerate(order, 1)}
        rd, rk = ranks(dense), ranks(kw)
        if mode == "dense":
            order = sorted(rd, key=lambda i: rd[i]); score = lambda i: float(dense[i])
        elif mode == "keyword":
            order = sorted(rk, key=lambda i: rk[i]); score = lambda i: float(kw[i])
        else:
            fused = {i: 1 / (60 + rd[i]) + 1 / (60 + rk[i]) for i in rd}
            order = sorted(fused, key=lambda i: -fused[i]); score = lambda i: float(dense[i])
        hits = []
        for i in order:
            if mode != "keyword" and dense[i] < self.min_score and kw[i] <= 0:
                continue
            if mode == "keyword" and kw[i] <= 0:
                continue
            hits.append(Hit(self.chunks[i], score(i), len(hits) + 1, mode))
            if len(hits) >= k:
                break
        return hits

    # -------- evidence
    @staticmethod
    def to_evidence(h: Hit, max_chars: int = 420) -> EvidenceRef:
        c = h.chunk
        snippet = c.text if len(c.text) <= max_chars else c.text[:max_chars].rsplit(" ", 1)[0] + " ..."
        return EvidenceRef(source_file=c.source_file, doc_type=c.doc_type, supplier_id=c.supplier_id, section=c.section, page=c.page, snippet=snippet, score=round(h.score, 4), chunk_id=c.chunk_id)

    def evidence_for(self, code: str, supplier_id: str | None, product_code: str | None = None, product_desc: str | None = None, category: str | None = None, k: int = 2,
                     agreement_id: str | None = None) -> list[EvidenceRef]:
        """Supporting passages for a finding. Returns [] when nothing relevant exists (never invents a citation)."""
        key = (code, supplier_id, product_code, category, agreement_id)
        if key in self._cache:
            return self._cache[key]
        tpl = QUERY_TEMPLATES.get(code)
        out: list[EvidenceRef] = []
        if tpl:
            q = tpl[0].format(product=f"{product_code or ''} {product_desc or ''}".strip(), category=category or "")
            hits = self.search(q, k=k, mode="hybrid", supplier_id=supplier_id if "CONTRACT" in tpl[1] else None, doc_types=tpl[1])
            if code in ("PRICE_ABOVE_CONTRACT", "NO_CONTRACT_PRICE") and product_code:
                cand = [h for h in self.search(product_code, k=12, mode="keyword", supplier_id=supplier_id, doc_types=("CONTRACT",)) if product_code in h.chunk.text]
                if agreement_id:
                    cand = [h for h in cand if agreement_id in (h.chunk.section or "")] or []
                refs = []
                for h in cand[:1]:
                    row = next((ln for ln in h.chunk.text.split("\n") if product_code in ln), None)
                    if row:
                        row = re.sub(r"^\[[^\]]*\]\s*", "", row)
                        ev = self.to_evidence(h)
                        ev.snippet = f"[{h.chunk.section}] {row}"
                        refs.append(ev)
                out = refs
                self._cache[key] = out
                return out
            out = [self.to_evidence(h) for h in hits[:k]]
        self._cache[key] = out
        return out

    def verify_citation(self, ref: EvidenceRef) -> bool:
        """True iff the cited file is indexed and every non-ellipsis fragment of the snippet appears in its text."""
        src = self.source_text.get(ref.source_file)
        if src is None:
            return False
        norm = re.sub(r"\s+", " ", src)
        frag = re.sub(r"\s+", " ", ref.snippet.replace(" ...", "")).strip()
        frag = re.sub(r"^\[[^\]]*\]\s*", "", frag)
        return all(part.strip() in norm for part in frag.split("\n") if part.strip()) or frag in norm
