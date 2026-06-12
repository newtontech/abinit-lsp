# OpenQC Agent Context

OpenQC consumes `abinit-lsp-tool` and `lsp-capabilities.json` to assemble diagnostics, hover, completion, symbols, examples, next-token guidance, and repair-plan hints for `abinit` documents.

## Agent CLI Surface

```bash
abinit-lsp-tool capabilities    # Report supported operations
abinit-lsp-tool check <path>    # Run diagnostics with DiagnosticEnvelope/v1
abinit-lsp-tool context <path>  # Position-aware context (token, symbols, diagnostics)
abinit-lsp-tool complete <path> # Keyword completion
abinit-lsp-tool hover <path>    # Hover documentation
abinit-lsp-tool symbols <path>  # Document symbols
abinit-lsp-tool fix <path>      # Quick-fix actions
```

## Capabilities from lsp-capabilities.json

- `agent-envelope` — DiagnosticEnvelope/v1 JSON output
- `blocking-gate` — Error diagnostics block run-gate and Bohrium submission
- `completion` — 50+ documented ABINIT keywords
- `diagnostics` — 8 lint rules (ABINIT101–ABINIT108)
- `hover` — Source-grounded keyword documentation
- `source-provenance` — Official docs links per keyword

## Source Provenance

Hover and completion documentation in `src/abinit_lsp/completion.py` references:
- ABINIT Input Variables: <https://docs.abinit.org/variables/>
- See `raw/assets/upstream-sources.md` for complete variable→URL mapping

## Related Pages

- [[diagnostic-engine-v1]] — Diagnostic code catalog
- [[ABINIT]] — Software overview
- [[ecut]], [[natom]], [[typat]], [[ntypat]] — Key input variables
