# ABINIT LSP Wiki

## 快速开始 (Quick Start)

This wiki contains ABINIT domain knowledge organized by entity types, concepts, and synthesis pages.

- **[Raw Assets](raw/assets/)** - Source evidence files
- **[Entities](wiki/entities/)** - ABINIT-specific entities (input variables, file formats)
- **[Concepts](wiki/concepts/)** - Cross-cutting concepts (diagnostics, DFT)
- **[Synthesis](wiki/synthesis/)** - Agent context and API references

## Entity Pages

### Core Input Variables
- [ABINIT](wiki/entities/ABINIT.md) — Software overview, input format, and LSP support
- [ecut](wiki/entities/ecut.md) — Plane-wave energy cutoff (ABINIT101, ABINIT031)
- [natom](wiki/entities/natom.md) — Number of atoms (ABINIT102)
- [ntypat](wiki/entities/ntypat.md) — Number of atom types
- [typat](wiki/entities/typat.md) — Atom type mapping (ABINIT103)

### Planned Pages (see docs/LLM-WIKI-PLAN.md)
- Input_Variables, DFT_Variables, Pseudopotentials, K_Point_Sampling
- Output_Files, Density_Files, Wavefunction_Files

## Concept Pages

- [Diagnostic Engine v1](wiki/concepts/diagnostic-engine-v1.md) — DiagnosticEnvelope/v1 contract, code catalog

### Planned Pages (see docs/LLM-WIKI-PLAN.md)
- DFT_Implementation, Plane_Wave_Basis, FFT_Grids
- Convergence_Parameters, Basis_Set_Cutoffs
- Ground_State_Calculation, Geometry_Optimization, Response_Properties

## Synthesis Pages

- [OpenQC Agent Context](wiki/synthesis/openqc-agent-context.md) — Agent CLI surface, capabilities, source provenance

### Planned Pages (see docs/LLM-WIKI-PLAN.md)
- Input_Variable_Reference, Diagnostics_Catalog, API_Reference
- Quick_Start_Guide, Common_Workflows

## Raw Evidence

Source documentation and code extracts are stored in [raw/assets/](raw/assets/).

- [README.md](raw/assets/README.md) — Project overview
- [AGENTS.md](raw/assets/AGENTS.md) — Agent workflow guide
- [DIAGNOSTIC_ENGINE_V1.md](raw/assets/DIAGNOSTIC_ENGINE_V1.md) — Diagnostic engine spec
- [diagnostic-engine-v1.schema.json](raw/assets/diagnostic-engine-v1.schema.json) — Schema
- [upstream-sources.md](raw/assets/upstream-sources.md) — Official ABINIT docs link manifest
- [examples-silicon-scf.abi](raw/assets/examples-silicon-scf.abi) — Si SCF tutorial example
- [examples-relaxation.abi](raw/assets/examples-relaxation.abi) — Si relaxation example
- [examples-multidataset.abi](raw/assets/examples-multidataset.abi) — Multi-dataset example

## Changelog

See [log.md](log.md) for wiki change history.
