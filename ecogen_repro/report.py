"""Export a self-contained HTML view after verifying a run receipt."""

import html
import json
from pathlib import Path

from . import __version__
from .core import ReproError, digest, load_record, utc_now, verify_receipt


def escape(value):
    return html.escape(str(value), quote=True)


def table(headers, rows):
    head = "".join(f"<th scope='col'>{escape(value)}</th>" for value in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row)
                   + "</tr>" for row in rows)
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def write_report(receipt, output):
    """Refuse a stale run or existing output; embed no scripts or remote assets."""
    receipt = Path(receipt).resolve(strict=True)
    record = verify_receipt(receipt)
    lock = load_record(receipt.parent / record["lock_path"], "lock")
    state = lock["state"]
    if digest(state) != record["snapshot_sha256"]:
        raise ReproError("Lock changed before report generation")
    spec = state["spec"]
    checked = utc_now()
    inputs = table(["ID", "Path", "Format", "Bytes", "SHA256"], [
        [name, entry["path"], entry["format"], entry["bytes"], entry["sha256"]]
        for name, entry in state["inputs"].items()
    ])
    outputs = table(["Path (relative to receipt)", "Bytes", "SHA256"], [
        [entry["path"], entry["bytes"], entry["sha256"]] for entry in record["outputs"]
    ])
    scope = spec.get("sample_scope")
    if scope:
        selected = state["inputs"][scope["samples"]]["samples"]
        source = state["inputs"][scope["vcf"]]["samples"]
        samples = table(["Scope mode", "VCF samples", "Selected samples", "Reason"], [
            [scope["mode"], len(source), len(selected), scope.get("reason", "Exact ordered match")]
        ])
        samples += ("<details><summary>Selected IDs in recorded order</summary><pre>"
                    + escape("\n".join(selected)) + "</pre></details>")
    else:
        samples = "<p>No sample-scope check was declared.</p>"
    title = escape(spec["project"])
    parameters = escape(json.dumps(spec["parameters"], indent=2, ensure_ascii=False))
    command = escape(json.dumps(record["command"], ensure_ascii=False))
    method = spec["method"]["name"] + " " + spec["method"]["version"]
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>EcoGen-Repro | {title}</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #171717; background: white; font: 16px/1.6 system-ui, sans-serif; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 36px 24px 60px; }}
h1 {{ font-size: 30px; line-height: 1.2; margin: 12px 0; overflow-wrap: anywhere; }}
h2 {{ font-size: 21px; margin: 32px 0 12px; }}
.eyebrow {{ font-size: 13px; letter-spacing: .08em; text-transform: uppercase; }}
.status {{ display: inline-block; border: 2px solid #171717; padding: 3px 12px; font-weight: 700; }}
.note {{ border-left: 3px solid #777; padding-left: 14px; }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; min-width: 720px; border-collapse: collapse; font-size: 13px; }}
th, td {{ text-align: left; vertical-align: top; border-bottom: 1px solid #ccc; padding: 9px 8px; overflow-wrap: anywhere; }}
th {{ font-weight: 700; }}
td:last-child {{ font-family: ui-monospace, monospace; word-break: break-all; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; border: 1px solid #ccc; padding: 12px; font: 13px/1.6 ui-monospace, monospace; }}
summary {{ cursor: pointer; }}
.table-help {{ display: none; }}
footer {{ margin-top: 36px; border-top: 1px solid #ccc; padding-top: 12px; font-size: 13px; }}
@media (max-width: 640px) {{ .table-help {{ display: block; font-size: 13px; }} }}
@media print {{ main {{ padding: 0; }} .table-wrap {{ overflow: visible; }} table {{ min-width: 0; }} h2 {{ break-after: avoid; }} tr {{ break-inside: avoid; }} }}
</style></head><body><main>
<div class="eyebrow">EcoGen-Repro · research file provenance</div>
<h1>{title}</h1><p><span class="status">PASS — provenance verified</span></p>
<p>Checked at {escape(checked)} with EcoGen-Repro {escape(__version__)}.</p>
<p class="table-help">Scroll tables horizontally to read all columns.</p>
<p class="note">This is a point-in-time check of declared files. It establishes file provenance,
not scientific validity. Re-run verification after changing or receiving files.
This static report does not refresh or authenticate itself.</p>
<h2>Run</h2>
{table(["Declared method/version", "Started UTC", "Finished UTC", "Exit code"], [[method, record["started_utc"], record["finished_utc"], record["exit_code"]]])}
<p>Method and external software versions are researcher declarations.</p>
<h2>Command arguments</h2><pre>{command}</pre>
<h2>Parameters</h2><pre>{parameters}</pre>
<h2>Sample scope</h2>{samples}
<h2>Declared inputs</h2>{inputs}
<h2>Recorded outputs</h2>{outputs}
<h2>Verification references</h2>
{table(["Record", "SHA256"], [["Lock file", record["lock_sha256"]], ["Input snapshot", record["snapshot_sha256"]]])}
<footer>Generated locally. No remote assets, scripts, telemetry, or network requests.
Paths, sample IDs, command arguments, and parameters may be sensitive; review before sharing.</footer>
</main></body></html>"""
    output = Path(output).resolve()
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(document)
    return {"report": str(output), "checked_utc": checked}
