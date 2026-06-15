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
_ERROR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "allocation_error",
        re.compile(r"^\s*Allocation error", re.IGNORECASE),
    ),
    (
        "input_error",
        re.compile(r"^\s*.*Action : check.*input file", re.IGNORECASE),
    ),
    (
        "malloc_error",
        re.compile(r"^\s*.*malloc.*failed", re.IGNORECASE),
    ),
    (
        "file_not_found",
        re.compile(r"^\s*.*file.*not found", re.IGNORECASE),
    ),
    (
        "mpi_error",
        re.compile(r"^\s*.*MPI.*error", re.IGNORECASE),
    ),
    (
        "fatal_error",
        re.compile(r"^\s*.*Fatal error", re.IGNORECASE),
    ),
    (
        "stopped",
        re.compile(r"^\s*.*Stopped.*at.*iteration", re.IGNORECASE),
    ),
]


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
        for _label, pattern in _ERROR_PATTERNS:
            if pattern.match(line):
                diagnostics.append(
                    enrich_diagnostic_provenance(
                        Diagnostic(
                            code="ABINIT201",
                            severity="error",
                            message=f"ABINIT runtime error: {line.strip()}",
                            file=str(path),
                            line=line_no,
                            evidence=[line.strip()],
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
