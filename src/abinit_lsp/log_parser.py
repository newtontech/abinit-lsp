"""Log parser for ABINIT runtime output.

Parses ABINIT standard output and log files for runtime diagnostics,
especially SCF convergence failures and error messages.
"""

from __future__ import annotations

import re
from pathlib import Path

from .diagnostics import Diagnostic

# ---------------------------------------------------------------------------
# Log patterns
# ---------------------------------------------------------------------------

# SCF did not converge patterns
_SCF_NOT_CONVERGED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "nstep_exceeded",
        re.compile(
            r"^\s*.*SCF.*not.*converged.*nstep",
            re.IGNORECASE,
        ),
    ),
    (
        "scf_failed",
        re.compile(
            r"^\s*.*SCF cycle did not converge",
            re.IGNORECASE,
        ),
    ),
    (
        "nstep_reached",
        re.compile(
            r"^\s*.*nstep.*reached.*convergence",
            re.IGNORECASE,
        ),
    ),
    (
        "cvxcen_failed",
        re.compile(
            r"^\s*.*cvxcen.*not.*converged",
            re.IGNORECASE,
        ),
    ),
]

# General error patterns
_ERROR_PATTERNS: list[tuple[str, re.Pattern[str], str, str | None]] = [
    (
        "allocation_error",
        re.compile(r"^\s*Allocation error", re.IGNORECASE),
        "ABINIT201",
        "Memory allocation failed during execution",
    ),
    (
        "input_error",
        re.compile(r"^\s*.*Action : check.*input file", re.IGNORECASE),
        "ABINIT202",
        "Input file validation failed",
    ),
    (
        "malloc_error",
        re.compile(r"^\s*.*malloc.*failed", re.IGNORECASE),
        "ABINIT201",
        "Memory allocation (malloc) failed",
    ),
    (
        "file_not_found",
        re.compile(r"^\s*.*file.*not found", re.IGNORECASE),
        "ABINIT203",
        "Required file not found",
    ),
    (
        "mpi_error",
        re.compile(r"^\s*.*MPI.*error", re.IGNORECASE),
        "ABINIT204",
        "MPI communication error",
    ),
    (
        "fatal_error",
        re.compile(r"^\s*.*Fatal error", re.IGNORECASE),
        "ABINIT205",
        "Fatal runtime error",
    ),
    (
        "stopped",
        re.compile(r"^\s*.*Stopped.*at.*iteration", re.IGNORECASE),
        "ABINIT200",
        "ABINIT stopped at an iteration",
    ),
    (
        "segfault",
        re.compile(r"^\s*.*segmentation fault", re.IGNORECASE),
        "ABINIT206",
        "Segmentation fault detected",
    ),
    (
        "pseudopotential_error",
        re.compile(r"^\s*.*pseudopotential.*error", re.IGNORECASE),
        "ABINIT207",
        "Pseudopotential loading or parsing error",
    ),
    (
        "divergence",
        re.compile(r"^\s*.*divergence.*detected", re.IGNORECASE),
        "ABINIT208",
        "Numerical divergence detected",
    ),
    (
        "memory_exceeded",
        re.compile(r"^\s*.*memory.*exceeded", re.IGNORECASE),
        "ABINIT209",
        "Memory limit exceeded",
    ),
]


_LOG_ERROR_FIXES: dict[str, dict[str, object]] = {
    "ABINIT201": {
        "kind": "fix_memory_allocation",
        "hints": ["reduce npband/npfft", "decrease FFT mesh", "check memory limits"],
    },
    "ABINIT202": {
        "kind": "fix_input_validation",
        "hints": ["check input syntax", "verify variable names", "validate dataset structure"],
    },
    "ABINIT203": {
        "kind": "fix_file_not_found",
        "hints": ["verify file paths", "check working directory", "ensure pseudopotentials exist"],
    },
    "ABINIT204": {
        "kind": "fix_mpi_error",
        "hints": ["check MPI configuration", "verify processor count", "check interconnect"],
    },
    "ABINIT205": {
        "kind": "fix_fatal_error",
        "hints": [
            "check log for details",
            "verify input parameters",
            "check ABINIT version compatibility",
        ],
    },
    "ABINIT206": {
        "kind": "fix_segmentation_fault",
        "hints": ["check array bounds", "verify memory allocation", "check input dimensions"],
    },
    "ABINIT207": {
        "kind": "fix_pseudopotential_error",
        "hints": [
            "verify pseudo file format",
            "check pseudo type compatibility",
            "download fresh pseudos",
        ],
    },
    "ABINIT208": {
        "kind": "fix_divergence",
        "hints": ["reduce mixing parameter", "check initial guess", "use different xc functional"],
    },
    "ABINIT209": {
        "kind": "fix_memory_exceeded",
        "hints": [
            "reduce k-points",
            "decrease cutoff energy",
            "use fewer bands",
            "increase system memory",
        ],
    },
}


def _suggested_fix_for_log_error(code: str) -> dict[str, object] | None:
    """Return a suggested fix envelope for a known log error code."""
    return _LOG_ERROR_FIXES.get(code)


def parse_log(content: str, path: Path) -> list[Diagnostic]:
    """Parse ABINIT log/output content for runtime diagnostics.

    Args:
        content: The log file content as a string.
        path: The path to the log file (used in diagnostic messages).

    Returns:
        A list of Diagnostic objects for any issues found.
    """
    # Imported lazily to avoid a circular import: lint.py imports parser.py
    # and parser.py does not import log_parser, but log_parser importing lint
    # at module load would pull parser -> lint -> ... chains eagerly.
    from .lint import enrich_diagnostic_provenance

    diagnostics: list[Diagnostic] = []
    lines = content.splitlines()

    for line_no, line in enumerate(lines, start=1):
        # Check SCF convergence failures
        for _label, pattern in _SCF_NOT_CONVERGED_PATTERNS:
            if pattern.match(line):
                diagnostics.append(
                    enrich_diagnostic_provenance(
                        Diagnostic(
                            code="ABINIT200",
                            severity="error",
                            message="SCF convergence failure in ABINIT run",
                            file=str(path),
                            line=line_no,
                            evidence=[line.strip()],
                            suggested_fix={
                                "kind": "fix_scf_convergence",
                                "hints": [
                                    "increase nstep",
                                    "tighten tolerance (toldfe/tolvrs)",
                                    "adjust diemix",
                                    "check initial guess",
                                ],
                            },
                            confidence=0.95,
                        )
                    )
                )
                break  # One diagnostic per line at most

        # Check general errors
        for _label, pattern, code, message in _ERROR_PATTERNS:
            if pattern.match(line):
                diagnostics.append(
                    enrich_diagnostic_provenance(
                        Diagnostic(
                            code=code,
                            severity="error",
                            message=message or f"ABINIT runtime error: {line.strip()}",
                            file=str(path),
                            line=line_no,
                            evidence=[line.strip()],
                            suggested_fix=_suggested_fix_for_log_error(code),
                            confidence=0.9,
                        )
                    )
                )
                break

    return diagnostics


def parse_log_file(path: Path) -> list[Diagnostic]:
    """Parse an ABINIT log file from a filesystem path."""
    path = Path(path)
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return parse_log(content, path)
