# Changelog

## 0.2.0 — 2026-10-22

- Added an offline `demo` command usable from an installed wheel, with six observed provenance scenarios and restored synthetic files.
- Added `report` to verify a receipt and export a self-contained HTML report with escaped configuration text.
- Expanded Chinese installation, walkthrough, configuration and interpretation documentation.
- Added installed-package demo/report checks to the Linux/Windows CI matrix.
- Return a structured CLI failure for a truncated gzip input instead of an uncaught EOFError.

## 0.1.0 — 2026-10-22

Initial alpha implementation: provenance locks, VCF sample-scope checks, guarded runs, output receipts, synthetic examples, and regression tests.
