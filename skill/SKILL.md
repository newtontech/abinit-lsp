---
name: abinit
description: "ABINIT input preflight for .abi and .abinit input files."
---

# ABINIT LSP Skill

Use this skill when preparing, repairing, or reviewing ABINIT input files before a run. It provides an installable language server and an agent-facing CLI that reports machine-readable diagnostics.

## Scope

- Input patterns: *.abi, *.abinit
- Server command: `abinit-lsp`
- Agent CLI: `abinit-lsp-tool`
- Diagnostic contract: `DiagnosticEnvelope/v1`

## Installing the checker

```bash
pip install abinit-lsp
```

This installs the `abinit-lsp` language server and the `abinit-lsp-tool` agent CLI from the `abinit-lsp` Python package.

## Useful inspection commands

```bash
abinit-lsp-tool capabilities
abinit-lsp-tool skill-spec --format json
abinit-lsp-tool skill-export --output ./skill
abinit-lsp-tool check <input-file-or-dir> --format json
abinit-lsp-tool context <input-file-or-dir> --line 0 --character 0 --format json
abinit-lsp-tool hover <input-file-or-dir> --line 0 --character 0 --format json
abinit-lsp-tool complete <input-file-or-dir> --line 0 --character 0 --format json
abinit-lsp-tool symbols <input-file-or-dir> --format json
abinit-lsp-tool fix <input-file-or-dir> --line 0 --character 0 --format json
```

`fix` is advisory and must be treated as a preview. Do not blindly apply a repair without preserving the user's scientific intent.

## Validation gate

Before saying generated inputs are ready, run:

```bash
abinit-lsp-tool check <input-file-or-dir> --format json --fail-on-blocking
```

Report `commands`, `files_checked`, `tool_available`, `diagnostics`, `blocking_findings`, `readiness`, and `reason`.

## Repair rules

1. Validate first and identify the smallest blocking issue.
2. Fix syntax or schema errors with minimal edits.
3. Preserve scientific settings unless the user explicitly asks to redesign them.
4. Re-run the checker after every edit.
5. Separate syntax, schema, semantic, and runtime-log diagnostics in the final report.
