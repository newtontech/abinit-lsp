"""Parser-backed linting rules for ABINIT input files.

Each rule is a named constant with a check function that operates on the
parsed AbinitFile representation.  Diagnostic codes use the ABINIT prefix.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .diagnostics import Diagnostic
from .parser import AbinitFile, parse_content

# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

RULE_MISSING_ECUT = "abinit.input.missing_ecut"
RULE_MISSING_NATOM = "abinit.structure.missing_natom"
RULE_INCONSISTENT_TYPAT_ZNUCL = "abinit.structure.inconsistent_typat_znucl"
RULE_INVALID_VARIABLE_TYPE = "abinit.variable.invalid_type"
RULE_BAD_MULTIDATASET_SUFFIX = "abinit.multidataset.bad_suffix"
RULE_LOOSE_TOLERANCE = "abinit.scf.loose_tolerance"
RULE_UNKNOWN_KEYWORD = "abinit.input.unknown_keyword"
RULE_DUPLICATE_KEYWORD = "abinit.input.duplicate_keyword"

# Type expectations for known keywords.
_INT_KEYWORDS: set[str] = {
    "natom", "nband", "nstep", "ntypat", "ndtset",
    "kptopt", "occopt", "optcell",
}
_FLOAT_KEYWORDS: set[str] = {
    "ecut", "ecutsm", "toldfe", "tolmxf", "tolvrs",
    "diemac", "diemix", "dilatmx",
}

# Keywords that are known ABINIT variables (superset from completion.py).
_KNOWN_BASES: set[str] = {
    "acell", "amu", "autoparal", "chkprim", "diemac", "diemix", "dilatmx",
    "dtset", "ecut", "ecutsm", "fband", "getden", "getwfk", "irdwfk",
    "irdden", "iscf", "ixc", "jdtset", "kptopt", "natom", "nband", "ndtset",
    "ngkpt", "nline", "npband", "npfft", "npkpt", "npsp", "nshiftk", "nstep",
    "ntypat", "occopt", "optcell", "ppdirpath", "prtden", "prt1dm", "prtstd",
    "prtvolf", "prtwf", "pseudos", "rprim", "shiftk", "toldfe", "tolmxf",
    "tolvrs", "typat", "udtset", "usepaw", "xcart", "xred", "znucl",
}


@dataclass(frozen=True)
class RuleInfo:
    """Static metadata about a lint rule."""

    rule_id: str
    code: str
    severity: str
    description: str
    source: str


RULE_MANIFEST: list[RuleInfo] = [
    RuleInfo(
        RULE_MISSING_ECUT, "ABINIT101", "warning",
        "ecut is a required variable for ABINIT calculations", "official",
    ),
    RuleInfo(
        RULE_MISSING_NATOM, "ABINIT102", "error",
        "natom is required to define the crystal structure", "official",
    ),
    RuleInfo(
        RULE_INCONSISTENT_TYPAT_ZNUCL, "ABINIT103", "error",
        "typat and znucl must be consistent with ntypat", "official",
    ),
    RuleInfo(
        RULE_INVALID_VARIABLE_TYPE, "ABINIT104", "error",
        "variable value does not match the expected type", "official",
    ),
    RuleInfo(
        RULE_BAD_MULTIDATASET_SUFFIX, "ABINIT105", "warning",
        "dataset suffix exceeds ndtset", "official",
    ),
    RuleInfo(
        RULE_LOOSE_TOLERANCE, "ABINIT106", "warning",
        "convergence tolerance is too loose for reliable results", "official",
    ),
    RuleInfo(
        RULE_UNKNOWN_KEYWORD, "ABINIT107", "warning",
        "unknown or unsupported ABINIT keyword", "official",
    ),
    RuleInfo(
        RULE_DUPLICATE_KEYWORD, "ABINIT108", "warning",
        "keyword is defined more than once", "official",
    ),
]


def get_rule_manifest() -> list[dict[str, str]]:
    """Return the rule manifest as a list of dicts for JSON export."""
    return [
        {
            "rule_id": r.rule_id,
            "code": r.code,
            "severity": r.severity,
            "description": r.description,
            "source": r.source,
        }
        for r in RULE_MANIFEST
    ]


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_missing_ecut(af: AbinitFile, path: Path) -> list[Diagnostic]:
    """RULE #14: Warn when ecut is missing from the input."""
    if af.has_keyword("ecut"):
        return []
    return [
        Diagnostic(
            code="ABINIT101",
            severity="warning",
            message="ecut is a required variable for ABINIT calculations",
            file=str(path),
            line=1,
            evidence=["MVP rule derived from MatMaster execution contracts"],
            suggested_fix={"kind": "add_required_token", "token": "ecut"},
            confidence=0.72,
        )
    ]


def check_missing_natom(af: AbinitFile, path: Path) -> list[Diagnostic]:
    """RULE #15: Error when natom is missing."""
    if af.has_keyword("natom"):
        return []
    return [
        Diagnostic(
            code="ABINIT102",
            severity="error",
            message="natom is required to define the crystal structure",
            file=str(path),
            line=1,
            evidence=["ABINIT requires natom for any calculation with atoms"],
            suggested_fix={"kind": "add_required_token", "token": "natom"},
            confidence=0.95,
        )
    ]


def check_inconsistent_typat_znucl(af: AbinitFile, path: Path) -> list[Diagnostic]:
    """RULE #16: Error when typat/znucl are inconsistent with ntypat."""
    diagnostics: list[Diagnostic] = []

    typat_entries = af.get_entries_for("typat")
    znucl_entries = af.get_entries_for("znucl")
    ntypat_entries = af.get_entries_for("ntypat")

    # Determine ntypat
    ntypat_val: int | None = None
    if ntypat_entries:
        try:
            ntypat_val = int(float(ntypat_entries[0].values[0]))
        except (ValueError, IndexError):
            pass

    # Check typat values reference valid type indices
    if typat_entries and ntypat_val is not None:
        for entry in typat_entries:
            for v in entry.values:
                try:
                    idx = int(float(v))
                    if idx < 1 or idx > ntypat_val:
                        diagnostics.append(
                            Diagnostic(
                                code="ABINIT103",
                                severity="error",
                                message=(
                                    f"typat value {idx} is out of range "
                                    f"[1, {ntypat_val}] defined by ntypat"
                                ),
                                file=str(path),
                                line=entry.line,
                                suggested_fix={
                                    "kind": "fix_typat_value",
                                    "value": str(idx),
                                    "ntypat": ntypat_val,
                                },
                                confidence=0.95,
                            )
                        )
                except (ValueError, IndexError):
                    pass

    # Check znucl count matches ntypat
    if znucl_entries and ntypat_val is not None:
        for entry in znucl_entries:
            if len(entry.values) != ntypat_val:
                diagnostics.append(
                    Diagnostic(
                        code="ABINIT103",
                        severity="error",
                        message=(
                            f"znucl has {len(entry.values)} values but "
                            f"ntypat={ntypat_val}"
                        ),
                        file=str(path),
                        line=entry.line,
                        suggested_fix={
                            "kind": "fix_znucl_count",
                            "expected": ntypat_val,
                            "actual": len(entry.values),
                        },
                        confidence=0.95,
                    )
                )

    # Cross-check: if typat and znucl both present but ntypat missing, infer
    if typat_entries and znucl_entries and ntypat_val is None:
        ntypat_inferred = (
            len(znucl_entries[0].values) if znucl_entries[0].values else 0
        )
        if ntypat_inferred > 0:
            for entry in typat_entries:
                for v in entry.values:
                    try:
                        idx = int(float(v))
                        if idx < 1 or idx > ntypat_inferred:
                            diagnostics.append(
                                Diagnostic(
                                    code="ABINIT103",
                                    severity="error",
                                    message=(
                                        f"typat value {idx} exceeds the "
                                        f"{ntypat_inferred} types implied by znucl"
                                    ),
                                    file=str(path),
                                    line=entry.line,
                                    confidence=0.9,
                                )
                            )
                    except (ValueError, IndexError):
                        pass

    return diagnostics


def check_invalid_variable_type(af: AbinitFile, path: Path) -> list[Diagnostic]:
    """RULE #17: Error when a variable value has the wrong type."""
    diagnostics: list[Diagnostic] = []

    for entry in af.entries:
        base = entry.base_keyword
        if not entry.values:
            continue

        first_val = entry.values[0]

        # Handle star notation (e.g. 3*10.26) - skip type check
        if "*" in first_val:
            continue

        # Integer keywords
        if base in _INT_KEYWORDS:
            try:
                fval = float(first_val)
                ival = int(fval)
                if fval != ival:
                    diagnostics.append(
                        Diagnostic(
                            code="ABINIT104",
                            severity="error",
                            message=(
                                f"keyword '{entry.keyword}' expects an integer "
                                f"value, got '{first_val}'"
                            ),
                            file=str(path),
                            line=entry.line,
                            suggested_fix={
                                "kind": "fix_value_type",
                                "keyword": entry.keyword,
                                "value": str(ival),
                            },
                            confidence=0.95,
                        )
                    )
            except ValueError:
                diagnostics.append(
                    Diagnostic(
                        code="ABINIT104",
                        severity="error",
                        message=(
                            f"keyword '{entry.keyword}' expects an integer "
                            f"value, got non-numeric '{first_val}'"
                        ),
                        file=str(path),
                        line=entry.line,
                        confidence=0.95,
                    )
                )

        # Float keywords
        if base in _FLOAT_KEYWORDS:
            try:
                float(first_val)
            except ValueError:
                # Could be Fortran scientific notation like 1.0d-6
                try:
                    float(first_val.replace("d", "e").replace("D", "E"))
                except ValueError:
                    diagnostics.append(
                        Diagnostic(
                            code="ABINIT104",
                            severity="error",
                            message=(
                                f"keyword '{entry.keyword}' expects a numeric "
                                f"value, got '{first_val}'"
                            ),
                            file=str(path),
                            line=entry.line,
                            confidence=0.95,
                        )
                    )

    return diagnostics


def check_bad_multidataset_suffix(af: AbinitFile, path: Path) -> list[Diagnostic]:
    """RULE #18: Warn when dataset suffix exceeds ndtset."""
    diagnostics: list[Diagnostic] = []

    # Find ndtset value
    ndtset_entries = af.get_entries_for("ndtset")
    if not ndtset_entries:
        # No multi-dataset, no suffix check needed
        return []

    try:
        ndtset = int(float(ndtset_entries[0].values[0]))
    except (ValueError, IndexError):
        return []

    if ndtset <= 0:
        return []

    # Check all entries with dataset suffixes
    for entry in af.entries:
        ds = entry.dataset
        if ds is not None and ds > ndtset:
            diagnostics.append(
                Diagnostic(
                    code="ABINIT105",
                    severity="warning",
                    message=(
                        f"keyword '{entry.keyword}' has dataset suffix {ds} "
                        f"but ndtset={ndtset}"
                    ),
                    file=str(path),
                    line=entry.line,
                    suggested_fix={
                        "kind": "fix_dataset_suffix",
                        "keyword": entry.keyword,
                        "suffix": ds,
                        "ndtset": ndtset,
                    },
                    confidence=0.9,
                )
            )

    return diagnostics


def check_loose_tolerance(af: AbinitFile, path: Path) -> list[Diagnostic]:
    """RULE #19: Warn when convergence tolerance is too loose."""
    diagnostics: list[Diagnostic] = []

    THRESHOLD_TOLDFE = 1e-4
    for entry in af.get_entries_for("toldfe"):
        if not entry.values:
            continue
        try:
            val = float(entry.values[0].replace("d", "e").replace("D", "E"))
            if val > THRESHOLD_TOLDFE:
                diagnostics.append(
                    Diagnostic(
                        code="ABINIT106",
                        severity="warning",
                        message=(
                            f"toldfe={val} is very loose; consider using "
                            f"a value < {THRESHOLD_TOLDFE} for reliable results"
                        ),
                        file=str(path),
                        line=entry.line,
                        suggested_fix={
                            "kind": "tighten_tolerance",
                            "keyword": "toldfe",
                            "current": val,
                            "suggested_max": THRESHOLD_TOLDFE,
                        },
                        confidence=0.8,
                    )
                )
        except ValueError:
            pass

    THRESHOLD_TOLVRS = 1e-6
    for entry in af.get_entries_for("tolvrs"):
        if not entry.values:
            continue
        try:
            val = float(entry.values[0].replace("d", "e").replace("D", "E"))
            if val > THRESHOLD_TOLVRS:
                diagnostics.append(
                    Diagnostic(
                        code="ABINIT106",
                        severity="warning",
                        message=(
                            f"tolvrs={val} is very loose; consider using "
                            f"a value < {THRESHOLD_TOLVRS} for reliable results"
                        ),
                        file=str(path),
                        line=entry.line,
                        suggested_fix={
                            "kind": "tighten_tolerance",
                            "keyword": "tolvrs",
                            "current": val,
                            "suggested_max": THRESHOLD_TOLVRS,
                        },
                        confidence=0.8,
                    )
                )
        except ValueError:
            pass

    THRESHOLD_TOLMXF = 1e-3
    for entry in af.get_entries_for("tolmxf"):
        if not entry.values:
            continue
        try:
            val = float(entry.values[0].replace("d", "e").replace("D", "E"))
            if val > THRESHOLD_TOLMXF:
                diagnostics.append(
                    Diagnostic(
                        code="ABINIT106",
                        severity="warning",
                        message=(
                            f"tolmxf={val} is very loose; consider using "
                            f"a value < {THRESHOLD_TOLMXF} for reliable results"
                        ),
                        file=str(path),
                        line=entry.line,
                        suggested_fix={
                            "kind": "tighten_tolerance",
                            "keyword": "tolmxf",
                            "current": val,
                            "suggested_max": THRESHOLD_TOLMXF,
                        },
                        confidence=0.8,
                    )
                )
        except ValueError:
            pass

    return diagnostics


def check_unknown_keywords(af: AbinitFile, path: Path) -> list[Diagnostic]:
    """RULE: Warn about unknown keywords."""
    diagnostics: list[Diagnostic] = []
    for entry in af.entries:
        base = entry.base_keyword
        if base not in _KNOWN_BASES:
            diagnostics.append(
                Diagnostic(
                    code="ABINIT107",
                    severity="warning",
                    message=(
                        f"unknown or unsupported ABINIT keyword: "
                        f"{entry.keyword}"
                    ),
                    file=str(path),
                    line=entry.line,
                    suggested_fix={
                        "kind": "check_keyword_spelling",
                        "keyword": entry.keyword,
                    },
                    confidence=0.55,
                )
            )
    return diagnostics


def check_duplicate_keywords(af: AbinitFile, path: Path) -> list[Diagnostic]:
    """RULE: Warn about duplicate keyword definitions."""
    diagnostics: list[Diagnostic] = []
    seen: dict[str, int] = {}
    for entry in af.entries:
        key = entry.keyword
        if key in seen:
            diagnostics.append(
                Diagnostic(
                    code="ABINIT108",
                    severity="warning",
                    message=(
                        f"duplicate keyword '{key}' "
                        f"(first defined on line {seen[key]})"
                    ),
                    file=str(path),
                    line=entry.line,
                    suggested_fix={"kind": "remove_duplicate", "keyword": key},
                    confidence=0.85,
                )
            )
        else:
            seen[key] = entry.line
    return diagnostics


# ---------------------------------------------------------------------------
# Main lint entry point
# ---------------------------------------------------------------------------


def lint_file(path: Path) -> list[Diagnostic]:
    """Run all parser-backed lint rules on an ABINIT file."""
    path = Path(path)
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [
            Diagnostic(
                "ABINIT202", "error", "file is not valid UTF-8 text",
                str(path), 1,
            )
        ]

    af = parse_content(path, content)
    diagnostics: list[Diagnostic] = []

    diagnostics.extend(check_missing_ecut(af, path))
    diagnostics.extend(check_missing_natom(af, path))
    diagnostics.extend(check_inconsistent_typat_znucl(af, path))
    diagnostics.extend(check_invalid_variable_type(af, path))
    diagnostics.extend(check_bad_multidataset_suffix(af, path))
    diagnostics.extend(check_loose_tolerance(af, path))
    diagnostics.extend(check_unknown_keywords(af, path))
    diagnostics.extend(check_duplicate_keywords(af, path))

    return sorted(diagnostics, key=lambda d: (d.file, d.line, d.code))


def lint_path(path: Path) -> list[Diagnostic]:
    """Lint a single file or directory."""
    path = Path(path)
    if path.is_file():
        return lint_file(path)
    if path.is_dir():
        diagnostics: list[Diagnostic] = []
        for pattern in ("*.abi", "*.abinit", "*.in"):
            for f in sorted(path.rglob(pattern)):
                if f.is_file():
                    diagnostics.extend(lint_file(f))
        if not diagnostics:
            found = any(
                f
                for pattern in ("*.abi", "*.abinit", "*.in")
                for f in path.rglob(pattern)
                if f.is_file()
            )
            if not found:
                diagnostics.append(
                    Diagnostic(
                        code="ABINIT201",
                        severity="error",
                        message="no supported ABINIT files found",
                        file=str(path),
                        line=1,
                    )
                )
        return sorted(diagnostics, key=lambda d: (d.file, d.line, d.code))
    return []
