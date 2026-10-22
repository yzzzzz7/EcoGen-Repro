"""Small, standard-library provenance primitives for local or HPC pipelines."""

import gzip
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__


class ReproError(ValueError):
    """A provenance requirement was not satisfied."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def read_json(path):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ReproError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ReproError(f"Non-finite JSON value: {value}")

    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle, object_pairs_hook=unique_keys,
                         parse_constant=invalid_constant)


def write_new_json(path, value):
    """Never overwrite an input, lock, receipt, or user-owned file."""
    text = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def file_hash(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def signature(path):
    stat = Path(path).stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino


def sample_ids(path):
    ids = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if not ids or any(not s or s != s.strip() or any(c.isspace() for c in s)
                      for s in ids):
        raise ReproError("Sample lists require one nonempty ID per line, without whitespace")
    if len(set(ids)) != len(ids):
        raise ReproError("Duplicate sample IDs")
    return ids


def vcf_samples(path):
    """Read only a VCF header, preserving sample order; not a VCF validator."""
    opener = gzip.open if str(path).lower().endswith((".gz", ".bgz")) else open
    fixed = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT"]
    with opener(path, "rt", encoding="utf-8-sig") as handle:
        first = handle.readline().rstrip("\r\n")
        if not first.startswith("##fileformat=VCFv4."):
            raise ReproError("Expected a VCFv4 fileformat header")
        for line in handle:
            if line.startswith("##"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if fields[:9] != fixed or len(fields) < 10:
                raise ReproError("Expected a tab-delimited VCF header with samples")
            ids = fields[9:]
            if any(not s or any(c.isspace() for c in s) for s in ids):
                raise ReproError("Invalid VCF sample ID")
            if len(set(ids)) != len(ids):
                raise ReproError("Duplicate VCF sample IDs")
            return ids
    raise ReproError("VCF #CHROM header not found")


def snapshot_file(path, kind="file"):
    path = Path(path).resolve(strict=True)
    before = signature(path)
    result = {"sha256": file_hash(path), "bytes": before[0]}
    if kind == "vcf":
        result["samples"] = vcf_samples(path)
    elif kind == "samples":
        result["samples"] = sample_ids(path)
    elif kind != "file":
        raise ReproError(f"Unsupported input format: {kind}")
    if signature(path) != before:
        raise ReproError(f"File changed while reading: {path}")
    return result


def snapshot(config):
    config = Path(config).resolve(strict=True)
    before = signature(config)
    config_sha = file_hash(config)
    spec = read_json(config)
    if not isinstance(spec, dict) or spec.get("schema_version") != 1:
        raise ReproError("Expected config schema_version 1")
    if not isinstance(spec.get("project"), str) or not spec["project"].strip():
        raise ReproError("A nonempty project identifier is required")
    method = spec.get("method")
    if not isinstance(method, dict) or any(
        not isinstance(method.get(key), str) or not method[key].strip()
        for key in ("name", "version")
    ):
        raise ReproError("Declare method.name and method.version")
    if not isinstance(spec.get("parameters"), dict):
        raise ReproError("Declare a parameters object, even if empty")
    inputs = spec.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise ReproError("Declare at least one input")
    records = {}
    for entry in inputs:
        if not isinstance(entry, dict):
            raise ReproError("Each input must be an object")
        name, rel = entry.get("id"), entry.get("path")
        if not isinstance(name, str) or not name.strip() or name in records:
            raise ReproError("Input IDs must be nonempty and unique")
        if not isinstance(rel, str) or not rel.strip():
            raise ReproError(f"Input {name} requires a path")
        kind = entry.get("format", "file")
        records[name] = {"path": rel, "format": kind,
                         **snapshot_file(config.parent / rel, kind)}
    scope = spec.get("sample_scope")
    if scope is not None:
        if not isinstance(scope, dict):
            raise ReproError("sample_scope must be an object")
        vcf = records.get(scope.get("vcf"))
        selected = records.get(scope.get("samples"))
        if not vcf or vcf["format"] != "vcf" or not selected or selected["format"] != "samples":
            raise ReproError("sample_scope must reference a VCF and a sample-list input")
        mode = scope.get("mode")
        if mode == "exact":
            if vcf["samples"] != selected["samples"]:
                raise ReproError("Sample IDs or order differ from the final VCF")
        elif mode == "subset":
            if not isinstance(scope.get("reason"), str) or not scope["reason"].strip():
                raise ReproError("Subset scope requires an explicit scientific reason")
            if not set(selected["samples"]).issubset(vcf["samples"]):
                raise ReproError("Selected samples are absent from the final VCF")
        else:
            raise ReproError("sample_scope.mode must be exact or subset")
    if signature(config) != before or file_hash(config) != config_sha:
        raise ReproError("Configuration changed while reading")
    return {"config_sha256": config_sha, "spec": spec, "inputs": records}


def seal(record):
    record["record_sha256"] = digest(record)
    return record


def load_record(path, kind):
    record = read_json(path)
    if not isinstance(record, dict):
        raise ReproError("Record must be a JSON object")
    claimed = record.pop("record_sha256", None)
    if claimed != digest(record):
        raise ReproError("Record integrity check failed")
    record["record_sha256"] = claimed
    if record.get("schema_version") != 1 or record.get("kind") != kind:
        raise ReproError(f"Expected a version 1 {kind} record")
    return record


def portable_path(path, parent):
    return Path(os.path.relpath(Path(path).resolve(), Path(parent).resolve())).as_posix()


def freeze(config, output):
    output = Path(output).resolve()
    state = snapshot(config)
    record = seal({"schema_version": 1, "kind": "lock", "tool_version": __version__,
                   "created_utc": utc_now(),
                   "config_path": portable_path(config, output.parent), "state": state})
    write_new_json(output, record)
    return record


def check(lock):
    lock = Path(lock).resolve(strict=True)
    record = load_record(lock, "lock")
    config = (lock.parent / record["config_path"]).resolve(strict=True)
    current = snapshot(config)
    old = record["state"]
    changes = []
    if current["config_sha256"] != old["config_sha256"]:
        changes.append("configuration")
    for name in sorted(set(old["inputs"]) | set(current["inputs"])):
        if old["inputs"].get(name) != current["inputs"].get(name):
            changes.append(f"input:{name}")
    if current != old and not changes:
        changes.append("snapshot")
    if changes:
        raise ReproError("Provenance drift: " + ", ".join(changes))
    return record, config


def guarded_run(lock, command, outputs, receipt):
    """Run an explicit trusted command, checking inputs before and after it."""
    if not command or not outputs:
        raise ReproError("A command and at least one output are required")
    record, config = check(lock)
    lock = Path(lock).resolve(strict=True)
    lock_sha = file_hash(lock)
    receipt = Path(receipt).resolve()
    paths = [(config.parent / p).resolve() for p in outputs]
    if len(set(paths)) != len(paths) or receipt in paths:
        raise ReproError("Outputs and receipt must have distinct paths")
    for path in paths + [receipt]:
        if path.exists() or path.is_symlink():
            raise ReproError(f"Refusing an existing output or receipt: {path}")
        if not path.parent.is_dir():
            raise ReproError(f"Output parent directory does not exist: {path.parent}")
    started = utc_now()
    # There is deliberately no shell, command interpolation, or automatic job submission.
    completed = subprocess.run(command, cwd=config.parent, shell=False, check=False)
    if completed.returncode:
        raise ReproError(f"Command failed with exit code {completed.returncode}; no receipt issued")
    if file_hash(lock) != lock_sha:
        raise ReproError("Lock changed during execution; no receipt issued")
    check(lock)
    result = seal({"schema_version": 1, "kind": "receipt", "tool_version": __version__,
                   "started_utc": started, "finished_utc": utc_now(),
                   "lock_path": portable_path(lock, receipt.parent), "lock_sha256": lock_sha,
                   "snapshot_sha256": digest(record["state"]),
                   "command": list(command), "cwd": portable_path(config.parent, receipt.parent),
                   "python": sys.version.split()[0], "exit_code": completed.returncode,
                   "outputs": [{"path": portable_path(p, receipt.parent), **snapshot_file(p)}
                               for p in paths]})
    write_new_json(receipt, result)
    return result


def verify_receipt(receipt):
    receipt = Path(receipt).resolve(strict=True)
    record = load_record(receipt, "receipt")
    lock = (receipt.parent / record["lock_path"]).resolve(strict=True)
    if file_hash(lock) != record["lock_sha256"]:
        raise ReproError("Receipt lock has changed")
    locked, _ = check(lock)
    if digest(locked["state"]) != record["snapshot_sha256"]:
        raise ReproError("Receipt snapshot does not match lock")
    if record.get("exit_code") != 0 or not record.get("outputs"):
        raise ReproError("Receipt has no successful command outputs")
    for entry in record["outputs"]:
        actual = snapshot_file(receipt.parent / entry["path"])
        if actual != {key: entry[key] for key in ("sha256", "bytes")}:
            raise ReproError(f"Output changed: {entry['path']}")
    return record
