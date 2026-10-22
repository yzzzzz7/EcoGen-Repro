# Record format, version 1

## Configuration

The configuration is UTF-8 JSON. `schema_version` is `1`; `project` is a nonempty identifier; `method` contains nonempty `name` and `version` strings; `parameters` is an object. `inputs` is a nonempty list of unique IDs, paths, and optional formats (`file` by default). Input paths are relative to the configuration directory or explicit absolute paths. JSON duplicate keys and NaN/Infinity are rejected. Missing values can be represented as JSON null where scientifically appropriate.

`sample_scope` is optional. It names a `vcf` input and a `samples` input. `mode: exact` requires identical ordered IDs. `mode: subset` requires a nonempty `reason` and membership of all selected IDs in that VCF. This is a scope declaration, not a biological validation.

## Lock

The lock records its schema version, tool version, creation time, relative configuration path, and a `state` object. State contains the full declared configuration, configuration-file SHA256, and per-input SHA256, byte count, format, path, and sample IDs where relevant. Changing even configuration whitespace invalidates the lock.

`record_sha256` hashes JSON serialization of all other fields with sorted keys, ASCII escapes, Python's default JSON separators, and nonfinite numbers disabled. It is an accidental-corruption check, not an authenticated signature.

## Receipt

A successful `run` receipt records start/end UTC timestamps, tool version, lock path and full-file SHA256, a snapshot checksum, exact command argument list, working directory, wrapper Python version, command exit code, and each declared output's path/SHA256/size. Command stdout/stderr are inherited by the caller rather than collected or interpreted. Keep analysis logs through your existing workflow and declare them as outputs when needed.

There is no successful receipt if inputs drift, the command fails, or declared outputs are missing. Failed attempts may leave ordinary command outputs; these must be reviewed separately. A preexisting receipt or output is rejected before execution. The tool does not overwrite or silently refresh an old lock.

`verify` checks receipt integrity, the referenced lock's file bytes, current inputs against that lock, snapshot identity, and every recorded output hash. A changed current input invalidates verification even if the historical output has not changed.

Relative paths allow relocation of a whole project with its structure preserved. Absolute input or executable paths remain machine-specific. No credentials are stored by the tool, but command arguments, paths and sample IDs can contain sensitive information supplied by the user.
