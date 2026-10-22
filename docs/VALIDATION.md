# Validation record — 2026-10-22

Validated source: initial alpha commit `6c19dcb` (tag `v0.1.0`).

## Automated checks

[GitHub Actions run 39706561044](https://github.com/yzzzzz7/EcoGen-Repro/actions/runs/39706561044) completed successfully. Each job installed the package, ran the 28-test regression suite, and checked the installed command version.

| Operating system | Python | Result |
| --- | --- | --- |
| Ubuntu | 3.10 | PASS |
| Ubuntu | 3.12 | PASS |
| Ubuntu | 3.13 | PASS |
| Windows | 3.10 | PASS |
| Windows | 3.12 | PASS |
| Windows | 3.13 | PASS |

Local Windows validation used Python 3.12.14: 28 tests passed. Nine additional installed-wheel CLI checks covered version reporting, locking, input checking, guarded execution, receipt verification, configuration drift rejection, restored-input verification, and changed-output rejection.

Distributed wheel: `ecogen_repro-0.1.0-py3-none-any.whl`.

SHA256: `a4e5fcf8ab286a1840190eb9da00bb31e420153a8235c2ff8e60974360687283`.

## What remains unverified

Large-file/shared-storage performance, real research workflow adoption, undeclared dependencies, transient/concurrent input changes beyond the observed checks, and biological/scientific validity. All regression fixtures and public examples are synthetic. Test success establishes the implemented provenance behavior for the exercised cases.
