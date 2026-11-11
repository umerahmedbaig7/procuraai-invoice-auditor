"""Shared services: master data, knowledge base, LLM client, configuration. Independent of Google Colab."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .audit.engine import MasterData
from .config import AuditConfig, Settings
from .extraction.llm import GeminiClient
from .extraction.structured import load_structured_dir
from .rag.kb import KnowledgeBase, make_embedder

log = logging.getLogger("procuraai")


@dataclass
class Services:
    master: MasterData
    kb: KnowledgeBase
    cfg: AuditConfig = field(default_factory=AuditConfig)
    llm: object | None = None                 # GeminiClient | MockLLM | None
    data_dir: Path | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def llm_available(self) -> bool:
        return bool(self.llm and getattr(self.llm, "available", False))


def load_services(data_dir: str | Path, settings: Settings | None = None, prefer_semantic: bool = False, llm=None, cfg: AuditConfig | None = None) -> Services:
    """Load master data from <data_dir>/structured and build the RAG index from <data_dir>/raw/{contracts,policies}.
    The LLM client is created only if GEMINI_API_KEY is present; otherwise ``llm`` is None and callers use fallbacks."""
    settings = settings or Settings()
    d = Path(data_dir)
    if not (d / "structured").exists():
        raise FileNotFoundError(f"{d}/structured not found - generate the dataset first (scripts/generate_synthetic_data.py)")
    S = load_structured_dir(d / "structured")
    master = MasterData(S["suppliers"], S["products"], S["agreements"], S["price_list"], S["policies"])
    emb, note = make_embedder(prefer_semantic, settings.embedding_model)
    kb = KnowledgeBase(embedder=emb)
    n = kb.add_directory(d / "raw")
    kb.build()
    notes = [f"knowledge base: {n} chunks, embedder = {emb.name}"] + ([note] if note else [])
    if llm is None and settings.gemini_api_key:
        llm = GeminiClient(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_s, settings.llm_max_retries)
    notes.append("LLM: " + ("Gemini client configured" if llm else "not configured (GEMINI_API_KEY not set) - rule-based extraction and template explanations are used"))
    return Services(master=master, kb=kb, cfg=cfg or AuditConfig(), llm=llm, data_dir=d, notes=notes)
