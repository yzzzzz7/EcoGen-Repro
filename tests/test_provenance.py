import contextlib
import gzip
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from ecogen_repro.cli import main
from ecogen_repro.core import (
    ReproError, check, freeze, guarded_run, read_json, snapshot,
    verify_receipt, vcf_samples,
)
from ecogen_repro.demo import run_demo as run_walkthrough
from ecogen_repro.report import write_report


VCF = ("##fileformat=VCFv4.2\n"
       "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\tS2\n"
       "chr1\t10\t.\tA\tC\t.\tPASS\t.\tGT\t0/1\t0/0\n")


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        # Keep workstation QA under the project; CI uses the same layout.
        qa = Path(__file__).resolve().parents[1] / "qa"
        qa.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=qa)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "final.vcf").write_text(VCF, encoding="utf-8")
        (self.root / "samples.txt").write_text("S1\nS2\n", encoding="utf-8")
        (self.root / "analysis.py").write_text(
            "from pathlib import Path\nPath('result.txt').write_text('synthetic output')\n",
            encoding="utf-8")
        self.spec = {"schema_version": 1, "project": "synthetic-population",
                     "method": {"name": "synthetic-demo", "version": "1"},
                     "parameters": {"seed": 42, "projection": 4},
                     "inputs": [{"id": "final", "path": "final.vcf", "format": "vcf"},
                                {"id": "samples", "path": "samples.txt", "format": "samples"},
                                {"id": "code", "path": "analysis.py"}],
                     "sample_scope": {"vcf": "final", "samples": "samples", "mode": "exact"}}
        self.config = self.root / "config.json"
        self.lock = self.root / "lock.json"
        self.receipt = self.root / "receipt.json"
        self.save_spec()

    def save_spec(self):
        self.config.write_text(json.dumps(self.spec), encoding="utf-8")

    def run_demo(self):
        return guarded_run(self.lock, [sys.executable, "analysis.py"],
                           ["result.txt"], self.receipt)

    def test_roundtrip_lock(self):
        freeze(self.config, self.lock)
        record, _ = check(self.lock)
        self.assertEqual(record["state"]["inputs"]["final"]["samples"], ["S1", "S2"])

    def test_vcf_content_drift(self):
        freeze(self.config, self.lock)
        with (self.root / "final.vcf").open("a") as handle:
            handle.write("chr1\t20\t.\tA\tG\t.\tPASS\t.\tGT\t1/1\t0/1\n")
        with self.assertRaisesRegex(ReproError, "input:final"):
            check(self.lock)

    def test_config_parameter_drift(self):
        freeze(self.config, self.lock)
        self.spec["parameters"]["seed"] = 43
        self.save_spec()
        with self.assertRaisesRegex(ReproError, "configuration"):
            check(self.lock)

    def test_script_drift(self):
        freeze(self.config, self.lock)
        (self.root / "analysis.py").write_text("raise RuntimeError('changed')")
        with self.assertRaisesRegex(ReproError, "input:code"):
            check(self.lock)

    def test_sample_order_is_significant(self):
        (self.root / "samples.txt").write_text("S2\nS1\n")
        with self.assertRaisesRegex(ReproError, "order differ"):
            freeze(self.config, self.lock)

    def test_duplicate_samples_rejected(self):
        (self.root / "samples.txt").write_text("S1\nS1\n")
        with self.assertRaisesRegex(ReproError, "Duplicate sample"):
            snapshot(self.config)

    def test_subset_requires_reason(self):
        (self.root / "samples.txt").write_text("S1\n")
        self.spec["sample_scope"]["mode"] = "subset"
        self.save_spec()
        with self.assertRaisesRegex(ReproError, "reason"):
            snapshot(self.config)

    def test_documented_subset(self):
        (self.root / "samples.txt").write_text("S1\n")
        self.spec["sample_scope"].update(mode="subset", reason="Declared high-depth subset")
        self.save_spec()
        freeze(self.config, self.lock)
        check(self.lock)

    def test_missing_subset_sample_rejected(self):
        (self.root / "samples.txt").write_text("S3\n")
        self.spec["sample_scope"].update(mode="subset", reason="Example")
        self.save_spec()
        with self.assertRaisesRegex(ReproError, "absent"):
            snapshot(self.config)

    def test_gzip_vcf(self):
        with gzip.open(self.root / "final.vcf.gz", "wt") as handle:
            handle.write(VCF)
        self.spec["inputs"][0]["path"] = "final.vcf.gz"
        self.save_spec()
        freeze(self.config, self.lock)
        check(self.lock)

    def test_bad_vcf_header(self):
        (self.root / "final.vcf").write_text("not a VCF\n")
        with self.assertRaisesRegex(ReproError, "fileformat"):
            vcf_samples(self.root / "final.vcf")

    def test_duplicate_vcf_samples(self):
        (self.root / "final.vcf").write_text(VCF.replace("\tS2", "\tS1"))
        with self.assertRaisesRegex(ReproError, "Duplicate VCF"):
            snapshot(self.config)

    def test_duplicate_json_keys(self):
        self.config.write_text('{"schema_version": 1, "schema_version": 2}')
        with self.assertRaisesRegex(ReproError, "Duplicate JSON key"):
            read_json(self.config)

    def test_nonfinite_json(self):
        self.config.write_text('{"parameter": NaN}')
        with self.assertRaisesRegex(ReproError, "Non-finite"):
            read_json(self.config)

    def test_unknown_format_rejected(self):
        self.spec["inputs"][0]["format"] = "guess"
        self.save_spec()
        with self.assertRaisesRegex(ReproError, "Unsupported"):
            snapshot(self.config)

    def test_missing_input(self):
        (self.root / "final.vcf").unlink()
        with self.assertRaises(FileNotFoundError):
            snapshot(self.config)

    def test_lock_not_overwritten(self):
        freeze(self.config, self.lock)
        original = self.lock.read_bytes()
        with self.assertRaises(FileExistsError):
            freeze(self.config, self.lock)
        self.assertEqual(original, self.lock.read_bytes())

    def test_successful_command_and_receipt(self):
        freeze(self.config, self.lock)
        result = self.run_demo()
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(verify_receipt(self.receipt)["command"], [sys.executable, "analysis.py"])

    def test_stale_input_prevents_execution(self):
        freeze(self.config, self.lock)
        (self.root / "analysis.py").write_text("raise RuntimeError('should not run')")
        with self.assertRaisesRegex(ReproError, "Provenance drift"):
            self.run_demo()
        self.assertFalse((self.root / "result.txt").exists())
        self.assertFalse(self.receipt.exists())

    def test_input_changed_by_command_has_no_receipt(self):
        (self.root / "analysis.py").write_text(
            "from pathlib import Path\nPath('samples.txt').write_text('S1\\n')\n"
            "Path('result.txt').write_text('not acceptable')\n")
        freeze(self.config, self.lock)
        with self.assertRaises(ReproError):
            self.run_demo()
        self.assertFalse(self.receipt.exists())

    def test_failed_command_has_no_receipt(self):
        freeze(self.config, self.lock)
        with self.assertRaisesRegex(ReproError, "exit code 7"):
            guarded_run(self.lock, [sys.executable, "-c", "raise SystemExit(7)"],
                        ["result.txt"], self.receipt)
        self.assertFalse(self.receipt.exists())

    def test_preexisting_output_is_not_attested(self):
        freeze(self.config, self.lock)
        (self.root / "result.txt").write_text("historical result")
        with self.assertRaisesRegex(ReproError, "existing output"):
            self.run_demo()

    def test_output_change_invalidates_receipt(self):
        freeze(self.config, self.lock)
        self.run_demo()
        (self.root / "result.txt").write_text("changed")
        with self.assertRaisesRegex(ReproError, "Output changed"):
            verify_receipt(self.receipt)

    def test_receipt_does_not_validate_stale_inputs(self):
        freeze(self.config, self.lock)
        self.run_demo()
        self.spec["parameters"]["projection"] = 2
        self.save_spec()
        with self.assertRaisesRegex(ReproError, "Provenance drift"):
            verify_receipt(self.receipt)

    def test_tampered_record_rejected(self):
        freeze(self.config, self.lock)
        record = read_json(self.lock)
        record["state"]["spec"]["parameters"]["seed"] = 99
        self.lock.write_text(json.dumps(record))
        with self.assertRaisesRegex(ReproError, "integrity"):
            check(self.lock)

    def test_portable_project(self):
        freeze(self.config, self.lock)
        self.run_demo()
        destination = self.root / "relocated"
        destination.mkdir()
        for name in ["config.json", "final.vcf", "samples.txt", "analysis.py",
                     "lock.json", "receipt.json", "result.txt"]:
            shutil.copy2(self.root / name, destination / name)
        verify_receipt(destination / "receipt.json")

    def test_cli_end_to_end(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["lock", str(self.config), "--out", str(self.lock)]), 0)
            self.assertEqual(main(["run", str(self.lock), "--output", "result.txt",
                                   "--receipt", str(self.receipt), "--", sys.executable,
                                   "analysis.py"]), 0)
            self.assertEqual(main(["verify", str(self.receipt)]), 0)

    def test_cli_failure_exit_code(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["check", str(self.lock)]), 1)

    def test_report_verifies_and_escapes_user_content(self):
        self.spec["project"] = '<script>alert("project")</script>'
        self.save_spec()
        freeze(self.config, self.lock)
        self.run_demo()
        report = self.root / "report.html"
        write_report(self.receipt, report)
        text = report.read_text(encoding="utf-8")
        self.assertIn("PASS — provenance verified", text)
        self.assertIn("&lt;script&gt;", text)
        self.assertNotIn("<script>", text)
        self.assertIn("Content-Security-Policy", text)
        self.assertIn("S1\nS2", text)

    def test_report_rejects_stale_run_without_writing(self):
        freeze(self.config, self.lock)
        self.run_demo()
        (self.root / "result.txt").write_text("changed")
        report = self.root / "report.html"
        with self.assertRaisesRegex(ReproError, "Output changed"):
            write_report(self.receipt, report)
        self.assertFalse(report.exists())

    def test_report_never_overwrites_existing_file(self):
        freeze(self.config, self.lock)
        self.run_demo()
        report = self.root / "report.html"
        report.write_text("user-owned content")
        with self.assertRaises(FileExistsError):
            write_report(self.receipt, report)
        self.assertEqual(report.read_text(), "user-owned content")

    def test_report_without_sample_scope(self):
        self.spec.pop("sample_scope")
        self.save_spec()
        freeze(self.config, self.lock)
        self.run_demo()
        report = self.root / "report.html"
        write_report(self.receipt, report)
        self.assertIn("No sample-scope check was declared", report.read_text(encoding="utf-8"))

    def test_walkthrough_rejects_drift_and_restores_its_files(self):
        directory = self.root / "walkthrough"
        result = run_walkthrough(directory)
        self.assertEqual(result["cases_passed"], 6)
        cases = read_json(directory / "demo-results.json")["cases"]
        self.assertEqual(len(cases), 6)
        self.assertEqual(sum(row["observed"] == "REJECT" for row in cases), 4)
        self.assertTrue(all(row["expected"] == row["observed"] for row in cases))
        verify_receipt(directory / "receipt.json")
        self.assertTrue((directory / "report.html").is_file())

    def test_walkthrough_refuses_nonempty_directory(self):
        original = self.config.read_bytes()
        with self.assertRaisesRegex(ReproError, "new or empty"):
            run_walkthrough(self.root)
        self.assertEqual(self.config.read_bytes(), original)

    def test_cli_walkthrough_and_report(self):
        directory = self.root / "walkthrough"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["demo", "--out", str(directory)]), 0)
            self.assertEqual(main(["report", str(directory / "receipt.json"),
                                   "--out", str(directory / "second-report.html")]), 0)
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(records[0]["cases_passed"], 6)
        self.assertTrue(Path(records[1]["report"]).is_file())

    def test_truncated_gzip_has_structured_cli_error(self):
        (self.root / "final.vcf.gz").write_bytes(gzip.compress(VCF.encode())[:8])
        self.spec["inputs"][0]["path"] = "final.vcf.gz"
        self.save_spec()
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            self.assertEqual(main(["lock", str(self.config), "--out", str(self.lock)]), 1)
        self.assertEqual(json.loads(error.getvalue())["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
