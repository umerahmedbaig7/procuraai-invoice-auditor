<div align="center">

# 🧾 ProcuraAI — AI Invoice Auditor & Procurement Compliance Checker
### Three-Way Matching (PO ↔ Delivery ↔ Invoice) · OCR · RAG with Citations · LangGraph Agents · Decimal Audit Engine · FastAPI · Streamlit

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-1C3C3C?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/Gemini%20API-Optional-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-0467DF?style=for-the-badge)]()
[![Tests](https://img.shields.io/badge/Tests-54%20passing-brightgreen?style=for-the-badge)]()
[![Status](https://img.shields.io/badge/Status-Prototype-orange?style=for-the-badge)]()

<br>

> *"A flagged invoice is a question for a human, not a verdict about a supplier."*

<br>

**Author:** Umer Ahmed Baig Mughal <br>
**Project type:** AI Engineering · LLM Application · Accounts Payable Automation · Document Intelligence <br>
**Focus areas:** Invoice Auditing · Three-Way Matching · RAG · Multi-Agent Workflows · OCR · Financial Reconciliation <br>
**Background:** MSc Robotics and Artificial Intelligence — ITMO University

</div>

---

<div align="center">

![Dashboard summary with flagged invoices and estimated exposure](docs/images/dashboard-summary.png)

![Evidence viewer showing the contract clause behind a finding](docs/images/dashboard-evidence.png)

</div>

---

## 📋 Table of Contents

- [📖 About This Repository](#-about-this-repository)
- [📁 Repository Structure](#-repository-structure)
- [🔬 Overview — How the Pipeline Works](#-overview--how-the-pipeline-works)
- [🧪 Component Summaries](#-component-summaries)
  - [🔵 Stage 1 — Synthetic Procurement Dataset](#-stage-1--synthetic-procurement-dataset)
  - [🟠 Stage 2 — Ingestion: PDF, Images & OCR](#-stage-2--ingestion-pdf-images--ocr)
  - [🟣 Stage 3 — Extraction & Entity Matching](#-stage-3--extraction--entity-matching)
  - [🟢 Stage 4 — RAG Knowledge Base with Citations](#-stage-4--rag-knowledge-base-with-citations)
  - [🔴 Stage 5 — Deterministic Audit Engine](#-stage-5--deterministic-audit-engine)
  - [🟡 Stage 6 — Multi-Agent Workflow & Reporting](#-stage-6--multi-agent-workflow--reporting)
  - [⚪ Stage 7 — REST API & Streamlit Dashboard](#-stage-7--rest-api--streamlit-dashboard)
- [🔗 Request Lifecycle](#-request-lifecycle)
- [🌐 API Reference](#-api-reference)
- [🔧 Technical Specifications](#-technical-specifications)
- [🚀 Getting Started](#-getting-started)
- [📊 Key Results Summary](#-key-results-summary)
- [🧠 Analysis and Discussion](#-analysis-and-discussion)
- [🚧 Notes and Limitations](#-notes-and-limitations)
- [🔒 Security Considerations](#-security-considerations)
- [🧰 Tech Stack](#-tech-stack)
- [🏷️ Keywords](#️-keywords)
- [👤 Author](#-author)
- [📄 License](#-license)

---

## 📖 About This Repository

**ProcuraAI** is an open-source **AI invoice auditing and procurement compliance** prototype. It checks supplier invoices against **purchase orders, delivery challans (goods-received notes), supplier contracts, approved price lists and procurement policies** — the classic **three-way matching** workflow used in accounts payable (AP) automation.

It reads PDFs, scans and images (with **OCR** only where needed), extracts structured fields, matches suppliers and products, retrieves the relevant **contract and policy passages with citations (RAG)**, and runs a **deterministic `Decimal` audit engine** that reports price overcharges, quantity overbilling, **duplicate invoices**, arithmetic and tax errors, unauthorised charges, missing documents and more. A four-agent **LangGraph** workflow orchestrates the stages, and results are exposed through a **FastAPI** service and a **Streamlit** dashboard with JSON, Markdown, CSV and Excel exports.

The unifying idea is that **an LLM should read and explain, but never decide**. Every financial comparison is plain Python with explicit rounding rules; findings are labelled *confirmed*, *potential*, *insufficient evidence* or *manual review*; and no supplier is ever called fraudulent. **All payment decisions stay with humans.**

> **Everything in this repository is synthetic.** Companies, products, documents and transactions are fictional (a made-up Pakistan-based buyer, PKR). Tax rates and policies are synthetic configuration, **not** real tax law. This is a **prototype, not production-ready software**.

### 🎯 What You Will Find Here

| 📁 Component | 🏷️ Topic | 🧠 Core Concept | 🛠️ Key Tools |
|:------------:|:--------:|:---------------:|:-------------:|
| Data | Synthetic procurement dataset | Seeded generator · 25 labelled anomaly scenarios · ground truth kept separate | `reportlab` · `Pillow` · `pandas` |
| Ingestion | PDF, image and text intake | Text layer first · OCR only for image-only pages · safe ZIP handling | `PyMuPDF` · `Tesseract` |
| Extraction | Structured document data | Template rules offline · optional Gemini · Pydantic validation · provenance | `Pydantic` · `google-genai` |
| Matching | Supplier & product entities | Exact → alias → fuzzy · review queue for low confidence | `rapidfuzz` |
| RAG | Contract & policy evidence | Section-aware chunking · FAISS + BM25 hybrid · verifiable citations | `FAISS` · `scikit-learn` |
| Audit | Reconciliation engine | `Decimal` money · tolerances · de-duplicated exposure | Pure Python |
| Agents | Workflow orchestration | 4 agents · shared state · conditional human-review routing | `LangGraph` |
| Delivery | API and UI | REST endpoints · SQLite persistence · interactive dashboard | `FastAPI` · `Streamlit` |

---

## 📁 Repository Structure

```
📦 procuraai-invoice-auditor/
│
├── 📄 README.md                               # ← You are here
├── 📄 app.py                                  # Streamlit dashboard
├── 📄 pyproject.toml · pytest.ini · requirements.txt
├── 📄 .env.example                            # copy to .env (git-ignored) — never commit real keys
├── 📄 Dockerfile · docker-compose.yml · LICENSE
│
├── 📁 src/procuraai/
│   ├── 📁 datagen/                            # synthetic data: catalogue, generator, renderers, exporter + validator
│   ├── 📁 ingestion/loader.py                 # PDF text layer, OCR fallback, ZIP safety
│   ├── 📁 extraction/                         # rule-based, structured CSV, Gemini client, OCR retry pipeline
│   ├── 📄 normalization.py                    # supplier / product matching, dates, currencies, units
│   ├── 📁 rag/                                # chunking, embeddings, FAISS + BM25, citations
│   ├── 📁 audit/                              # money.py (Decimal rules) · engine.py (all checks)
│   ├── 📁 agents/                             # 4 agents + LangGraph graph
│   ├── 📁 reporting/                          # JSON · Markdown · CSV · Excel
│   ├── 📁 api/ · 📁 storage/                  # FastAPI app · SQLite persistence
│   └── 📄 schemas.py · taxonomy.py · config.py · services.py · evaluation.py
│
├── 📁 scripts/
│   ├── 📄 generate_synthetic_data.py          # reproducible dataset (seed 20250101)
│   ├── 📄 run_evaluation.py                   # labelled evaluation: P/R/F1, RAG Recall@k, timing
│   ├── 📄 check_gemini.py                     # diagnose Gemini key / model / API
│   └── 📄 try_audit.py · make_evaluation_doc.py · build_notebook.py
│
├── 📁 tests/                                  # 54 offline tests (no API key needed)
├── 📁 notebooks/ProcuraAI_Complete_Implementation.ipynb   # Google Colab walkthrough (15 sections)
├── 📁 docs/                                   # architecture.md · evaluation.md
├── 📁 data/README.md                          # how to generate / download the dataset
└── 📁 reports/                                # example audit reports · evaluation results · test report
```

> The 58 MB synthetic dataset is **generated, not committed** — run `python scripts/generate_synthetic_data.py` or download it from the Releases page.

---

## 🔬 Overview — How the Pipeline Works

Every audit flows through four agents, each with one job and an explicit data contract. Deterministic Python does the work wherever possible; the LLM is used only at the edges, and only if you configure it.

**Agent 1 — Document Intelligence:** ingest files, use the PDF text layer when it exists, OCR only image-only pages, extract fields into validated Pydantic records, and keep provenance (file, page, excerpt, confidence).

**Agent 2 — Procurement Evidence:** find the supplier agreement effective on the PO date and retrieve the relevant contract and policy passages, with citations.

**Agent 3 — Reconciliation & Audit:** run the deterministic three-way match, price, discount, arithmetic, tax, duplicate and charge checks, and estimate exposure without double counting.

**Agent 4 — Reporting & Review:** assign severity and confidence by documented rules, write explanations (template or Gemini), build the human-review queue and export JSON / Markdown / CSV / Excel.

```
  Uploads / Dataset       Agent 1                Agent 2               Agent 3                 Agent 4
  ─────────────────       ───────────────        ───────────────       ─────────────────       ─────────────────
  PDF · PNG/JPG · TXT ──► Document            ─► Procurement        ─► Reconciliation      ─► Reporting & Review
  CSV · XLSX · ZIP        Intelligence           Evidence (RAG)        & Audit (Decimal)       JSON · MD · CSV · XLSX
                          OCR · extract          contracts · policy    PO ↔ DC ↔ Invoice       ┌────────────────────┐
                          validate · match       citations             duplicates · tax        │ human-review queue │
                                                                                               └────────────────────┘
```

---

## 🧪 Component Summaries

---

### 🔵 Stage 1 — Synthetic Procurement Dataset

<div align="center">

[![Stage1](https://img.shields.io/badge/Stage%201-Synthetic%20Data-0078D7?style=flat-square&logo=python&logoColor=white)]()
[![Module](https://img.shields.io/badge/Module-datagen-lightblue?style=flat-square)]()
[![Docs](https://img.shields.io/badge/Documents-PDF%20%C2%B7%20PNG%20%C2%B7%20JPG%20%C2%B7%20TXT-lightblue?style=flat-square)]()
[![Seed](https://img.shields.io/badge/Seed-20250101-lightblue?style=flat-square)]()

</div>

#### 📌 Task Description

> Create realistic, **internally consistent** procurement documents with **known, labelled defects** — so every audit rule can be tested without real confidential data.

**What this stage does:**
- Generates fictional suppliers, products (electrical equipment, lighting, electronics, cables, connectors, industrial supplies), price agreements, POs, delivery records and invoices.
- Builds every transaction **clean first**, then injects one defect scenario at a time, so clean cases cannot contain accidental anomalies.
- Renders three invoice layouts, two PO and two delivery layouts as **selectable-text PDFs, image-only (scanned-style) PDFs, rotated/noisy PNG and JPG images and plain text**.
- Writes **ground truth in separate files** that agents never see during an audit — only the evaluator reads them.
- Validates every cross-document reference **before saving** and stops with a clear error if anything is inconsistent.

#### 📤 Key Numerical Results

```
Dataset (seed 20250101, regenerated bit-for-bit)

┌──────────────────────────────┬──────────────────────────────────────────────┐
│ Item                         │ Count                                        │
├──────────────────────────────┼──────────────────────────────────────────────┤
│ Invoices                     │ 72  (30 clean / info-only, 42 anomalous)     │
│ Purchase orders              │ 65                                           │
│ Delivery challans / GRNs     │ 68                                           │
│ Suppliers · products         │ 8 · 52                                       │
│ Pricing agreements           │ 10  (two suppliers revised, one expires)     │
│ Contracts · policies         │ 8 · 5  (PDF + TXT)                           │
│ Scenarios covered            │ 25 + supplier-detail + possible-duplicate    │
│ Files / archive size         │ 249 files · 58 MB zip                        │
└──────────────────────────────┴──────────────────────────────────────────────┘
```

---

### 🟠 Stage 2 — Ingestion: PDF, Images & OCR

<div align="center">

[![Stage2](https://img.shields.io/badge/Stage%202-Ingestion-E85D04?style=flat-square&logo=python&logoColor=white)]()
[![Module](https://img.shields.io/badge/Module-loader.py-orange?style=flat-square)]()
[![OCR](https://img.shields.io/badge/OCR-Tesseract-orange?style=flat-square)]()
[![PDF](https://img.shields.io/badge/PDF-PyMuPDF-orange?style=flat-square)]()

</div>

#### 📌 Task Description

> Read many file types safely and **never OCR a page that already has usable text**.

**What this stage does:**
- Uses the **PDF text layer** when a page has enough text; applies **OCR only to image-only pages and images**.
- Rebuilds visual lines from word boxes so PDF text and OCR share one format.
- **Retries OCR** with different preprocessing and keeps the pass whose result is most self-consistent (lines sum to subtotal, totals foot).
- Accepts PDF, PNG/JPG, CSV, XLSX, TXT/MD and **nested ZIPs** with extension, size, count, depth and **zip-slip** protection. One bad file never stops a batch.

---

### 🟣 Stage 3 — Extraction & Entity Matching

<div align="center">

[![Stage3](https://img.shields.io/badge/Stage%203-Extraction-7B2FBE?style=flat-square&logo=python&logoColor=white)]()
[![Module](https://img.shields.io/badge/Module-extraction%20%C2%B7%20normalization-purple?style=flat-square)]()
[![Schema](https://img.shields.io/badge/Validation-Pydantic%20v2-purple?style=flat-square)]()
[![LLM](https://img.shields.io/badge/LLM-Gemini%20(optional)-purple?style=flat-square)]()

</div>

#### 📌 Task Description

> Turn documents into validated records — **never inventing a value that is not there**.

**What this stage does:**
- **Rule-based extractor** (offline, no key) for the three synthetic invoice layouts, POs and delivery notes; unknown values stay `None` and are listed in `missing_fields`.
- **Optional Gemini extraction** with schema-constrained JSON, Pydantic re-validation, bounded retries and honest fallback: if the LLM fails, the pipeline records `llm_fallback` and says so — it never pretends the LLM succeeded.
- **Supplier matching:** exact → alias → tax ID → fuzzy. **Product matching:** code → alias → fuzzy with a numeric-specification guard and margin test. **Low-confidence matches are never auto-accepted** — they go to the human-review queue.
- Keeps original and normalised values together so every transformation is traceable.

---

### 🟢 Stage 4 — RAG Knowledge Base with Citations

<div align="center">

[![Stage4](https://img.shields.io/badge/Stage%204-RAG-2E7D32?style=flat-square&logo=python&logoColor=white)]()
[![Module](https://img.shields.io/badge/Module-rag%2Fkb.py-green?style=flat-square)]()
[![Index](https://img.shields.io/badge/Index-FAISS%20%2B%20BM25-green?style=flat-square)]()
[![Retrieval](https://img.shields.io/badge/Retrieval-Hybrid%20(RRF)-green?style=flat-square)]()

</div>

#### 📌 Task Description

> Attach the **actual contract or policy passage** to each finding — or say that no evidence was found.

**What this stage does:**
- Section-aware chunking with configurable size and overlap; price schedules are chunked by row.
- **Dense (FAISS) + keyword (BM25) hybrid retrieval** with reciprocal-rank fusion and supplier / document-type filters.
- Offline **TF-IDF lexical embeddings by default** (no download, no paid API); a local sentence-transformers option is available.
- Every citation is **verifiable** (`verify_citation` re-checks the snippet against the source file). Invented quotations are rejected; empty retrieval returns *evidence not found*.
- Retrieved text is treated as **untrusted data**: injection-like patterns are flagged and never obeyed.

---

### 🔴 Stage 5 — Deterministic Audit Engine

<div align="center">

[![Stage5](https://img.shields.io/badge/Stage%205-Audit%20Engine-C62828?style=flat-square&logo=python&logoColor=white)]()
[![Module](https://img.shields.io/badge/Module-audit%2Fengine.py-red?style=flat-square)]()
[![Math](https://img.shields.io/badge/Money-Decimal%20ROUND__HALF__UP-red?style=flat-square)]()
[![Findings](https://img.shields.io/badge/Finding%20types-28-red?style=flat-square)]()

</div>

#### 📌 Task Description

> Decide what is wrong with an invoice using **explicit, explainable, testable rules** — no LLM in the loop.

**What this stage checks:**

| Category | Checks |
|----------|--------|
| 💰 Pricing | Unit price above contract · wrong volume discount · agreement effective on PO date · currency mismatch |
| 📦 Quantities | Invoiced > ordered · invoiced > received (cumulative, partial deliveries aggregated) · PO/DC conflicts |
| 🔁 Duplicates | Exact (supplier + OCR-tolerant invoice number) vs. possible (same PO and economics) |
| 🧮 Arithmetic & tax | Line amount · line tax · header subtotal / tax / grand total · tax rate vs. synthetic policy · missing tax info |
| 🚚 Charges | Unauthorised surcharges · freight above the agreed cap |
| 📄 Documents & identity | Missing PO · missing delivery record · unknown or ambiguous product · unknown supplier · inconsistent supplier details · inconsistent dates / references |

**Design rules:**
- **Statuses:** `CONFIRMED`, `POTENTIAL`, `INSUFFICIENT_EVIDENCE`, `MANUAL_REVIEW`, `PASSED`. A **missing delivery record is never proof of non-delivery**; a missing policy passage is never proof of a violation.
- **Rounding:** `ROUND_HALF_UP` to 0.01 at every step; configurable tolerances (line 0.01, header 0.05). No binary floats in validation.
- **Exposure without double counting:** all findings on one line share an `exposure_key`; totals count each key once and report *confirmed* and *potential* exposure separately.
- **OCR-aware:** findings that rely on low-confidence extraction or OCR-derived PO/DC evidence are **downgraded to POTENTIAL** and routed to review.

---

### 🟡 Stage 6 — Multi-Agent Workflow & Reporting

<div align="center">

[![Stage6](https://img.shields.io/badge/Stage%206-Agents-F9A825?style=flat-square&logo=python&logoColor=white)]()
[![Module](https://img.shields.io/badge/Module-agents%20%C2%B7%20reporting-yellow?style=flat-square)]()
[![Graph](https://img.shields.io/badge/Orchestration-LangGraph-yellow?style=flat-square)]()

</div>

#### 📌 Task Description

> Orchestrate the four agents with shared state, conditional routing and graceful failure.

- Real **LangGraph** nodes: `ingest → evidence → audit → (human_review) → report`, with a conditional edge to the review node.
- **Per-node error handling:** a failing node records the error and routes to the report, so callers always receive a (possibly partial) report. A sequential fallback with the same contract is used if LangGraph is missing.
- The `human_review` node **only builds a queue** — it triggers no external action and no payment.
- Reports include audit ID, timestamp, linked PO / delivery records, severity, expected vs. observed values, estimated exposure, evidence references, extraction confidence, unresolved questions, recommended actions and review status.

---

### ⚪ Stage 7 — REST API & Streamlit Dashboard

<div align="center">

[![Stage7](https://img.shields.io/badge/Stage%207-API%20%26%20UI-455A64?style=flat-square&logo=fastapi&logoColor=white)]()
[![API](https://img.shields.io/badge/API-FastAPI-455A64?style=flat-square)]()
[![UI](https://img.shields.io/badge/UI-Streamlit-455A64?style=flat-square)]()
[![DB](https://img.shields.io/badge/Storage-SQLite-455A64?style=flat-square)]()

</div>

- **FastAPI:** Pydantic request/response models, meaningful status codes, optional `X-API-Key`, SQLite persistence (**paths and hashes only — never file contents**), background audit runs.
- **Streamlit dashboard:** multi-file upload, document preview, severity/status filters, evidence viewer with the cited source, review queue, and JSON / Markdown / CSV / Excel downloads. Works in-process or against the API. The Gemini key never reaches the browser.

---

## 🔗 Request Lifecycle

```
╔════════════════════════════════════════════════════════════════════════════════════════════════╗
║                    POST /audits  —  WHAT HAPPENS TO AN AUDIT REQUEST                           ║
╠═══════════════╦═══════════════╦═══════════════╦═══════════════╦═══════════════╦════════════════╣
║  1. UPLOAD    ║  2. EXTRACT   ║  3. EVIDENCE  ║  4. AUDIT     ║  5. REVIEW    ║  6. REPORT     ║
║  validate     ║  text / OCR   ║  agreement +  ║  3-way match  ║  queue for    ║  JSON · MD ·   ║
║  type · size  ║  fields       ║  RAG passages ║  Decimal rules║  humans       ║  CSV · XLSX    ║
╠═══════════════╩═══════════════╩═══════════════╩═══════════════╩═══════════════╩════════════════╣
║           Status: queued → running → completed | completed_with_errors | failed                ║
╚════════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 🌐 API Reference

**Base URL (local):** `http://127.0.0.1:8000` — interactive docs at `/docs`.

| Method | Endpoint | Purpose |
|:------:|----------|---------|
| `GET` | `/health` | Service status, whether an LLM key is configured |
| `POST` | `/documents/upload` | Upload one or more files (PDF, PNG/JPG, TXT, CSV, XLSX, ZIP) |
| `POST` | `/audits` | Start an audit (returns `202` + `audit_id`) |
| `GET` | `/audits/{id}` | Status and summary |
| `GET` | `/audits/{id}/report?format=json\|markdown\|csv\|xlsx` | Download the report |
| `GET` | `/audits/{id}/findings?severity=&status=&code=` | Filter findings |
| `GET` | `/knowledge-base/search?q=&supplier_id=&k=` | Search contracts and policies |
| `GET` | `/metrics` | Counts, timings, LLM usage |

**Windows PowerShell**

```powershell
curl.exe -X POST http://127.0.0.1:8000/documents/upload -F "files=@procuraai-data\raw\invoices\pdf\INV-001_PCH_PCH-0397.pdf"
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/audits -ContentType "application/json" `
  -Body '{"input_mode":"documents","document_ids":["<id from upload>"],"extraction_mode":"rule"}'
```

| HTTP | When |
|---|---|
| 202 | Audit accepted |
| 401 | Missing/invalid `X-API-Key` (only when `PROCURAAI_API_KEY` is set) |
| 404 | Unknown document or audit ID |
| 409 | Report requested before the audit finished |
| 422 | Invalid body, bad file type, empty file, bad filter value |
| 503 | Master data / knowledge base unavailable |

---

## 🔧 Technical Specifications

### 🌍 Data

| Asset | Source |
|-------|--------|
| Documents | Generated locally by `scripts/generate_synthetic_data.py` — fully fictional, labelled SYNTHETIC |
| Structured tables | CSV + `procurement_master_data.xlsx` (observed values, no labels) |
| Ground truth / manifest | `ground_truth/`, `manifest/` — **evaluation only** |

### 🧰 Configuration (environment variables, see `.env.example`)

| Variable | Default | Meaning |
|----------|:-------:|---------|
| `GEMINI_API_KEY` | — | Optional. Enables LLM extraction / explanations |
| `PROCURAAI_GEMINI_MODEL` | `gemini-3.8-flash` | Model name |
| `PROCURAAI_GEMINI_API` | `interactions` | `interactions` (current) or `generate_content` (legacy) |
| `PROCURAAI_API_KEY` | — | If set, the API requires header `X-API-Key` |
| `PROCURAAI_DATA_DIR` | `procuraai-data` | Dataset folder |
| `PROCURAAI_DB_URL` | `sqlite:///procuraai.db` | Persistence |
| `PROCURAAI_MAX_UPLOAD_MB` | `25` | Per-file upload limit |
| `PROCURAAI_LLM_TIMEOUT` / `_RETRIES` | `60` / `3` | LLM call limits |

### 💻 Hardware and Performance

Runs on a normal laptop CPU; no GPU, database server or vector DB service needed. Measured in development:

| Step | Typical time |
|------|-------------|
| Text-layer PDF / TXT extraction | milliseconds per document |
| OCR extraction (image or scanned PDF) | about 5.7 s per document (up to 11 s with retries) |
| Structured audit of all 72 invoices | about 0.65 s |
| Full test suite (54 tests) | about 1–1.5 min |

---

## 🚀 Getting Started

Developed and tested on **Python 3.12**. Windows, macOS and Linux are supported (the OCR engine must be installed separately).

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/umerahmedbaig7/procuraai-invoice-auditor.git
cd procuraai-invoice-auditor
```

### 2️⃣ Install Tesseract OCR

- **Windows:** install the UB Mannheim build (default folder `C:\Program Files\Tesseract-OCR`) and add that folder to `PATH`. Check with `tesseract --version`.
- **Ubuntu/Debian:** `sudo apt-get install -y tesseract-ocr` · **macOS:** `brew install tesseract`

### 3️⃣ Create a Virtual Environment and Install Dependencies

**Windows (PowerShell)**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e . --no-deps
```

> If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**macOS / Linux**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e . --no-deps
```

### 4️⃣ Generate the Synthetic Dataset

```bash
python scripts/generate_synthetic_data.py --out procuraai-data    # ~1-2 min, seed 20250101
```

The output must contain `"checks": "all passed"`. The same data is available as `procuraai_synthetic_dataset.zip` on the Releases page.

### 5️⃣ Verify Everything Offline

```bash
python -m pytest                                                   # 54 tests, no API key or network needed
python scripts/run_evaluation.py --data procuraai-data --out reports/evaluation_local --skip-documents
python scripts/try_audit.py                                        # example audits with clear diagnostics
```

### 6️⃣ Run the API and the Dashboard

```bash
uvicorn procuraai.api.app:app --port 8000     # API docs: http://127.0.0.1:8000/docs
streamlit run app.py                          # dashboard: http://localhost:8501
```

In the dashboard click **Run audit on the sample dataset**, or upload an invoice **together with its PO and delivery note** (otherwise the audit correctly reports them as missing).

### 7️⃣ Optional — Gemini (free tier available)

Everything works without a key. To try LLM extraction and explanations:

1. Create a key at **<https://aistudio.google.com/apikey>** (AI Studio keys start with `AIza`).
2. Put it in `.env` as `GEMINI_API_KEY=...` (or `$env:GEMINI_API_KEY = "..."` in PowerShell).
3. Run `python scripts/check_gemini.py` — it prints the real reason if a key, model or API fails.
4. In the dashboard set *Extraction mode* to `auto`.

> The free tier is rate-limited and Google states that free-tier content may be used to improve its products — use **synthetic or non-confidential documents only**. The report's extraction log shows whether `llm` or a rule-based fallback was used.

### 8️⃣ Docker

```bash
docker compose up --build      # API on :8000, dashboard on :8501
```

### 🩺 Troubleshooting

| Symptom | Fix |
|---------|-----|
| `TesseractNotFoundError` | Install Tesseract and add it to `PATH`; open a new terminal |
| `faiss-cpu` fails to install | Use Python 3.12 (not 3.13) |
| `ModuleNotFoundError: procuraai` | Activate the venv and run `pip install -e . --no-deps` |
| Gemini `404` | Model not available to your key — change `PROCURAAI_GEMINI_MODEL` |
| Gemini `429` | Free-tier rate limit — wait or use a lighter Flash-Lite model |
| Audit says `MISSING_PO` / `MISSING_DC` | Upload the invoice's own PO and delivery note with it |
| Upload rejected as too large | Set `PROCURAAI_MAX_UPLOAD_MB` |

---

## 📊 Key Results Summary

Ground truth is used **only for scoring**. A prediction is an (invoice, finding-code) pair. Numbers are from actual runs of `scripts/run_evaluation.py` (see [`docs/evaluation.md`](docs/evaluation.md)).

| Measure | Structured CSV input | Documents (OCR + extraction) |
|---------|:--------------------:|:----------------------------:|
| TP / FP / FN | 54 / 0 / 0 | 53 / 23 / 1 |
| Precision / Recall / F1 | 1.00 / 1.00 / 1.00 | 0.70 / 0.98 / 0.82 |
| Anomalous invoices flagged | 42 / 42 | 42 / 42 |
| Clean invoices wrongly flagged | 0 / 30 | 4 / 30 |
| False positives that were *confirmed* | 0 | 0 |
| Exposure estimate | matches ground truth | **not reliable** (≈2.53 M PKR vs. 0.84 M expected) |

| Component | Result |
|-----------|--------|
| Extraction field accuracy | **100%** on text-layer PDFs / TXT · **93.7%** on OCR'd images (10 of 22 fully correct) |
| Product matching (description only) | 196 / 196 lines correct on the synthetic catalogue |
| RAG retrieval (hybrid, 70 queries) | Recall@1 **0.986** · Recall@3 **1.0** · MRR **0.993** |
| Citation integrity | 135/135 and 85/85 citations verified against source text |
| Automated tests | **54 passing** (offline) |
| Gemini calls in the evaluation | 0 (no key used; rule-based extraction) |

> **How to read this.** The structured score shows the generator and engine are consistent — they were written together — **not** accuracy on real invoices. The document column is the more informative number, and OCR quality is the weak link.

---

## 🧠 Analysis and Discussion

### 🔵 Why a Deterministic Core and an LLM at the Edges
Money and rules need to be **repeatable and explainable**. Comparisons, rounding, duplicate rules and exposure aggregation are plain Python with documented tolerances. The LLM only reads messy text and explains findings that already exist; it cannot create, change or suppress one, and it has no tools.

### 🟠 Confirmed vs. Suspected
A price above the contract is a **confirmed rule violation**; a missing delivery note is a **question**, not proof of non-delivery. Separating the two avoids accusing suppliers and keeps reviewers focused. Nothing is labelled fraud.

### 🟣 OCR Is the Weak Link — and the System Says So
On images and scans, a misread digit in the invoice *or in the linked PO/delivery note* can look like overbilling. The pipeline measures extraction self-consistency, lowers confidence, and **downgrades such findings to POTENTIAL for human review**. No false positive was confirmed — but exposure totals on the OCR path are inflated and should be treated as a review aid.

### 🟢 Evidence or Silence
Each finding carries the contract clause or policy section that supports it, quoted from the source and re-verifiable. If retrieval finds nothing, the report says *no supporting passage was found* instead of inventing one.

### 🔴 Exposure Without Double Counting
A line with both a price and a quantity problem has **one** disputed amount, not two. Findings on the same line share an exposure key; reports count each key once, and keep confirmed and potential amounts separate.

---

## 🚧 Notes and Limitations

- **Synthetic, template-based documents.** The rule-based extractor understands only the generated layouts; real invoices need the optional Gemini path (invoices only) or a custom extractor, and that path is **unvalidated on real documents**.
- **Reference data is synthetic.** Suppliers, products, contracts and policies are fictional; real data requires your own master tables in the same schema.
- **OCR accuracy** is about 94% field-level on the synthetic scans; real scans will be worse.
- **Single-page documents**, a single currency per invoice (no conversion), prices compared against the agreement effective on the **PO date**.
- **Embeddings are lexical by default** (offline TF-IDF); RAG scores are optimistic because queries share vocabulary with the synthetic documents.
- **Prototype scope:** not production-ready — see Security Considerations.

---

## 🔒 Security Considerations

No secrets in code, reports or logs; `.env` is git-ignored. Uploads are type- and size-checked; ZIPs are extracted defensively; only paths and hashes are stored in the database. Supplier text is treated as untrusted data and the LLM cannot alter findings or approve payments. **Not implemented:** user authentication/SSO, tenant isolation, encryption at rest, malware scanning, quotas, audit logging, retention policies. Do not process confidential documents on a free LLM tier.

---

## 🧰 Tech Stack

<div align="center">

| 🛠️ Tool | 🎯 Role in This Project |
|:-------:|:----------------------:|
| ![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white) | Core language |
| ![FastAPI](https://img.shields.io/badge/-FastAPI-009688?logo=fastapi&logoColor=white) | REST API |
| ![Streamlit](https://img.shields.io/badge/-Streamlit-FF4B4B?logo=streamlit&logoColor=white) | Dashboard |
| ![LangGraph](https://img.shields.io/badge/-LangGraph-1C3C3C) | Multi-agent orchestration |
| ![Pydantic](https://img.shields.io/badge/-Pydantic-E92063?logo=pydantic&logoColor=white) | Schemas and validation |
| ![SQLAlchemy](https://img.shields.io/badge/-SQLAlchemy-D71F00) | SQLite persistence |
| ![FAISS](https://img.shields.io/badge/-FAISS-0467DF) | Vector index (+ BM25 hybrid) |
| ![Tesseract](https://img.shields.io/badge/-Tesseract-3C6EB4) | OCR |
| ![PyMuPDF](https://img.shields.io/badge/-PyMuPDF-D32F2F) | PDF text and rendering |
| ![rapidfuzz](https://img.shields.io/badge/-rapidfuzz-555555) | Fuzzy matching |
| ![Gemini](https://img.shields.io/badge/-Gemini%20API-4285F4?logo=google&logoColor=white) | Optional extraction / explanations |
| ![pytest](https://img.shields.io/badge/-pytest-0A9EDC?logo=pytest&logoColor=white) | 54 offline tests |
| ![Docker](https://img.shields.io/badge/-Docker-2496ED?logo=docker&logoColor=white) | Containerisation |
| ![GitHub Actions](https://img.shields.io/badge/-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white) | CI |

</div>

---

## 🏷️ Keywords

`invoice auditing` · `invoice fraud and anomaly detection` · `three-way matching` · `accounts payable automation` · `procurement compliance` · `purchase order matching` · `goods receipt` · `duplicate invoice detection` · `invoice OCR` · `document intelligence` · `retrieval-augmented generation` · `RAG` · `LangGraph` · `multi-agent workflow` · `Gemini API` · `FastAPI` · `Streamlit` · `financial reconciliation` · `FAISS` · `Pydantic` · `synthetic data`

---

## 👤 Author

<div align="center">

### Umer Ahmed Baig Mughal

🎓 **MSc Robotics and Artificial Intelligence** — ITMO University <br>
🔬 *Focus: AI Engineering · LLM Applications · Backend APIs · Document Intelligence · Autonomous Systems*

[![GitHub](https://img.shields.io/badge/GitHub-umerahmedbaig7-181717?style=for-the-badge&logo=github)](https://github.com/umerahmedbaig7)

</div>

---

## 📄 License

Released under the **MIT License** (see [`LICENSE`](LICENSE)). All data in this repository is synthetic; tax rates and policies are illustrative configuration, not legal or tax advice.

---

<div align="center">

*ProcuraAI | Three-Way Matching · RAG · LangGraph · FastAPI · Streamlit*

⭐ *If this repository helped you, consider giving it a star!* ⭐

</div>
