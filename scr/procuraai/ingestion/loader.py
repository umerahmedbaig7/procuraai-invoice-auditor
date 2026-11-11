"""Document ingestion: PDF (PyMuPDF text layer, OCR fallback only when needed), PNG/JPG (Tesseract OCR),
CSV/XLSX (structured tables), TXT/MD, plus safe handling of batches and nested ZIP archives.

Text is reconstructed into visual *lines* from word boxes so that PDF text and OCR output share one format:
words on the same baseline are joined with a single space; a horizontal gap > ``GAP_PT`` points is rendered
as two spaces, which the rule-based extractor uses as a column/field separator.
"""
from __future__ import annotations

import logging
import statistics
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd
import pymupdf
from PIL import Image, ImageOps

log = logging.getLogger("procuraai.ingestion")

ALLOWED_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".csv", ".xlsx", ".txt", ".md", ".zip"}
GAP_PT = 6.0
MIN_TEXT_CHARS = 40          # below this a PDF page is treated as image-only and OCR is applied
A4_W_PT = 595.0


class IngestionError(Exception):
    pass


@dataclass
class ExtractedPage:
    page: int
    text: str
    method: str                    # "text-layer" | "ocr" | "plain-text"
    confidence: float = 1.0
    n_words: int = 0


@dataclass
class ExtractedDocument:
    source_file: str
    file_type: str
    pages: list[ExtractedPage] = field(default_factory=list)
    table: pd.DataFrame | None = None            # for CSV/XLSX
    doc_type: str = "UNKNOWN"
    warnings: list[str] = field(default_factory=list)
    ocr_variant: int = 0

    @property
    def text(self) -> str:
        return "\n".join(p.text for p in self.pages)

    @property
    def confidence(self) -> float:
        return min((p.confidence for p in self.pages), default=0.0)

    @property
    def method(self) -> str:
        ms = {p.method for p in self.pages}
        return "+".join(sorted(ms)) if ms else "none"


# ---------------------------------------------------------------------------------------------
def words_to_lines(words: list[tuple[float, float, float, float, str]], gap: float = GAP_PT) -> str:
    """words: (x0, y0, x1, y1, text) in points. Cluster by vertical centre and join left-to-right."""
    words = [w for w in words if w[4].strip()]
    if not words:
        return ""
    med_h = statistics.median(w[3] - w[1] for w in words) or 8.0
    words.sort(key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    rows: list[list] = []
    for w in words:
        yc = (w[1] + w[3]) / 2
        if rows and abs(yc - rows[-1][0]) <= med_h * 0.55:
            rows[-1][1].append(w)
            rows[-1][0] = (rows[-1][0] * (len(rows[-1][1]) - 1) + yc) / len(rows[-1][1])
        else:
            rows.append([yc, [w]])
    out = []
    for _, ws in rows:
        ws.sort(key=lambda w: w[0])
        s = ws[0][4]
        for prev, cur in zip(ws, ws[1:]):
            s += ("  " if cur[0] - prev[2] > gap else " ") + cur[4]
        out.append(s)
    return "\n".join(out)


# (target width px, tesseract psm, binarisation threshold). Variant 0 is tried first; later variants are retries.
OCR_VARIANTS = [(1800, 6, None), (2400, 4, None), (2400, 6, 150), (2400, 6, None)]


def _ocr_image(img: Image.Image, scale_pt: float, variant: int = 0) -> tuple[str, float, int]:
    """OCR a PIL image. Returns (line-structured text, mean confidence 0-1, word count)."""
    try:
        import pytesseract
    except ImportError as e:  # pragma: no cover
        raise IngestionError("pytesseract is not installed") from e
    width, psm, thr = OCR_VARIANTS[variant % len(OCR_VARIANTS)]
    g = ImageOps.autocontrast(ImageOps.grayscale(img), cutoff=1)
    f = width / g.width
    g = g.resize((int(g.width * f), int(g.height * f)), Image.LANCZOS)
    if thr:
        g = g.point(lambda v: 255 if v > thr else 0)
    d = pytesseract.image_to_data(g, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    k = A4_W_PT / g.width
    words, confs = [], []
    for i, t in enumerate(d["text"]):
        if t.strip() and float(d["conf"][i]) >= 0:
            x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
            words.append((x * k, y * k, (x + w) * k, (y + h) * k, t))
            confs.append(float(d["conf"][i]) / 100.0)
    return words_to_lines(words), (sum(confs) / len(confs) if confs else 0.0), len(words)


def load_pdf(path: Path, ocr: bool = True, ocr_variant: int = 0) -> ExtractedDocument:
    doc = ExtractedDocument(source_file=path.name, file_type="pdf")
    try:
        pdf = pymupdf.open(path)
    except Exception as e:
        raise IngestionError(f"cannot open PDF {path.name}: {e}") from e
    try:
        if pdf.page_count == 0:
            raise IngestionError(f"{path.name}: PDF has no pages")
        for i, page in enumerate(pdf, 1):
            words = [(w[0], w[1], w[2], w[3], w[4]) for w in page.get_text("words")]
            text = words_to_lines(words)
            if len(text.replace(" ", "").replace("\n", "")) >= MIN_TEXT_CHARS:
                doc.pages.append(ExtractedPage(i, text, "text-layer", 1.0, len(words)))
                continue
            if not ocr:
                doc.pages.append(ExtractedPage(i, text, "text-layer", 0.0, len(words)))
                doc.warnings.append(f"page {i}: little/no text and OCR disabled")
                continue
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            t, conf, n = _ocr_image(img, page.rect.width, ocr_variant)
            doc.pages.append(ExtractedPage(i, t, "ocr", conf, n))
            if n == 0:
                doc.warnings.append(f"page {i}: OCR found no text")
    finally:
        pdf.close()
    return doc


def load_image(path: Path, ocr_variant: int = 0) -> ExtractedDocument:
    doc = ExtractedDocument(source_file=path.name, file_type=path.suffix.lower().lstrip("."))
    try:
        img = Image.open(path)
        img.load()
    except Exception as e:
        raise IngestionError(f"cannot read image {path.name}: {e}") from e
    t, conf, n = _ocr_image(img.convert("RGB"), A4_W_PT, ocr_variant)
    doc.pages.append(ExtractedPage(1, t, "ocr", conf, n))
    if n == 0:
        doc.warnings.append("OCR found no text")
    return doc


def load_text(path: Path) -> ExtractedDocument:
    txt = path.read_text(encoding="utf-8", errors="replace")
    doc = ExtractedDocument(source_file=path.name, file_type=path.suffix.lower().lstrip("."))
    doc.pages.append(ExtractedPage(1, txt, "plain-text", 1.0, len(txt.split())))
    if not txt.strip():
        doc.warnings.append("empty text file")
    return doc


def load_table(path: Path) -> ExtractedDocument:
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False) if path.suffix.lower() == ".csv" else pd.read_excel(path, dtype=str, sheet_name=0).fillna("")
    except Exception as e:
        raise IngestionError(f"cannot read table {path.name}: {e}") from e
    doc = ExtractedDocument(source_file=path.name, file_type=path.suffix.lower().lstrip("."), table=df)
    doc.pages.append(ExtractedPage(1, df.head(5).to_csv(index=False), "plain-text", 1.0, int(df.size)))
    return doc


# ---------------------------------------------------------------------------------------------
_TITLES = {"PURCHASE ORDER": "PURCHASE_ORDER", "DELIVERY CHALLAN": "DELIVERY_CHALLAN", "GOODS RECEIVED NOTE": "DELIVERY_CHALLAN",
           "TAX INVOICE": "INVOICE", "INVOICE": "INVOICE", "BILL / CASH MEMO": "INVOICE"}


def detect_doc_type(text: str, filename: str = "") -> str:
    """Title-first detection (a title is a whole 2-space-separated segment), then label heuristics."""
    fn = filename.lower()
    if fn.startswith("contract"):
        return "CONTRACT"
    if fn.startswith("pol-") or "polic" in fn:
        return "POLICY"
    lines = text.splitlines()[:14]
    for ln in lines:
        for seg in ln.split("  "):
            key = seg.strip().upper()
            if key in _TITLES:
                return _TITLES[key]
    low = "\n".join(lines).lower()
    if "supply and pricing agreement" in low:
        return "CONTRACT"
    if "purchase order" in low and "po number" in low and "invoice" not in low:
        return "PURCHASE_ORDER"
    if any(k in low for k in ("invoice no", "invoice #", "bill no", "tax invoice")):
        return "INVOICE"
    if any(k in low for k in ("dc no", "grn no", "delivery challan", "goods received")):
        return "DELIVERY_CHALLAN"
    if "policy" in low:
        return "POLICY"
    return "UNKNOWN"


def load_file(path: str | Path, ocr: bool = True, ocr_variant: int = 0) -> ExtractedDocument:
    p = Path(path)
    ext = p.suffix.lower()
    if ext not in ALLOWED_EXT - {".zip"}:
        raise IngestionError(f"unsupported file type: {p.name}")
    if not p.is_file() or p.stat().st_size == 0:
        raise IngestionError(f"empty or missing file: {p.name}")
    d = load_pdf(p, ocr, ocr_variant) if ext == ".pdf" else load_image(p, ocr_variant) if ext in (".png", ".jpg", ".jpeg") else load_table(p) if ext in (".csv", ".xlsx") else load_text(p)
    d.ocr_variant = ocr_variant
    if d.table is None:
        d.doc_type = detect_doc_type(d.text, p.name)
    return d


def safe_extract_zip(zip_path: Path, dest: Path, max_files: int = 2000, max_total_mb: int = 500, depth: int = 0, max_depth: int = 3) -> list[Path]:
    """Extract an archive defensively: zip-slip protection, size/count limits, extension allow-list, bounded nesting."""
    if depth > max_depth:
        raise IngestionError("zip nesting too deep")
    out: list[Path] = []
    dest.mkdir(parents=True, exist_ok=True)
    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as e:
        raise IngestionError(f"{zip_path.name} is not a valid zip archive") from e
    with zf:
        infos = [i for i in zf.infolist() if not i.is_dir()]
        if len(infos) > max_files:
            raise IngestionError(f"archive contains {len(infos)} files (limit {max_files})")
        if sum(i.file_size for i in infos) > max_total_mb * 1_000_000:
            raise IngestionError(f"archive expands beyond {max_total_mb} MB")
        root = dest.resolve()
        for i in infos:
            target = (dest / i.filename).resolve()
            if not str(target).startswith(str(root)):
                raise IngestionError(f"unsafe path in archive: {i.filename}")
            if Path(i.filename).suffix.lower() not in ALLOWED_EXT:
                log.warning("skipping unsupported archive member %s", i.filename)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(i) as src, open(target, "wb") as dst:
                dst.write(src.read())
            if target.suffix.lower() == ".zip":
                out += safe_extract_zip(target, target.with_suffix(""), max_files, max_total_mb, depth + 1, max_depth)
            else:
                out.append(target)
    return out


def validate_upload(path: Path, max_mb: int = 25) -> None:
    if path.suffix.lower() not in ALLOWED_EXT:
        raise IngestionError(f"file type {path.suffix!r} not allowed")
    if path.stat().st_size > max_mb * 1_000_000:
        raise IngestionError(f"{path.name} exceeds {max_mb} MB")


def ingest_paths(paths: Iterable[str | Path], workdir: str | Path | None = None, ocr: bool = True, max_mb: int = 25
                 ) -> tuple[list[ExtractedDocument], list[dict]]:
    """Ingest many files (including ZIPs). Returns (documents, errors). One bad file never stops the batch."""
    docs: list[ExtractedDocument] = []
    errors: list[dict] = []
    work = Path(workdir or "processed/unzipped")
    queue = [Path(p) for p in paths]
    flat: list[Path] = []
    for p in queue:
        try:
            validate_upload(p, max_mb)
            if p.suffix.lower() == ".zip":
                flat += safe_extract_zip(p, work / p.stem)
            else:
                flat.append(p)
        except (IngestionError, OSError) as e:
            errors.append(dict(file=p.name, error=str(e)))
    for p in flat:
        try:
            docs.append(load_file(p, ocr=ocr))
        except Exception as e:  # noqa: BLE001 - keep the batch going, record the error
            errors.append(dict(file=p.name, error=f"{type(e).__name__}: {e}"))
    return docs, errors
