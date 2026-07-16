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

## Installation

Current release: `0.1.1`

Install the server and command-line tools from PyPI:

```bash
pip install abinit-lsp
abinit-lsp --stdio
```

The `abinit-lsp-tool` agent CLI exposes JSON capabilities, checks, context,
completion, hover, symbols, and non-destructive fix previews. Its `check`
operation accepts ABINIT inputs and runtime `.out`/`.log` files.

## Releases

Releases use PyPI Trusted Publishing: a pushed `v*` tag starts the release
workflow, which verifies that the tag matches `pyproject.toml`, builds and
checks the distribution, and installs the wheel into a fresh virtual
environment for server, agent, and fixture smoke tests. Only the protected
`pypi` environment receives `id-token: write`; no long-lived PyPI token is
stored.

After this PR is merged and its release point is approved, create `v0.1.1` on
the merge commit. Pull requests and ordinary branch pushes cannot publish.

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
