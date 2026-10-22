import argparse
import json
import sys

from . import __version__
from .core import ReproError, check, freeze, guarded_run, verify_receipt
from .demo import run_demo
from .report import write_report


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if argv and argv[0] == "run" and "--" in argv:
        boundary = argv.index("--")
        argv, command = argv[:boundary], argv[boundary + 1:]
    parser = argparse.ArgumentParser(description="Research input and sample provenance gates")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("lock", help="Freeze declared inputs, parameters, and sample scope")
    create.add_argument("config")
    create.add_argument("--out", required=True)
    inspect = sub.add_parser("check", help="Fail if inputs or configuration differ")
    inspect.add_argument("lock")
    run = sub.add_parser("run", help="Execute a trusted command with input gates")
    run.add_argument("lock")
    run.add_argument("--output", action="append", required=True,
                     help="New output relative to the config directory; repeat as needed")
    run.add_argument("--receipt", required=True)
    verify = sub.add_parser("verify", help="Check receipt, current inputs, and output hashes")
    verify.add_argument("receipt")
    report = sub.add_parser("report", help="Verify a receipt and export a self-contained HTML report")
    report.add_argument("receipt")
    report.add_argument("--out", required=True)
    demo = sub.add_parser("demo", help="Run a complete offline walkthrough using synthetic data")
    demo.add_argument("--out", required=True, help="Explicitly named new or empty directory")
    args = parser.parse_args(argv)
    details = {}
    try:
        if args.action == "lock":
            freeze(args.config, args.out)
        elif args.action == "check":
            check(args.lock)
        elif args.action == "run":
            guarded_run(args.lock, command, args.output, args.receipt)
        elif args.action == "verify":
            verify_receipt(args.receipt)
        elif args.action == "report":
            details = write_report(args.receipt, args.out)
        else:
            details = run_demo(args.out)
    except (ReproError, OSError, ValueError, KeyError, TypeError, EOFError) as exc:
        print(json.dumps({"status": "FAIL", "action": args.action,
                          "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 1
    print(json.dumps({"status": "PASS", "action": args.action, **details}))
    return 0
