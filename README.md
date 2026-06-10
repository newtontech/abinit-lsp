# abinit-lsp

`abinit-lsp` is an MVP Language Server Protocol and CLI toolkit for ABINIT files used in MatMaster workflows.

The first version is intentionally deterministic and lightweight: static parsing, lint diagnostics, safe formatting, and machine-readable JSON output live here. Full scientific execution, Bohrium submission, and heavy workflow automation stay outside the LSP and should be invoked explicitly by higher-level tools.

## CLI Surface

```bash
abinit-lsp --stdio
abinit-lint ./case --json
abinit-fmt -w input.file
abinit-test static ./case --json
```

Diagnostic JSON uses the shared newtontech LSP shape: `file`, `line`, `column`, `severity`, `code`, `message`, `evidence`, `suggested_fix`, and `confidence`.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check src tests
ruff format --check src tests
mypy src
```

## Scope

This repository is seeded from MatMaster skill contracts and evaluation fixtures. The roadmap is tracked in GitHub issues and should converge toward parser-backed diagnostics, completion, hover documentation, formatting, OpenQC integration, and regression fixtures.
