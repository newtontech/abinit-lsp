# Changelog

All notable changes to this project are documented in this file.

## [0.1.1] - 2026-07-16

### Added

- Tag-only PyPI release automation using GitHub OIDC Trusted Publishing and
  the protected `pypi` environment.
- Fresh-wheel smoke coverage for the stdio server and agent CLI against
  canonical valid, invalid, and runtime-log fixtures.
- Machine-readable release version and repository metadata in
  `lsp-capabilities.json`.

### Changed

- Runtime `.out` and `.log` files now route through the existing log parser
  when checked with `abinit-lsp-tool`.
- Package, runtime, capability, and `VERSION` metadata now consistently report
  `0.1.1`. The approved post-merge release tag is `v0.1.1`.

## [0.1.0] - 2026-06-15

### Added

- Structured provenance manifest (`raw/assets/manifest.json`) with checksums,
  retrieval dates, and wiki cross-links for every captured asset.
- `scripts/refresh-wiki-digest.sh` to verify on-disk assets against manifest
  checksums and run wiki lint in one command.
- `VERSION` file aligned with `pyproject.toml`.
- Closed-loop test asserting `raw/assets/manifest.json` is present and linked
  from `lsp-capabilities.json`.

### Changed

- `lsp-capabilities.json` `sourceProvenance` now references
  `raw/assets/manifest.json` as the canonical provenance digest.
