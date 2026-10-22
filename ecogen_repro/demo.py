"""An offline, synthetic walkthrough that works from an installed wheel."""

import sys
from pathlib import Path

from .core import ReproError, check, freeze, guarded_run, verify_receipt, write_new_json
from .report import write_report


VCF = ("##fileformat=VCFv4.2\n##source=EcoGen-Repro-synthetic-demo\n"
       "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tDEMO_01\tDEMO_02\n"
       "chrDemo\t10\t.\tA\tC\t.\tPASS\t.\tGT\t0/1\t0/0\n")
SCRIPT = '''"""Synthetic I/O example, not a biological estimator."""
import json
from pathlib import Path
config = json.loads(Path("config.json").read_text(encoding="utf-8"))
result = {"synthetic_only": True, "seed": config["parameters"]["seed"],
          "selected_samples": Path("samples.txt").read_text(encoding="utf-8").splitlines()}
Path("summary.json").write_text(json.dumps(result, indent=2) + "\\n", encoding="utf-8")
'''


def run_demo(output):
    """Create only an explicitly named new/empty directory; preserve existing files."""
    if not Path(sys.executable).is_file():
        raise ReproError("The demo requires a normal Python executable; this embedded launcher reports a directory")
    output = Path(output)
    if output.is_symlink():
        raise ReproError("Demo destination must not be a symbolic link")
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise ReproError("Demo destination must be new or empty")
    else:
        output.mkdir()
    config = output / "config.json"
    lock = output / "lock.json"
    receipt = output / "receipt.json"
    for name, text in [("final.vcf", VCF), ("samples.txt", "DEMO_01\nDEMO_02\n"),
                       ("summarize.py", SCRIPT)]:
        with (output / name).open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    spec = {"schema_version": 1, "project": "synthetic-provenance-demo",
            "method": {"name": "synthetic-io-summary", "version": "1"},
            "parameters": {"seed": 42},
            "inputs": [{"id": "final_vcf", "path": "final.vcf", "format": "vcf"},
                       {"id": "selected_samples", "path": "samples.txt", "format": "samples"},
                       {"id": "analysis_code", "path": "summarize.py"}],
            "sample_scope": {"vcf": "final_vcf", "samples": "selected_samples", "mode": "exact"}}
    write_new_json(config, spec)
    freeze(config, lock)
    check(lock)
    guarded_run(lock, [sys.executable, "summarize.py"], ["summary.json"], receipt)
    verify_receipt(receipt)
    cases = [{"case": "unchanged_run", "expected": "PASS", "observed": "PASS"}]

    def expect_rejection(name, path, changed, verify):
        original = path.read_bytes()
        try:
            path.write_bytes(changed)
            try:
                verify()
            except ReproError as exc:
                cases.append({"case": name, "expected": "REJECT", "observed": "REJECT", "reason": str(exc)})
            else:
                raise ReproError(f"Demo failed to reject {name}")
        finally:
            path.write_bytes(original)

    expect_rejection("changed_vcf", output / "final.vcf",
                     VCF.encode() + b"chrDemo\t20\t.\tG\tT\t.\tPASS\t.\tGT\t0/1\t1/1\n",
                     lambda: check(lock))
    expect_rejection("changed_sample_order", output / "samples.txt",
                     b"DEMO_02\nDEMO_01\n", lambda: check(lock))
    expect_rejection("changed_parameter", config,
                     config.read_bytes().replace(b'"seed": 42', b'"seed": 43'), lambda: check(lock))
    expect_rejection("changed_output", output / "summary.json",
                     b'{"modified": true}\n', lambda: verify_receipt(receipt))
    verify_receipt(receipt)
    cases.append({"case": "restored_files", "expected": "PASS", "observed": "PASS"})
    report = write_report(receipt, output / "report.html")
    results = {"synthetic_only": True, "cases": cases,
               "interpretation": "Expected rejections are successful software checks, not scientific validation."}
    write_new_json(output / "demo-results.json", results)
    return {"directory": str(output), "cases_passed": len(cases), **report}
