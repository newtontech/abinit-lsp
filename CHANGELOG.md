# Changelog

All notable changes to this project are documented in this file.

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
