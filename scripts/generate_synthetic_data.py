#!/usr/bin/env python
"""Regenerate the ProcuraAI synthetic dataset deterministically.

Usage: python scripts/generate_synthetic_data.py --out procuraai-data --seed 20250101
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from procuraai.datagen.catalog import ELECTRICAL_PKR  # noqa: E402
from procuraai.datagen.export import write_dataset  # noqa: E402
from procuraai.datagen.generator import generate  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="procuraai-data")
    ap.add_argument("--seed", type=int, default=20250101)
    ap.add_argument("--clean", type=int, default=22, help="number of standalone clean invoices")
    a = ap.parse_args()
    ds = generate(ELECTRICAL_PKR, seed=a.seed, n_clean=a.clean)
    print(json.dumps(write_dataset(ds, a.out), indent=2))
