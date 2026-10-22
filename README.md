# EcoGen-Repro

**Catch stale research results before they enter the next analysis.**

EcoGen-Repro is a small command-line tool that binds a research run to its declared input files, parameters, analysis scripts, and sample scope. It checks those inputs before and after an explicit command and records hashes of newly produced outputs.

Status: **0.1.0 alpha**. The public examples use synthetic data. External adoption, large-file benchmarks, and scientific validation are not established.

## The problem

A pipeline can finish successfully while using an outdated sample list or an earlier filtered VCF. A folder called `COMPLETE` does not identify which data produced its outputs. This becomes difficult to audit when results move between a workstation and a shared computing cluster.

EcoGen-Repro provides a small provenance gate that can be added to an existing script. It preserves the researcher's analysis command and scientific method.

## What it checks

- SHA256 of every declared input, including code, reference files, masks, or tables.
- Exact configuration bytes and declared method/version/parameters.
- Ordered VCF-header sample IDs against a one-ID-per-line sample list.
- Explicitly documented sample subsets when `mode` is `subset`.
- Input identity before and after execution, command exit status, and output hashes.
- Receipt validity against both current inputs and current outputs.

All core operations use the Python standard library. No API key, cloud account, or network connection is required at runtime.

## Install

Python 3.10 or later is required. From a checkout:

```sh
python -m pip install .
ecogen-repro --version
```

Without installation, use `python -m ecogen_repro` from the repository root. The commands below use that form. Package installation requires setuptools; it is a build dependency, not a runtime dependency.

## Try the synthetic example

Run from the repository root:

```sh
python -m ecogen_repro lock examples/config.json --out examples/lock.json
python -m ecogen_repro check examples/lock.json
python -m ecogen_repro run examples/lock.json --output summary.json --receipt examples/receipt.json -- python summarize.py
python -m ecogen_repro verify examples/receipt.json
```

Each successful command prints a JSON object with `"status": "PASS"` and exits with code 0. A failed check prints an error and exits with code 1. The demonstration writes `examples/summary.json`; it is a synthetic I/O summary, not an estimator.

After completing the example, edit `seed` in `examples/config.json` and run `check` again. It fails with `Provenance drift: configuration`. Restore the original configuration to continue verifying the original run. Changing declared code or input content also invalidates the lock. To adopt new inputs, review them and create a **new** lock and a **new** receipt; existing files are never overwritten by these commands.

Output paths passed with `--output` are relative to the **configuration's directory**. Receipt and lock arguments are relative to the invoking working directory. The analysis command runs in the configuration's directory. Parent output directories must already exist. Existing outputs are rejected so historical files cannot receive a new-run receipt accidentally.

## Use your own inputs

Start from [examples/config.json](examples/config.json). Give the project its actual population or dataset identifier. Declare every dependency that matters to interpretation: the final filtered VCF, selected sample list, reference, BED masks, analysis script, and a software-environment lockfile where available.

`format` is one of `file`, `vcf`, or `samples`. Generic `file` inputs are hashed without interpretation. The optional `sample_scope` compares one VCF input to one sample-list input:

```json
"sample_scope": {
  "vcf": "final_vcf",
  "samples": "selected_samples",
  "mode": "subset",
  "reason": "Documented high-depth subset for this analysis"
}
```

`exact` requires identical sample IDs and order. `subset` requires every selected ID to occur in the final VCF and a nonempty reason; the selected order is recorded as supplied. Use separate configurations for analyses with different sample scopes. The tool does not decide whether a subset or projection is scientifically appropriate.

For existing R, Python, or command-line analyses, replace `python summarize.py` with the actual trusted command. List every expected new output with a separate `--output`. The command receives arguments directly, without an intermediate shell. A scheduler can invoke the same CLI inside its existing job script; EcoGen-Repro does not submit jobs itself.

## Scope and interpretation

Passing means that declared files matched a lock at the observed checks and that a successful command produced the recorded output files. It does not establish scientific validity or prove that the command used every declared input.

- `method.version` is a researcher declaration, not automatic verification of an installed R package or external executable. Include an environment lockfile and actual version/diagnostic logs as declared artifacts when they matter.
- VCF sample checking reads the header. BCF is unsupported. This release does not validate all VCF records, genotype filters, BED coordinates, reference compatibility, or SFS projection.
- Hashing reads full file bytes, including compressed bytes. Recompression changes identity. Hashing large files incurs storage I/O and should run where those files reside; large-file performance has not been benchmarked.
- Files should be immutable during execution. Before/after checks cannot detect every concurrent or transient modification. A lock is not a filesystem snapshot or a process sandbox.
- Record checksums detect accidental edits; they are not digital signatures or protection against an adversary who can rewrite records and hashes.
- Paths and sample IDs are stored in lock/receipt records. Review records before sharing. The tool sends no telemetry.

## Relationship to other tools

[DVC](https://doc.dvc.org/start) provides data versioning and pipelines; [Snakemake](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html) provides workflow rules and execution. EcoGen-Repro focuses on a small explicit input lock, sample-scope checks, and portable run receipts. It can sit beside existing workflows. No novelty or superiority over these projects is claimed.

## Development

```sh
python -m unittest discover -s tests -v
```

Tests exercise provenance drift, changed sample order, documented subsets, compressed VCF headers, failed commands, stale output rejection, receipt invalidation, and relocation of a complete project. The GitHub Actions workflow requests Python 3.10, 3.12, and 3.13 on Linux and Windows; workflow configuration alone is not evidence that those runs passed.

See [CONTRIBUTING.md](CONTRIBUTING.md), [docs/FORMAT.md](docs/FORMAT.md), and [ROADMAP.md](ROADMAP.md). Bug reports with small synthetic reproductions are welcome.

## License

MIT. All bundled example data are synthetic and distributed under the same license. This repository contains newly written software and does not redistribute data or code from the separate panda manuscript repository.
