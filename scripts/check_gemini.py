#!/usr/bin/env python
"""Diagnose the Gemini connection and print the REAL error (key redacted).
Run:  python scripts/check_gemini.py
"""
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from procuraai.config import Settings
from procuraai.extraction.llm import GeminiClient

s = Settings()
key = s.gemini_api_key
print("GEMINI_API_KEY set:", bool(key))
if not key:
    sys.exit("Set it first, e.g. PowerShell:  $env:GEMINI_API_KEY = '<your key>'")
shape = "Gemini Developer API key (AIza...)" if key.startswith("AIza") else "Vertex AI express-mode key (AQ....)" if key.startswith("AQ.") else "unrecognised format"
print(f"key length {len(key)}, looks like: {shape}   model: {s.gemini_model}\n")
for vertex in ("0", "1"):
    os.environ["PROCURAAI_GEMINI_VERTEX"] = vertex
    ok, msg = GeminiClient(key, s.gemini_model, 30, 1).ping()
    print(f"[{'Vertex endpoint' if vertex == '1' else 'Gemini Developer API endpoint'}] {msg}\n")
print("If one endpoint says OK, use it:  for Vertex set  $env:PROCURAAI_GEMINI_VERTEX = '1'  before starting the app.")
print("If both fail with 400/403: create a new key at https://aistudio.google.com/apikey and/or set  $env:PROCURAAI_GEMINI_MODEL  to a model your key can use.")
