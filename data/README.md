# Data

The synthetic dataset is **generated, not committed** (about 60 MB of PDFs/images). Options:

1. **Generate on demand (recommended):** `python scripts/generate_synthetic_data.py --out procuraai-data` (about 1 minute, fixed seed 20250101, byte-for-byte reproducible labels).
2. **GitHub Release asset:** attach `procuraai_synthetic_dataset.zip` (created by the script next to the output folder) to a release.
3. Docker: the container generates the dataset on first start if `/data/procuraai-data` is missing.

Everything is fictional and labelled SYNTHETIC. Tax rates and policies are synthetic configuration, **not** Pakistani tax law.

## Layout
```
procuraai-data/
  raw/invoices/{pdf,images,text}   raw/purchase_orders/{pdf,images}   raw/delivery_challans/{pdf,images}
  raw/contracts  raw/policies      (PDF + TXT; the RAG index is built from these)
  structured/    CSV + procurement_master_data.xlsx + document_registry.csv   (observed values, NO labels)
  ground_truth/  ground_truth.csv, expected_values.csv                        (EVALUATION ONLY)
  manifest/      dataset_manifest.csv/.json (file inventory with labels)       (EVALUATION ONLY)
  processed/ reports/                                                          (pipeline outputs)
```
Ground truth must never be passed to the agents; only `procuraai.evaluation` and the tests read it.
