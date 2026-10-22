# Validation record — 2026-10-22

## 0.2.0 alpha

Validated code commit: `3e86689ab038ede3bdfbd083d3d29c0cfa66e7a5`.

[GitHub Actions run 39708952719](https://github.com/yzzzzz7/EcoGen-Repro/actions/runs/39708952719) passed all six Linux/Windows × Python 3.10/3.12/3.13 jobs. Each job installed the package, ran the 36-test regression suite, then exercised `demo`, `verify`, and `report` with the installed command outside the source directory.

Local Windows/Python 3.12.14 checks: 36 regression tests, six installed-wheel CLI checks, and all six expected walkthrough outcomes passed. A changed output prevented a new PASS report from being written. The walkthrough restored its synthetic files, and its original receipt remained valid.

The generated HTML was rendered and visually inspected at desktop and mobile widths (1280 and 390 CSS pixels). Tables scroll within their containers on narrow screens, the page had no horizontal overflow, and the report made no remote requests. The [preview image](report-preview.png) was captured from the actual generated report.

Wheel: `ecogen_repro-0.2.0-py3-none-any.whl`.

SHA256: `a8b73b5c198fc4b7fff86295b9a7a456962f61c6ec1fb5264f4e2bd8b59d5dae`.

These checks use synthetic fixtures. External adoption, large-file/shared-storage performance, environment completeness, and biological validity remain unverified.

## 0.1.0 alpha

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
