# Contributing

Please open an issue with a minimal synthetic example, Python/platform versions, the command, and expected/observed behavior. Do not upload private genomic data, credentials, or identifiable sample records.

For a change:

1. Keep the provenance semantics explicit and preserve sample order.
2. Include a regression test for the demonstrated failure.
3. Run `python -m unittest discover -s tests -v`.
4. Document format or behavior changes. Do not silently migrate or overwrite locks.

Scientific estimators belong to their named implementations. New adapters must identify what is actually verified and should not claim biological validity from a hash check.

The project is currently maintained by its initiating maintainer. There is no promised response SLA or established contributor community.
