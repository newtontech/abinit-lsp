# ABINIT LSP Wiki

## 快速开始 (Quick Start)

This wiki contains ABINIT domain knowledge organized by entity types, concepts, and synthesis pages.

- **[Raw Assets](raw/assets/)** - Source evidence files
- **[Entities](wiki/entities/)** - ABINIT-specific entities (input variables, file formats)
- **[Concepts](wiki/concepts/)** - Cross-cutting concepts (DFT, pseudopotentials, k-points)
- **[Synthesis](wiki/synthesis/)** - API references and workflows

## Entity Pages

### Input Structure
- [[ABINIT_Input_Format]] - Main input file structure and syntax
- [[Input_Variables]] - Key input variables and their usage
- [[Dataset_Multiple]] - Multi-dataset calculations

### Physical Models
- [[DFT_Variables]] - Density functional theory variables
- [[Pseudopotentials]] - Pseudopotential files and formats (PSP8, PAW)
- [[K_Point_Sampling]] - k-point grids and paths

### File Formats
- [[Output_Files]] - ABINIT output file types
- [[Density_Files]] - Charge density formats
- [[Wavefunction_Files]] - Wavefunction file formats

## Concept Pages

### Electronic Structure
- [[DFT_Implementation]] - ABINIT DFT implementation details
- [[Plane_Wave_Basis]] - Plane wave basis set usage
- [[FFT_Grids]] - FFT grid parameters and optimization

### Convergence & Accuracy
- [[Convergence_Parameters]] - SCF and geometry convergence criteria
- [[Basis_Set_Cutoffs]] - Energy cutoff selection guidelines

### Calculation Types
- [[Ground_State_Calculation]] - SCF calculations
- [[Geometry_Optimization]] - Structural optimization
- [[Response_Properties]] - DFPT and phonon calculations

## Synthesis Pages

### References
- [[Input_Variable_Reference]] - Complete variable catalog
- [[Diagnostics_Catalog]] - ABINIT LSP diagnostic codes
- [[API_Reference]] - ABINIT LSP server API

### Workflows
- [[Quick_Start_Guide]] - Getting started with ABINIT LSP
- [[Common_Workflows]] - Typical ABINIT calculation workflows

## Raw Evidence

Source documentation and code extracts are stored in [raw/assets/](raw/assets/).

## Changelog

See [log.md](log.md) for wiki change history.
