"""Synthetic I/O demonstration, not a population-genetic estimator."""
import hashlib
import json
from pathlib import Path

raw = Path("final.vcf").read_bytes()
samples = Path("samples.txt").read_text(encoding="utf-8").splitlines()
Path("summary.json").write_text(json.dumps({
    "demonstration_only": True,
    "input_sha256": hashlib.sha256(raw).hexdigest(),
    "selected_samples": samples,
}, indent=2) + "\n", encoding="utf-8")
