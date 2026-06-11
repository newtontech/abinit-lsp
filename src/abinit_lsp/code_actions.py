"""Code actions for ABINIT input files.

Provides quick-fix actions for common ABINIT diagnostics: adding missing
required variables, fixing variable typos, and normalizing simple values.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .lint import lint_file
from .diagnostics import Diagnostic


@dataclass(frozen=True)
class CodeAction:
    """A code action (quick fix) for an ABINIT diagnostic."""

    title: str
    kind: str
    edits: list[dict[str, Any]]
    diagnostics: list[dict[str, Any]]

    def to_json(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "kind": self.kind,
            "edits": self.edits,
            "diagnostics": self.diagnostics,
        }


def get_code_actions(path: Path) -> list[CodeAction]:
    """Generate code actions for an ABINIT input file.

    Scans the file for diagnostics and produces suggested fixes.
    """
    path = Path(path)
    diagnostics = lint_file(path)
    actions: list[CodeAction] = []

    for diag in diagnostics:
        fix = diag.suggested_fix
        if fix is None:
            continue

        kind = fix.get("kind", "")

        if kind == "add_required_token":
            token = fix.get("token", "")
            if token:
                # Determine a reasonable default value
                defaults: dict[str, str] = {
                    "ecut": "30.0",
                    "natom": "1",
                    "typat": "1",
                    "znucl": "1",
                    "xred": "0.0 0.0 0.0",
                    "nstep": "100",
                    "toldfe": "1.0e-8",
                }
                value = defaults.get(token, "1")
                actions.append(
                    CodeAction(
                        title=f"Add missing variable '{token}'",
                        kind="quickfix",
                        edits=[
                            {
                                "file": diag.file,
                                "line": 1,
                                "column": 1,
                                "action": "insert",
                                "text": f"{token} {value}\n",
                            }
                        ],
                        diagnostics=[diag.to_json()],
                    )
                )

        elif kind == "fix_value_type":
            keyword = fix.get("keyword", "")
            value = fix.get("value", "")
            if keyword and value:
                actions.append(
                    CodeAction(
                        title=f"Fix '{keyword}' value type to '{value}'",
                        kind="quickfix",
                        edits=[
                            {
                                "file": diag.file,
                                "line": diag.line,
                                "column": 1,
                                "action": "replace_line",
                                "text": f"{keyword} {value}\n",
                            }
                        ],
                        diagnostics=[diag.to_json()],
                    )
                )

        elif kind == "remove_duplicate":
            keyword = fix.get("keyword", "")
            if keyword:
                actions.append(
                    CodeAction(
                        title=f"Remove duplicate '{keyword}'",
                        kind="quickfix",
                        edits=[
                            {
                                "file": diag.file,
                                "line": diag.line,
                                "column": 1,
                                "action": "delete_line",
                                "text": "",
                            }
                        ],
                        diagnostics=[diag.to_json()],
                    )
                )

        elif kind == "check_keyword_spelling":
            keyword = fix.get("keyword", "")
            if keyword:
                actions.append(
                    CodeAction(
                        title=f"Check spelling of '{keyword}'",
                        kind="quickfix",
                        edits=[],
                        diagnostics=[diag.to_json()],
                    )
                )

        elif kind == "fix_dataset_suffix":
            keyword = fix.get("keyword", "")
            if keyword:
                actions.append(
                    CodeAction(
                        title=f"Fix dataset suffix for '{keyword}'",
                        kind="quickfix",
                        edits=[],
                        diagnostics=[diag.to_json()],
                    )
                )

        elif kind == "tighten_tolerance":
            keyword = fix.get("keyword", "")
            suggested_max = fix.get("suggested_max", "")
            if keyword:
                actions.append(
                    CodeAction(
                        title=f"Tighten {keyword} to < {suggested_max}",
                        kind="quickfix",
                        edits=[],
                        diagnostics=[diag.to_json()],
                    )
                )

    return actions
