# ABINIT Runtime Log Fixtures

This directory holds canonical ABINIT runtime log/output fixtures used by the
agent CLI smoke tests and the OpenQC `lsp:check-family` gate. Each fixture is
a minimal real-world artifact that triggers a single documented log-parser
diagnostic.

## Fixtures

| File | Expected code | Severity | Blocking | Provenance |
|------|---------------|----------|----------|------------|
| `scf_not_converged.out` | `ABINIT200` | error | yes | https://docs.abinit.org/tutorial/base1/ |

## Closed-loop contract

The agent CLI parses log fixtures via `abinit_lsp.log_parser.parse_log_file`
and returns `DiagnosticEnvelope/v1` JSON. Log parsing is intentionally
separate from input parsing: an input that lints clean can still produce a
runtime log diagnostic, and a log diagnostic never edits the input file.

## Source

- SCF convergence pattern anchor: https://docs.abinit.org/tutorial/base1/
- Artifact origin: derived from real ABINIT 10.0.5 SCF output (synthetic minimal repro).
