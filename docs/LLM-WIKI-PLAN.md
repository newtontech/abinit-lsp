# ABINIT LSP Wiki Structure Plan

## Overview

This document describes the planned structure for the ABINIT LSP Wiki knowledge base following Karpathy's LLM Wiki pattern.

## Directory Structure

```
abinit-lsp/
├── raw/
│   └── assets/           # Source evidence files
├── wiki/
│   ├── entities/         # Entity pages
│   ├── concepts/         # Concept pages
│   └── synthesis/       # Synthesis pages
├── index.md             # Navigation hub
└── log.md               # Change log
```

## Content Areas

### 1. Entity Pages (Concrete Domain Objects)

#### Input Structure
- **ABINIT_Input_Format** - Main input file syntax and organization
- **Input_Variables** - Variable naming conventions and categories
- **Dataset_Multiple** - Multi-dataset workflow support

#### Physical Models
- **DFT_Variables** - XC functionals, spin treatment, relativity
- **Pseudopotentials** - PSP8, PAW, norm-conserving formats
- **K_Point_Sampling** - Monkhorst-Pack grids, k-point paths

#### File Formats
- **Output_Files** - Main output, DEN, WFK files
- **Density_Files** - Charge density formats and visualization
- **Wavefunction_Files** - Wavefunction file handling

### 2. Concept Pages (Reusable Ideas)

#### Electronic Structure Theory
- **DFT_Implementation** - ABINIT DFT specifics (XC, correlation)
- **Plane_Wave_Basis** - Kinetic energy cutoff, FFT grids
- **FFT_Grids** - Grid doubling, sphere packing

#### Convergence & Accuracy
- **Convergence_Parameters** - Toldfe, tolrst, tolwfr criteria
- **Basis_Set_Cutoffs** - Ecut selection guidelines

#### Calculation Types
- **Ground_State_Calculation** - SCF algorithms and convergence
- **Geometry_Optimization** - Ionic relaxation methods
- **Response_Properties** - DFPT, phonons, dielectric properties

### 3. Synthesis Pages (Curated References)

#### API Documentation
- **Input_Variable_Reference** - Complete variable catalog with usage
- **Diagnostics_Catalog** - LSP diagnostic codes and fixes
- **API_Reference** - LSP server capabilities

#### User Guides
- **Quick_Start_Guide** - Installation and basic usage
- **Common_Workflows** - SCF, relaxation, band structure

## Cross-Reference Strategy

Key pages to build first for referential integrity:
1. [[ABINIT_Input_Format]] - foundational
2. [[Input_Variables]] - referenced from multiple pages
3. [[Diagnostics_Catalog]] - LSP-specific
4. [[Common_Workflows]] - user-facing

## Source Files

Primary source files for wiki content:
- `README.md` - Project overview
- `docs/DIAGNOSTIC_ENGINE_V1.md` - Diagnostic engine spec
- `src/abinit_lsp/server.py` - LSP server implementation
- `src/abinit_lsp/parser/` - Input parsing logic
- ABINIT official documentation - Theory and input variables

## Target Audience

1. **Computational materials scientists** - Using ABINIT for DFT calculations
2. **LSP developers** - Contributing to abinit-lsp
3. **AI agents** - Consuming the agent API for automated workflows

## Bilingual Format

- Headings in Chinese (类型, 简介, 关键属性)
- Technical terms in English (DFT, pseudopotential, k-point, etc.)
- Code examples in English

## Estimated Size

- **Entity pages**: 8-10 pages
- **Concept pages**: 6-8 pages
- **Synthesis pages**: 4-6 pages
- **Total**: ~18-20 wiki pages
