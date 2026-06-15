# OpenQC Compatibility Report — abinit-lsp

> Generated: 2026-06-15
> Capability manifest: `lsp-capabilities.json`
> Coordinator gate: `lsp:check-family`

This document records the executable evidence that `abinit-lsp` is wired into
the OpenQC scientific LSP fleet. It is intentionally machine-readable in
structure so the coordinator can verify each claim from the repo without
running the LSP server.

## 1. Language and file detection

| Field | Value | Evidence |
|-------|-------|----------|
| `languageId` | `abinit` | `lsp-capabilities.json` |
| `filePatterns` | `*.abi`, `*.abinit` | `lsp-capabilities.json` |
| `displayName` | ABINIT | `lsp-capabilities.json` |

## 2. Configured executable

| Field | Value |
|-------|-------|
| `executable` | `abinit-lsp` (editor server entrypoint: `abinit_lsp.cli:lsp_main`) |
| `agentCli.command` | `abinit-lsp-tool` |
| `agentCli.jsonFormat` | true |
| `agentCli.failOnBlocking` | true |

## 3. Agent CLI availability

`abinit-lsp-tool` answers the fleet-standard operations:

```bash
abinit-lsp-tool capabilities
abinit-lsp-tool check <path> [--fail-on-blocking]
abinit-lsp-tool preflight <path> [--fail-on-blocking]
abinit-lsp-tool manifest [path]
abinit-lsp-tool context <path> [--line N --character N]
abinit-lsp-tool complete <path> [--line N --character N]
abinit-lsp-tool hover <path> [--line N --character N]
abinit-lsp-tool symbols <path>
abinit-lsp-tool fix <path> [--line N --character N]
```

Every operation returns stable `DiagnosticEnvelope/v1` JSON.

## 4. Closed-loop fixture evidence

| Fixture | Expected outcome | Verified by |
|---------|------------------|-------------|
| `tests/fixtures/valid/silicon_scf.abi` | clean (no diagnostics, `ok=true`) | `tests/test_closed_loop_fixtures.py` |
| `tests/fixtures/invalid/missing_natom.abi` | `ABINIT102` blocking error | `tests/test_closed_loop_fixtures.py` |
| `tests/fixtures/invalid/inconsistent_typat_znucl.abi` | `ABINIT103` blocking error | `tests/test_closed_loop_fixtures.py` |
| `tests/fixtures/invalid/loose_tolerance.abi` | `ABINIT106` non-blocking warning | `tests/test_closed_loop_fixtures.py` |
| `tests/fixtures/invalid/unknown_keyword.abi` | `ABINIT107` non-blocking warning | `tests/test_closed_loop_fixtures.py` |
| `tests/fixtures/logs/scf_not_converged.out` | `ABINIT200` runtime log error | `tests/test_closed_loop_fixtures.py` |

## 5. Source provenance summary

Every lint diagnostic now carries `source_provenance.kind=official_docs` and
a URL pinned to https://docs.abinit.org/variables/<name>/ (or the user guide
for structural errors). The provenance lookup is centralized in
`src/abinit_lsp/lint.RULE_PROVENANCE` and applied by
`enrich_diagnostic_provenance`, so adding a new rule with provenance is a
single dict entry.

## 6. Blocking policy

| Code | Severity | Blocks run-gate? |
|------|----------|------------------|
| ABINIT101 (missing ecut) | warning | no |
| ABINIT102 (missing natom) | error | yes |
| ABINIT103 (typat/znucl inconsistent) | error | yes |
| ABINIT104 (invalid value type) | error | yes |
| ABINIT105 (multidataset suffix) | warning | no |
| ABINIT106 (loose tolerance) | warning | no |
| ABINIT107 (unknown keyword) | warning | no |
| ABINIT108 (duplicate keyword) | warning | no |
| ABINIT200 (SCF did not converge) | error | yes (runtime log) |
| ABINIT202 (non-UTF-8 input) | error | yes |

## 7. Output/log diagnostic support

| Layer | Status |
|-------|--------|
| Input-file lint rules | implemented (8 rules + 2 I/O rules) |
| Preflight cross-file checks | implemented (`ABINIT601`–`ABINIT610`) |
| Runtime log parser | implemented for SCF convergence + fatal-error patterns |
| Version-aware keyword scope | implemented via `.abinit-lsp/intent.json` |

## 8. Verification commands

```bash
# Closed-loop fixture gate
PYTHONPATH=src python3 -m pytest tests/test_closed_loop_fixtures.py -v

# Full test suite
PYTHONPATH=src python3 -m pytest tests/

# One-shot agent CLI smoke
PYTHONPATH=src python3 -m abinit_lsp.tool capabilities
PYTHONPATH=src python3 -m abinit_lsp.tool check tests/fixtures/valid/silicon_scf.abi
PYTHONPATH=src python3 -m abinit_lsp.tool check tests/fixtures/invalid/missing_natom.abi --fail-on-blocking
```
