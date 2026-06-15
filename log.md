# ABINIT LSP Wiki Changelog

## 2026-06-13 - Upstream Docs Closeout (#30)

**Scope**: Fill upstream documentation coverage gaps, add official examples, cross-reference wiki pages, create wiki lint.

**Content Added**:
- `raw/assets/upstream-sources.md` — Official ABINIT docs link manifest (docs.abinit.org)
- `raw/assets/examples-silicon-scf.abi` — Si FCC SCF tutorial input
- `raw/assets/examples-relaxation.abi` — Si geometry optimization example
- `raw/assets/examples-multidataset.abi` — Multi-dataset convergence study example
- `scripts/wiki-lint.sh` — Lightweight wiki integrity checker

**Pages Updated**:
- `wiki/entities/ABINIT.md` — Added official reference links and cross-references
- `wiki/entities/ecut.md` — Added official docs links and LSP hover provenance
- `wiki/entities/natom.md` — Added official docs links
- `wiki/entities/ntypat.md` — Added official docs links
- `wiki/entities/typat.md` — Added official docs links
- `wiki/concepts/diagnostic-engine-v1.md` — Expanded with code table and cross-references
- `wiki/synthesis/openqc-agent-context.md` — Expanded with CLI surface and capabilities
- `index.md` — Added raw asset listings for new files
- `log.md` — This entry

**LSP-facing Update**:
- Updated `lsp-capabilities.json` sourceProvenance with additional upstream URLs
- Hover docs in `completion.py` now traceable to wiki via upstream-sources.md manifest

## 2026-06-15 - Provenance manifest digest (#35)

**Scope**: Add structured `raw/assets/manifest.json`, refresh script, and fleet
provenance linkage for OpenQC `lsp:check-family`.

**Content Added**:
- `raw/assets/manifest.json` — checksum-backed provenance manifest
- `scripts/refresh-wiki-digest.sh` — verify captured assets + wiki lint
- `VERSION`, `CHANGELOG.md` — release metadata for family gate

**LSP-facing Update**:
- `lsp-capabilities.json` `sourceProvenance` references `raw/assets/manifest.json`
- `tests/test_closed_loop_fixtures.py` asserts manifest presence and linkage

## 2025-06-12 - Initial Wiki Creation

**Scope**: Created LLM Wiki knowledge base for ABINIT LSP project.

**Content Created**:
- `raw/assets/` - Source evidence files (README, docs, source code)
- `wiki/entities/` - Entity pages for ABINIT domain concepts
- `wiki/concepts/` - Concept pages for cross-cutting ideas
- `wiki/synthesis/` - Synthesis pages for API references and workflows
- `index.md` - Navigation hub
- `log.md` - This file

**Coverage**:
- ABINIT input file format and variables
- DFT implementation and plane wave basis
- Pseudopotentials and PAW datasets
- K-point sampling and convergence
- LSP server implementation and diagnostics

**Total Files**: 18+ wiki pages

**Notes**:
- Bilingual format (Chinese headings, English technical terms)
- Obsidian-style `[[Wiki_Link]]` cross-references
- Source-grounded with citations to original documentation
