"""Universal generated-input preflight capabilities.

This module implements the four fleet-wide preflight capabilities called out in
``newtontech/abinit-lsp#32`` against a *generic artifact-role model*, so the
checks generalize to any backend in the scientific LSP fleet instead of being
wired to MatMaster submission policy:

* ``version-aware-keywords``  - explicit runtime/version assumption metadata
  and keyword-availability validation derived from the builtin keyword set,
  never guessed.
* ``cross-artifact-graph``   - resolves the case as a graph of artifacts with
  stable roles (primary-input, structure, kpoints, pseudopotential, lattice).
  For ABINIT the structure/kpoints/lattice roles are in-file sections of the
  primary ``.abi`` input, while the pseudopotential role is the one true
  cross-file artifact (external files referenced by the ``pseudos`` keyword).
  The same role set generalizes to the rest of the fleet (VASP/CP2K/...).
* ``code-actions``           - normalizes repair hints/actions on every
  diagnostic and exposes a blocking gate the agent CLI can run as
  ``check --fail-on-blocking``.
* ``fleet-regression-fixtures`` - ``fleet_manifest`` returns a machine-readable
  description of the preflight surface (codes, capabilities, fixture
  expectations) so the parent ``bohrium_skills`` probe/report workflow can
  consume regression evidence without re-deriving it.

The diagnostics emitted here are plain dictionaries (not the legacy
``Diagnostic`` dataclass) so they can carry the richer ``DiagnosticEnvelope/v1``
fields (``source_provenance``, ``domain_tags``, ``facts``, ``artifact_roles``,
``version_assumption``, ``actions``) directly.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .parser import parse

# --- Artifact-role model ---------------------------------------------------

# Generic roles. These are intentionally software-agnostic: every fleet backend
# can map its native files/sections onto this same small role set, which is
# what lets the parent router consume cross-file checks without learning
# MatMaster specifics. For ABINIT the primary-input ``.abi`` file holds the
# in-file structure/kpoints/lattice sections; only pseudopotentials are real
# external artifacts. The graph records both kinds uniformly.
ROLE_PRIMARY_INPUT = "primary-input"
ROLE_STRUCTURE = "structure"
ROLE_KPOINTS = "kpoints"
ROLE_PSEUDOPOTENTIAL = "pseudopotential"
ROLE_ORBITAL = "orbital"
ROLE_LATTICE = "lattice"

ALL_ROLES = (
    ROLE_PRIMARY_INPUT,
    ROLE_STRUCTURE,
    ROLE_KPOINTS,
    ROLE_PSEUDOPOTENTIAL,
    ROLE_ORBITAL,
    ROLE_LATTICE,
)

# Conservative workflow threshold used by the warning-level ecut check. ABINIT
# documents ecut in Hartree (unlike ABACUS ecutwfc in Ry). The actual cutoff is
# overridable via the preflight intent contract; this is only the default fleet
# baseline, not a MatMaster policy.
DEFAULT_ECUT_WARNING_HA = 15.0

# Codes reserved for the universal preflight surface. They use the ``ABINIT6xx``
# band so they sort after existing rule codes (ABINIT0xx/1xx) and stay
# identifiable as cross-fleet preflight findings.
CODE_MISSING_INPUT = "ABINIT601"
CODE_MISSING_STRUCTURE = "ABINIT602"
CODE_MISSING_LATTICE = "ABINIT603"
CODE_NTYPAT_ZNUCL_MISMATCH = "ABINIT604"
CODE_UNRESOLVED_PSEUDO = "ABINIT605"
CODE_MISSING_PSEUDOS = "ABINIT606"
CODE_LOW_ECUT = "ABINIT607"
CODE_SUSPICIOUS_KPOINTS = "ABINIT608"
CODE_VERSION_ASSUMPTION = "ABINIT609"
CODE_UNKNOWN_KEYWORD_VERSION = "ABINIT610"

# Keywords that define the in-file structure section.
_STRUCTURE_KEYWORDS = {"natom", "typat", "znucl", "xred", "xcart", "xangst"}
# Keywords that define the in-file lattice section.
_LATTICE_KEYWORDS = {"rprim", "acell", "scalecart", "angdeg", "rprimd"}
# Keywords that define the in-file kpoints section.
_KPOINT_KEYWORDS = {"ngkpt", "kptopt", "shiftk", "nshiftk", "kptnrm", "istwfk"}


@dataclass(frozen=True)
class ArtifactNode:
    """A node in the cross-artifact graph.

    ``role`` is one of the fleet-generic roles above; ``path`` is the resolved
    filesystem path (may be a non-existent reference, which is itself a
    finding) or, for in-file ABINIT sections, the primary input path;
    ``exists`` records whether the artifact is present; ``source`` records
    where the reference originated so consumers can trace provenance.
    """

    role: str
    path: Path
    exists: bool
    source: str
    referenced_from: tuple[str, int] | None = None
    detail: dict[str, Any] | None = None


@dataclass
class ArtifactGraph:
    """Generic cross-artifact graph built from a parsed case directory."""

    case_dir: Path
    nodes: list[ArtifactNode] = field(default_factory=list)

    def by_role(self, role: str) -> list[ArtifactNode]:
        return [node for node in self.nodes if node.role == role]

    def to_json(self) -> list[dict[str, Any]]:
        """Serialize the graph for the parent probe/report workflow."""

        def _node_json(node: ArtifactNode) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "role": node.role,
                "path": str(node.path),
                "exists": node.exists,
                "source": node.source,
            }
            if node.referenced_from is not None:
                payload["referenced_from"] = {
                    "path": node.referenced_from[0],
                    "line": node.referenced_from[1],
                }
            if node.detail:
                payload["detail"] = node.detail
            return payload

        return sorted(
            (_node_json(node) for node in self.nodes),
            key=lambda item: (item["role"], item["path"]),
        )


def _find_primary_input(case_dir: Path) -> Path | None:
    """Locate the primary ABINIT input file in a case directory.

    ABINIT conventionally takes the input from ``.abi`` / ``.abinit`` / ``.in``
    files. We pick the first match so the graph has a stable primary node.
    """
    for pattern in ("*.abi", "*.abinit", "*.in"):
        for candidate in sorted(case_dir.glob(pattern)):
            if candidate.is_file():
                return candidate
    return None


def _keyword_value(abinit_file: Any, keyword: str) -> tuple[list[str], int] | None:
    """Return (values, line) for a keyword in a parsed AbinitFile, or None."""
    entries = abinit_file.get_entries_for(keyword)
    if not entries:
        return None
    entry = entries[0]
    return entry.values, entry.line


def _keyword_line(abinit_file: Any, keyword: str) -> int:
    entries = abinit_file.get_entries_for(keyword)
    return entries[0].line if entries else 1


def _has_any(abinit_file: Any, keywords: Iterable[str]) -> bool:
    return any(abinit_file.has_keyword(kw) for kw in keywords)


def _resolve_dir(case_dir: Path, declared: str | None) -> Path:
    if not declared:
        return case_dir
    candidate = Path(declared)
    if candidate.is_absolute():
        return candidate
    return case_dir / candidate


def build_artifact_graph(
    case_dir: Path,
    abinit_file: Any,
    input_path: Path,
) -> ArtifactGraph:
    """Build the cross-artifact graph from a parsed ABINIT input.

    The model is generic: it records roles + resolved paths + provenance. The
    same shape generalizes to other fleet backends because it never bakes in
    MatMaster/Bohrium runtime concepts (no input_dir, no image, no session).
    """
    case_dir = case_dir.resolve()
    graph = ArtifactGraph(case_dir=case_dir)

    graph.nodes.append(
        ArtifactNode(
            role=ROLE_PRIMARY_INPUT,
            path=input_path,
            exists=input_path.exists(),
            source="case-root",
        )
    )

    # In-file structure section.
    has_structure = _has_any(abinit_file, _STRUCTURE_KEYWORDS)
    structure_line = min(
        (
            abinit_file.get_entries_for(kw)[0].line
            for kw in _STRUCTURE_KEYWORDS
            if abinit_file.has_keyword(kw)
        ),
        default=1,
    )
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_STRUCTURE,
            path=input_path,
            exists=has_structure,
            source="abi:structure-section",
            referenced_from=(str(input_path), structure_line),
            detail={"keywords_present": sorted(_present(abinit_file, _STRUCTURE_KEYWORDS))},
        )
    )

    # In-file kpoints section.
    has_kpoints = _has_any(abinit_file, _KPOINT_KEYWORDS)
    kpt_line = min(
        (
            abinit_file.get_entries_for(kw)[0].line
            for kw in _KPOINT_KEYWORDS
            if abinit_file.has_keyword(kw)
        ),
        default=1,
    )
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_KPOINTS,
            path=input_path,
            exists=has_kpoints,
            source="abi:kpoints-section",
            referenced_from=(str(input_path), kpt_line),
            detail={"keywords_present": sorted(_present(abinit_file, _KPOINT_KEYWORDS))},
        )
    )

    # In-file lattice section.
    has_lattice = _has_any(abinit_file, _LATTICE_KEYWORDS)
    lat_line = min(
        (
            abinit_file.get_entries_for(kw)[0].line
            for kw in _LATTICE_KEYWORDS
            if abinit_file.has_keyword(kw)
        ),
        default=1,
    )
    graph.nodes.append(
        ArtifactNode(
            role=ROLE_LATTICE,
            path=input_path,
            exists=has_lattice,
            source="abi:lattice-section",
            referenced_from=(str(input_path), lat_line),
            detail={"keywords_present": sorted(_present(abinit_file, _LATTICE_KEYWORDS))},
        )
    )

    # Pseudopotential references (the only true cross-file artifact for ABINIT).
    pseudo_dir_value = _first_value(abinit_file, "pp_dirpath")
    pseudos_entry = _keyword_value(abinit_file, "pseudos")
    if pseudos_entry is not None:
        pseudo_line = _keyword_line(abinit_file, "pseudos")
        for filename in pseudos_entry[0]:
            resolved = _resolve_dir(case_dir, pseudo_dir_value) / filename
            graph.nodes.append(
                ArtifactNode(
                    role=ROLE_PSEUDOPOTENTIAL,
                    path=resolved,
                    exists=resolved.exists(),
                    source=f"abi:pseudos:{filename}",
                    referenced_from=(str(input_path), pseudo_line),
                    detail=(
                        {"declared_dir": pseudo_dir_value} if pseudo_dir_value else None
                    ),
                )
            )

    return graph


def _present(abinit_file: Any, keywords: Iterable[str]) -> list[str]:
    return [kw for kw in keywords if abinit_file.has_keyword(kw)]


def _first_value(abinit_file: Any, keyword: str) -> str | None:
    entry = _keyword_value(abinit_file, keyword)
    if entry is None or not entry[0]:
        return None
    return entry[0][0]


# --- Preflight diagnostics -------------------------------------------------


def preflight_diagnostics(
    case_dir: Path,
    *,
    intent: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], ArtifactGraph]:
    """Run universal generated-input preflight checks.

    Returns a tuple of (diagnostics, artifact_graph). Diagnostics are envelope
    dicts carrying the full ``DiagnosticEnvelope/v1`` field set so the agent
    CLI can emit them directly without re-shaping.
    """
    case_dir = case_dir.resolve()
    input_path = _find_primary_input(case_dir)
    if input_path is None:
        # No primary input at all: emit a single blocking finding and return
        # an empty graph. The legacy single-file lint path still flags
        # unsupported files; this finding is the preflight-specific view.
        empty_graph = ArtifactGraph(case_dir=case_dir)
        finding = _diag(
            code=CODE_MISSING_INPUT,
            severity="error",
            message=(
                "primary-input artifact not found: expected a .abi/.abinit/.in "
                "file in the case directory"
            ),
            path=case_dir / "<missing-input>",
            line=1,
            category="cross-file reference",
            confidence=0.97,
            blocking=True,
            source_provenance={
                "role": ROLE_PRIMARY_INPUT,
                "reason": "no .abi/.abinit/.in file in case directory",
            },
            fix_hints=[
                "Add an ABINIT input file (.abi/.abinit/.in) to the case directory",
            ],
            actions=[
                {
                    "kind": "create_artifact",
                    "role": ROLE_PRIMARY_INPUT,
                    "target": str(case_dir / "input.abi"),
                    "safe_to_auto_apply": False,
                }
            ],
            facts={"case_dir": str(case_dir)},
            artifact_roles=[ROLE_PRIMARY_INPUT],
            domain_tags=["cross-file", "blocking"],
        )
        return [finding], empty_graph

    abinit_file = parse(input_path)
    graph = build_artifact_graph(case_dir, abinit_file, input_path)

    version_assumption = resolve_version_assumption(intent)
    diagnostics: list[dict[str, Any]] = []
    diagnostics.extend(_structure_diagnostics(graph, abinit_file, input_path))
    diagnostics.extend(_lattice_diagnostics(graph, abinit_file, input_path))
    diagnostics.extend(_kpoints_presence_diagnostics(graph, abinit_file, input_path))
    diagnostics.extend(_ntypat_znucl_diagnostics(abinit_file, input_path))
    diagnostics.extend(_pseudos_diagnostics(graph, abinit_file, input_path))
    diagnostics.extend(_unresolved_pseudo_diagnostics(graph))
    diagnostics.extend(_low_ecut_diagnostics(abinit_file, input_path, intent))
    diagnostics.extend(_suspicious_kpoints_diagnostics(abinit_file, input_path))
    diagnostics.extend(
        _version_keyword_diagnostics(abinit_file, input_path, version_assumption)
    )
    diagnostics.extend(_version_assumption_diagnostic(version_assumption, intent, input_path))

    return sorted(
        diagnostics,
        key=lambda item: (
            item.get("range", {}).get("start", {}).get("line", 0),
            item.get("range", {}).get("start", {}).get("character", 0),
            item["code"],
        ),
    ), graph


def _diag(
    *,
    code: str,
    severity: str,
    message: str,
    path: Path,
    line: int = 1,
    column: int = 1,
    category: str,
    confidence: float,
    blocking: bool,
    source_provenance: dict[str, Any],
    fix_hints: list[str],
    actions: list[dict[str, Any]] | None = None,
    facts: dict[str, Any] | None = None,
    artifact_roles: list[str] | None = None,
    domain_tags: list[str] | None = None,
    version_assumption: dict[str, Any] | None = None,
    manual_ref: str | None = None,
    intent: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single normalized preflight diagnostic.

    Carries every field the issue acceptance criteria require (``code``,
    ``severity``, ``path``/``range``, ``blocking``, ``category``,
    ``source_provenance``, ``fix_hints``/``actions``) plus the richer envelope
    fields (``facts``, ``artifact_roles``, ``domain_tags``,
    ``version_assumption``) used by the parent fleet probe.
    """
    line0 = max(line - 1, 0)
    col0 = max(column - 1, 0)
    payload: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
        "file": str(path),
        "line": line,
        "column": column,
        "category": category,
        "confidence": confidence,
        "source": "abinit-preflight",
        "range": {
            "start": {"line": line0, "character": col0},
            "end": {"line": line0, "character": col0 + 1},
        },
        "blocking": blocking,
        "fix_hints": fix_hints,
        "source_provenance": source_provenance,
    }
    if actions:
        payload["actions"] = actions
    if facts:
        payload["facts"] = facts
    if artifact_roles:
        payload["artifact_roles"] = artifact_roles
    if domain_tags:
        payload["domain_tags"] = domain_tags
    if version_assumption:
        payload["version_assumption"] = version_assumption
    if manual_ref:
        payload["manual_ref"] = manual_ref
    if intent:
        payload["intent"] = intent
    return payload


def _structure_diagnostics(
    graph: ArtifactGraph, abinit_file: Any, input_path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in graph.by_role(ROLE_STRUCTURE):
        if node.exists:
            continue
        ref = node.referenced_from or (str(input_path), 1)
        out.append(
            _diag(
                code=CODE_MISSING_STRUCTURE,
                severity="error",
                message=(
                    "structure section missing: ABINIT input declares no "
                    "natom/typat/znucl/xred (or xcart) variables"
                ),
                path=node.path,
                line=ref[1],
                category="cross-file reference",
                confidence=0.95,
                blocking=True,
                source_provenance={
                    "role": ROLE_STRUCTURE,
                    "referenced_from": {"path": ref[0], "line": ref[1]},
                    "declared_in": node.source,
                },
                fix_hints=[
                    "Add natom, typat, znucl and xred (or xcart) to the input",
                ],
                actions=[
                    {
                        "kind": "insert_keywords",
                        "keywords": ["natom", "typat", "znucl", "xred"],
                        "target": str(node.path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"keywords_present": (node.detail or {}).get("keywords_present", [])},
                artifact_roles=[ROLE_STRUCTURE, ROLE_PRIMARY_INPUT],
                domain_tags=["cross-file", "blocking"],
            )
        )
    return out


def _lattice_diagnostics(
    graph: ArtifactGraph, abinit_file: Any, input_path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in graph.by_role(ROLE_LATTICE):
        if node.exists:
            continue
        ref = node.referenced_from or (str(input_path), 1)
        out.append(
            _diag(
                code=CODE_MISSING_LATTICE,
                severity="error",
                message=(
                    "lattice section missing: ABINIT input declares no "
                    "rprim/acell (or angdeg/rprimd) variables"
                ),
                path=node.path,
                line=ref[1],
                category="cross-file reference",
                confidence=0.95,
                blocking=True,
                source_provenance={
                    "role": ROLE_LATTICE,
                    "referenced_from": {"path": ref[0], "line": ref[1]},
                    "declared_in": node.source,
                },
                fix_hints=[
                    "Add rprim (primitive vectors) and acell (lattice scales)",
                    "Or set angdeg + acell for a Bravais lattice",
                ],
                actions=[
                    {
                        "kind": "insert_keywords",
                        "keywords": ["rprim", "acell"],
                        "target": str(node.path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"keywords_present": (node.detail or {}).get("keywords_present", [])},
                artifact_roles=[ROLE_LATTICE, ROLE_PRIMARY_INPUT],
                domain_tags=["cross-file", "blocking"],
            )
        )
    return out


def _kpoints_presence_diagnostics(
    graph: ArtifactGraph, abinit_file: Any, input_path: Path
) -> list[dict[str, Any]]:
    """Flag a missing kpoints section as a non-blocking warning.

    ABINIT defaults to a single k-point when ngkpt is unset, which silently
    produces meaningless band energies for metals/semiconductors. We surface
    this as a non-blocking warning so the parent probe can act on it without
    blocking legitimate gamma-only test inputs.
    """
    out: list[dict[str, Any]] = []
    for node in graph.by_role(ROLE_KPOINTS):
        if node.exists:
            continue
        ref = node.referenced_from or (str(input_path), 1)
        out.append(
            _diag(
                code=CODE_SUSPICIOUS_KPOINTS,
                severity="warning",
                message=(
                    "kpoints section missing: ABINIT will default to a single "
                    "(Gamma) k-point, which risks silently inaccurate results"
                ),
                path=node.path,
                line=ref[1],
                category="preflight/runtime-risk",
                confidence=0.75,
                blocking=False,
                source_provenance={
                    "role": ROLE_KPOINTS,
                    "referenced_from": {"path": ref[0], "line": ref[1]},
                    "declared_in": node.source,
                },
                fix_hints=[
                    "Add ngkpt (and kptopt) to declare a k-point mesh",
                    "Or document that a single k-point is intentional",
                ],
                actions=[
                    {
                        "kind": "insert_keywords",
                        "keywords": ["ngkpt", "kptopt"],
                        "target": str(node.path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"keywords_present": (node.detail or {}).get("keywords_present", [])},
                artifact_roles=[ROLE_KPOINTS, ROLE_PRIMARY_INPUT],
                domain_tags=["preflight", "runtime-risk"],
            )
        )
    return out


def _ntypat_znucl_diagnostics(
    abinit_file: Any, input_path: Path
) -> list[dict[str, Any]]:
    """Cross-check ntypat against the znucl array length and typat values.

    This is the generic "declared count vs evidence count" cross-artifact
    check that ABACUS expresses as ntype-vs-species; for ABINIT the species
    list is the znucl array.
    """
    out: list[dict[str, Any]] = []
    ntypat_entry = _keyword_value(abinit_file, "ntypat")
    znucl_entry = _keyword_value(abinit_file, "znucl")
    if ntypat_entry is None or znucl_entry is None:
        return out
    try:
        declared = int(float(ntypat_entry[0][0]))
    except (ValueError, IndexError):
        return out
    znucl_count = len(znucl_entry[0])
    if declared != znucl_count:
        line = ntypat_entry[1]
        out.append(
            _diag(
                code=CODE_NTYPAT_ZNUCL_MISMATCH,
                severity="error",
                message=(
                    f"ntypat={declared} does not match the {znucl_count} "
                    "atomic numbers declared in znucl"
                ),
                path=input_path,
                line=line,
                category="semantic consistency",
                confidence=0.96,
                blocking=True,
                source_provenance={
                    "role": ROLE_PRIMARY_INPUT,
                    "cross_referenced_role": ROLE_STRUCTURE,
                    "parsed_ntypat": declared,
                    "parsed_znucl": znucl_entry[0],
                },
                fix_hints=[
                    f"Set ntypat {znucl_count} to match the znucl array",
                    "Or correct the znucl list to match ntypat",
                ],
                actions=[
                    {
                        "kind": "set_keyword",
                        "keyword": "ntypat",
                        "value": str(znucl_count),
                        "target": str(input_path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={
                    "declared_ntypat": declared,
                    "znucl_count": znucl_count,
                    "znucl": znucl_entry[0],
                },
                artifact_roles=[ROLE_PRIMARY_INPUT, ROLE_STRUCTURE],
                domain_tags=["cross-file", "blocking"],
            )
        )
    return out


def _pseudos_diagnostics(
    graph: ArtifactGraph, abinit_file: Any, input_path: Path
) -> list[dict[str, Any]]:
    """Flag inputs that declare structure variables but no pseudopotentials.

    ABINIT reads pseudopotential filenames from the ``pseudos`` keyword (and
    optionally their directory from ``pp_dirpath``). A structure-declaring
    input without pseudos will fail at runtime, so we surface it as a
    blocking cross-artifact finding.
    """
    out: list[dict[str, Any]] = []
    has_structure = _has_any(abinit_file, _STRUCTURE_KEYWORDS)
    pseudos_entry = _keyword_value(abinit_file, "pseudos")
    if has_structure and pseudos_entry is None:
        out.append(
            _diag(
                code=CODE_MISSING_PSEUDOS,
                severity="error",
                message=(
                    "pseudopotential artifact missing: structure variables are "
                    "declared but the pseudos keyword is absent"
                ),
                path=input_path,
                line=1,
                category="cross-file reference",
                confidence=0.9,
                blocking=True,
                source_provenance={
                    "role": ROLE_PSEUDOPOTENTIAL,
                    "reason": "pseudos keyword absent while structure is declared",
                },
                fix_hints=[
                    "Add a pseudos keyword listing one file per atomic species",
                ],
                actions=[
                    {
                        "kind": "insert_keywords",
                        "keywords": ["pseudos"],
                        "target": str(input_path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"has_structure": has_structure},
                artifact_roles=[ROLE_PSEUDOPOTENTIAL, ROLE_PRIMARY_INPUT],
                domain_tags=["cross-file", "blocking"],
            )
        )
    # Count mismatch between znucl species and pseudos files.
    if pseudos_entry is not None:
        znucl_entry = _keyword_value(abinit_file, "znucl")
        if znucl_entry is not None:
            znucl_count = len(znucl_entry[0])
            pseudo_count = len(pseudos_entry[0])
            if znucl_count != pseudo_count:
                line = pseudos_entry[1]
                out.append(
                    _diag(
                        code=CODE_NTYPAT_ZNUCL_MISMATCH,
                        severity="error",
                        message=(
                            f"pseudos lists {pseudo_count} files but znucl "
                            f"declares {znucl_count} species"
                        ),
                        path=input_path,
                        line=line,
                        category="semantic consistency",
                        confidence=0.95,
                        blocking=True,
                        source_provenance={
                            "role": ROLE_PSEUDOPOTENTIAL,
                            "cross_referenced_role": ROLE_STRUCTURE,
                            "parsed_pseudo_count": pseudo_count,
                            "parsed_znucl_count": znucl_count,
                        },
                        fix_hints=[
                            f"List exactly {znucl_count} pseudopotential files",
                            "Or correct znucl to match the pseudos list",
                        ],
                        actions=[
                            {
                                "kind": "set_keyword",
                                "keyword": "pseudos",
                                "value": f"<{znucl_count} pseudo files>",
                                "target": str(input_path),
                                "safe_to_auto_apply": False,
                            }
                        ],
                        facts={
                            "pseudo_count": pseudo_count,
                            "znucl_count": znucl_count,
                        },
                        artifact_roles=[ROLE_PSEUDOPOTENTIAL, ROLE_STRUCTURE],
                        domain_tags=["cross-file", "blocking"],
                    )
                )
    return out


def _unresolved_pseudo_diagnostics(graph: ArtifactGraph) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in graph.by_role(ROLE_PSEUDOPOTENTIAL):
        if node.exists:
            continue
        ref = node.referenced_from or (str(node.path), 1)
        out.append(
            _diag(
                code=CODE_UNRESOLVED_PSEUDO,
                severity="warning",
                message=(
                    f"pseudopotential artifact referenced from pseudos cannot "
                    f"be resolved: {node.path.name}"
                ),
                path=node.path,
                line=ref[1],
                category="cross-file reference",
                confidence=0.85,
                blocking=False,
                source_provenance={
                    "role": ROLE_PSEUDOPOTENTIAL,
                    "declared_in": node.source,
                    "declared_dir": (node.detail or {}).get("declared_dir"),
                    "referenced_from": {"path": ref[0], "line": ref[1]},
                },
                fix_hints=[
                    f"Place {node.path.name} in the declared directory",
                    "Or correct pp_dirpath in the input",
                ],
                actions=[
                    {
                        "kind": "resolve_artifact",
                        "role": ROLE_PSEUDOPOTENTIAL,
                        "target": str(node.path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"unresolved_path": str(node.path)},
                artifact_roles=[ROLE_PSEUDOPOTENTIAL],
                domain_tags=["cross-file", "workspace-resolve"],
            )
        )
    return out


def _low_ecut_diagnostics(
    abinit_file: Any, input_path: Path, intent: dict[str, Any] | None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    ecut_entry = _keyword_value(abinit_file, "ecut")
    if ecut_entry is None:
        return out
    try:
        ecut = float(ecut_entry[0][0])
    except (ValueError, IndexError):
        return out
    threshold = float(
        (intent or {}).get("ecut_warning_ha", DEFAULT_ECUT_WARNING_HA)
    )
    high_accuracy = bool((intent or {}).get("high_accuracy_production", False))
    if ecut < threshold:
        severity = "warning"
        message = (
            f"ecut={ecut} Ha is below the conservative workflow threshold "
            f"({threshold} Ha)"
        )
        if high_accuracy:
            message += "; intent marks this as high-accuracy production input"
        line = ecut_entry[1]
        out.append(
            _diag(
                code=CODE_LOW_ECUT,
                severity=severity,
                message=message,
                path=input_path,
                line=line,
                category="preflight/runtime-risk",
                confidence=0.8,
                blocking=False,
                source_provenance={
                    "role": ROLE_PRIMARY_INPUT,
                    "keyword": "ecut",
                    "threshold_source": (
                        "intent" if "ecut_warning_ha" in (intent or {}) else "default"
                    ),
                },
                fix_hints=[
                    f"Raise ecut to at least {threshold} Ha",
                    "Or document the lower cutoff in the intent contract",
                ],
                actions=[
                    {
                        "kind": "set_keyword",
                        "keyword": "ecut",
                        "value": str(threshold),
                        "target": str(input_path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={
                    "ecut": ecut,
                    "threshold": threshold,
                    "high_accuracy_production": high_accuracy,
                },
                artifact_roles=[ROLE_PRIMARY_INPUT],
                domain_tags=["preflight", "runtime-risk"],
            )
        )
    return out


def _suspicious_kpoints_diagnostics(
    abinit_file: Any, input_path: Path
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    ngkpt_entry = _keyword_value(abinit_file, "ngkpt")
    if ngkpt_entry is None:
        return out
    try:
        grid = [int(float(v)) for v in ngkpt_entry[0][:3]]
    except (ValueError, IndexError):
        return out
    if len(grid) < 3:
        return out
    if any(component <= 1 for component in grid):
        line = ngkpt_entry[1]
        out.append(
            _diag(
                code=CODE_SUSPICIOUS_KPOINTS,
                severity="warning",
                message=(
                    f"k-point grid {grid} contains a 1-point axis; "
                    "under-sampling risks silently inaccurate results for "
                    "low-dimensional systems"
                ),
                path=input_path,
                line=line,
                category="preflight/runtime-risk",
                confidence=0.7,
                blocking=False,
                source_provenance={
                    "role": ROLE_KPOINTS,
                    "grid": grid,
                    "keyword": "ngkpt",
                },
                fix_hints=[
                    "Increase the sparse k-point axis",
                    "Or confirm the system is genuinely low-dimensional",
                ],
                actions=[
                    {
                        "kind": "set_keyword",
                        "keyword": "ngkpt",
                        "value": " ".join(str(max(c, 2)) for c in grid),
                        "target": str(input_path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={"grid": grid, "keyword": "ngkpt"},
                artifact_roles=[ROLE_KPOINTS],
                domain_tags=["preflight", "runtime-risk"],
            )
        )
    return out


# --- version-aware-keywords ------------------------------------------------


def resolve_version_assumption(intent: dict[str, Any] | None) -> dict[str, Any]:
    """Resolve the explicit runtime/version assumption for this preflight run.

    When the exact runtime/image version is unknown we record that fact
    explicitly rather than guessing, per the issue's version-assumptions
    acceptance criterion. The intent contract can override
    ``software_version`` (e.g. ``abinit >=9.6``); otherwise we fall back to the
    schema version the builtin keyword set was authored against.
    """
    intent = intent or {}
    software_version = intent.get("software_version")
    runtime_image = intent.get("runtime_image")
    assumption: dict[str, Any] = {
        "software": "abinit",
        "software_version": software_version or "unknown",
        "runtime_image": runtime_image or "unknown",
        "schema_source": intent.get("schema_source", "abinit-lsp builtin"),
        # The fallback is intentional and explicit so consumers never have to
        # guess whether ``unknown`` means "not checked" or "could not determine".
        "exact_runtime_known": bool(software_version or runtime_image),
    }
    if software_version or runtime_image:
        assumption["declared_by"] = "intent"
    else:
        assumption["declared_by"] = "fallback"
    return assumption


# Keywords introduced or only valid for recent ABINIT versions, with the
# minimal version each one requires. This is the version-aware schema that
# drives CODE_UNKNOWN_KEYWORD_VERSION: when a keyword is used below its
# introduction version, the parent probe can act on the mismatch.
_VERSIONED_KEYWORDS: dict[str, str] = {
    # Each value documents the minimal ABINIT version that introduced the
    # keyword, so preflight can flag inputs that rely on it without declaring
    # a compatible runtime version.
    "ecutsm": "abinit >=6.0",
    "ionmov": "abinit >=4.0",
    "optcell": "abinit >=4.0",
    "dilatmx": "abinit >=4.0",
    "pawxcdev": "abinit >=7.0",
    "usepaw": "abinit >=4.3",
    "gwcalctyp": "abinit >=5.0",
    "npsp": "abinit >=8.0",
}


def _version_keyword_diagnostics(
    abinit_file: Any,
    input_path: Path,
    version_assumption: dict[str, Any],
) -> list[dict[str, Any]]:
    """Flag keywords whose declared availability is newer than the runtime assumption.

    This is the version-aware-keywords capability: when an input uses a keyword
    that requires a newer ABINIT version than the intent/runtime declares, we
    surface an explicit version mismatch so the parent probe can fail early
    rather than discovering the incompatibility at runtime.
    """
    out: list[dict[str, Any]] = []
    declared_version = version_assumption.get("software_version", "unknown")
    exact_known = version_assumption.get("exact_runtime_known", False)
    for keyword, required in _VERSIONED_KEYWORDS.items():
        if not abinit_file.has_keyword(keyword):
            continue
        # Only emit when the runtime version is declared AND older than the
        # keyword requirement. When the version is unknown we leave the
        # generic CODE_VERSION_ASSUMPTION information diagnostic to carry that
        # fact, so we never guess at an incompatibility we cannot evidence.
        if not exact_known:
            continue
        if not _version_lt(declared_version, required):
            continue
        line = _keyword_line(abinit_file, keyword)
        out.append(
            _diag(
                code=CODE_UNKNOWN_KEYWORD_VERSION,
                severity="error",
                message=(
                    f"keyword {keyword} requires {required} but the declared "
                    f"runtime version is {declared_version}"
                ),
                path=input_path,
                line=line,
                category="schema",
                confidence=0.9,
                blocking=True,
                source_provenance={
                    "role": ROLE_PRIMARY_INPUT,
                    "keyword": keyword,
                    "schema_source": version_assumption.get("schema_source"),
                },
                fix_hints=[
                    f"Raise the declared runtime version to at least {required}",
                    f"Or remove {keyword} from the input",
                ],
                actions=[
                    {
                        "kind": "remove_keyword",
                        "keyword": keyword,
                        "target": str(input_path),
                        "safe_to_auto_apply": False,
                    }
                ],
                facts={
                    "keyword": keyword,
                    "required_version": required,
                    "declared_version": declared_version,
                },
                artifact_roles=[ROLE_PRIMARY_INPUT],
                domain_tags=["schema", "version-aware", "blocking"],
                version_assumption=version_assumption,
                manual_ref=version_assumption.get("schema_source"),
            )
        )
    return out


def _version_lt(declared: str, required: str) -> bool:
    """Best-effort ``declared < required`` comparison for version strings.

    Both inputs are of the form ``abinit >=X.Y``. We extract the leading
    numeric tuple from each and compare element-wise. Returns False if either
    side cannot be parsed, so we never fabricate a version mismatch.
    """

    def _tuple(text: str) -> tuple[int, ...]:
        match = re.search(r"(\d+(?:\.\d+)*)", text)
        if not match:
            return ()
        return tuple(int(part) for part in match.group(1).split("."))

    d = _tuple(declared)
    r = _tuple(required)
    if not d or not r:
        return False
    # Pad to equal length so (9,) compares correctly against (9, 6).
    length = max(len(d), len(r))
    d_padded = d + (0,) * (length - len(d))
    r_padded = r + (0,) * (length - len(r))
    return d_padded < r_padded


def _version_assumption_diagnostic(
    version_assumption: dict[str, Any],
    intent: dict[str, Any] | None,
    input_path: Path,
) -> list[dict[str, Any]]:
    """Emit an explicit information diagnostic when the runtime version is unknown.

    This makes the version assumption machine-readable in the diagnostic stream
    itself (not just metadata) so the parent probe can surface it without
    parsing the envelope top-level.
    """
    if version_assumption["exact_runtime_known"]:
        return []
    return [
        _diag(
            code=CODE_VERSION_ASSUMPTION,
            severity="information",
            message=(
                "Exact ABINIT runtime/image version is unknown; preflight "
                "validated against the builtin schema keyword set"
            ),
            path=input_path,
            line=1,
            category="preflight/runtime-risk",
            confidence=1.0,
            blocking=False,
            source_provenance={
                "role": ROLE_PRIMARY_INPUT,
                "reason": "software_version and runtime_image not declared in intent",
            },
            fix_hints=[
                "Declare software_version/runtime_image in the intent contract",
            ],
            actions=[],
            facts={
                "software_version": version_assumption["software_version"],
                "runtime_image": version_assumption["runtime_image"],
                "schema_source": version_assumption["schema_source"],
            },
            artifact_roles=[ROLE_PRIMARY_INPUT],
            domain_tags=["version-aware", "assumption"],
            version_assumption=version_assumption,
            intent=dict(intent) if intent else None,
        )
    ]


# --- fleet-regression-fixtures --------------------------------------------


def fleet_manifest(
    *,
    fixtures: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a machine-readable preflight manifest for the parent fleet.

    The parent ``bohrium_skills`` probe/report workflow consumes this to know
    which preflight codes exist, which capabilities are implemented, and which
    fixtures exercise them. Keeping it as data (not README prose) means the
    fleet regression evidence stays in sync with the implementation.
    """
    codes = {
        CODE_MISSING_INPUT: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "primary-input artifact missing from workspace",
        },
        CODE_MISSING_STRUCTURE: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "structure section variables missing from input",
        },
        CODE_MISSING_LATTICE: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "lattice section variables missing from input",
        },
        CODE_NTYPAT_ZNUCL_MISMATCH: {
            "severity": "error",
            "category": "semantic consistency",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "ntypat/znucl/pseudos species counts do not agree",
        },
        CODE_MISSING_PSEUDOS: {
            "severity": "error",
            "category": "cross-file reference",
            "blocking": True,
            "capability": "cross-artifact-graph",
            "summary": "structure declared but pseudos keyword absent",
        },
        CODE_UNRESOLVED_PSEUDO: {
            "severity": "warning",
            "category": "cross-file reference",
            "blocking": False,
            "capability": "cross-artifact-graph",
            "summary": "pseudopotential file cannot be resolved",
        },
        CODE_LOW_ECUT: {
            "severity": "warning",
            "category": "preflight/runtime-risk",
            "blocking": False,
            "capability": "version-aware-keywords",
            "summary": "ecut below conservative workflow threshold",
        },
        CODE_SUSPICIOUS_KPOINTS: {
            "severity": "warning",
            "category": "preflight/runtime-risk",
            "blocking": False,
            "capability": "cross-artifact-graph",
            "summary": "k-point grid has a 1-point axis or is undeclared",
        },
        CODE_VERSION_ASSUMPTION: {
            "severity": "information",
            "category": "preflight/runtime-risk",
            "blocking": False,
            "capability": "version-aware-keywords",
            "summary": "exact runtime version unknown; fallback schema used",
        },
        CODE_UNKNOWN_KEYWORD_VERSION: {
            "severity": "error",
            "category": "schema",
            "blocking": True,
            "capability": "version-aware-keywords",
            "summary": "keyword requires a newer runtime than declared",
        },
    }
    capabilities = {
        "version-aware-keywords": {
            "status": "available",
            "evidence_codes": [
                CODE_UNKNOWN_KEYWORD_VERSION,
                CODE_VERSION_ASSUMPTION,
                CODE_LOW_ECUT,
            ],
        },
        "cross-artifact-graph": {
            "status": "available",
            "roles": list(ALL_ROLES),
            "evidence_codes": [
                CODE_MISSING_INPUT,
                CODE_MISSING_STRUCTURE,
                CODE_MISSING_LATTICE,
                CODE_NTYPAT_ZNUCL_MISMATCH,
                CODE_MISSING_PSEUDOS,
                CODE_UNRESOLVED_PSEUDO,
                CODE_SUSPICIOUS_KPOINTS,
            ],
        },
        "code-actions": {
            "status": "available",
            "blocking_gate": "abinit-lsp-tool check --fail-on-blocking",
            "evidence_codes": list(codes.keys()),
        },
        "fleet-regression-fixtures": {
            "status": "available",
            "fixtures": list(fixtures) if fixtures else [],
        },
    }
    return {
        "software": "abinit",
        "preflight_envelope": "DiagnosticEnvelope/v1",
        "artifact_roles": list(ALL_ROLES),
        "capabilities": capabilities,
        "codes": codes,
    }
