# Diagnostic Engine v1

ABINIT diagnostics use `DiagnosticEnvelope/v1` with `error`, `warning`, `information`, and `hint` severities. Blocking behavior is controlled by `lsp-capabilities.json`, not by OpenQC guesswork.

## Source

- Contract spec: `raw/assets/DIAGNOSTIC_ENGINE_V1.md`
- Schema: `diagnostics/diagnostic-engine-v1.schema.json`
- Implementation: `src/abinit_lsp/lint.py`, `src/abinit_lsp/rich_diagnostics.py`

## Diagnostic Codes (ABINIT prefix)

| Code | Severity | Description | Source Rule |
|------|----------|-------------|-------------|
| ABINIT101 | warning | ecut is a required variable | `abinit.input.missing_ecut` |
| ABINIT102 | error | natom is required | `abinit.structure.missing_natom` |
| ABINIT103 | error | typat/znucl inconsistent with ntypat | `abinit.structure.inconsistent_typat_znucl` |
| ABINIT104 | error | variable value has wrong type | `abinit.variable.invalid_type` |
| ABINIT105 | warning | dataset suffix exceeds ndtset | `abinit.multidataset.bad_suffix` |
| ABINIT106 | warning | convergence tolerance too loose | `abinit.scf.loose_tolerance` |
| ABINIT107 | warning | unknown keyword | `abinit.input.unknown_keyword` |
| ABINIT108 | warning | duplicate keyword | `abinit.input.duplicate_keyword` |

## Related Pages

- [[ecut]] — ABINIT101/ABINIT031 target variable
- [[natom]] — ABINIT102 target variable
- [[typat]] — ABINIT103 target variable
- [[ABINIT]] — Software overview
- [[openqc-agent-context]] — Agent integration
