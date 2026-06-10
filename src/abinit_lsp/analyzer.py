from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from .diagnostics import Diagnostic

DOMAIN_NAME = "ABINIT"
DOMAIN_ID = "abinit"
DOMAIN_KIND = "text"
CODE_PREFIX = "ABINIT"
FILE_PATTERNS: list[str] = ["*.abi", "*.abinit", "*.in"]
FILE_NAMES: list[str] = []
FILE_SUFFIXES: list[str] = [".abi", ".abinit", ".in"]
KNOWN_TOKENS: list[str] = [
    "acell",
    "amu",
    "diemac",
    "ecut",
    "ixc",
    "kptopt",
    "natom",
    "nband",
    "ngkpt",
    "nstep",
    "ntypat",
    "occopt",
    "optcell",
    "pseudos",
    "rprim",
    "toldfe",
    "tolmxf",
    "typat",
    "xred",
    "xcart",
    "znucl",
]
REQUIRED_TOKENS: list[str] = ["ecut"]
REQUIRED_IMPORTS: list[str] = []
REQUIRED_SYMBOLS: list[str] = []
REQUIRED_JSON_KEYS: list[str] = []

COMMENT_PREFIXES = ("#", "!", ";")


def analyze_path(path: Path) -> list[Diagnostic]:
    path = path.resolve()
    files = _collect_files(path)
    diagnostics: list[Diagnostic] = []
    if not files:
        diagnostics.append(
            Diagnostic(
                code=f"{CODE_PREFIX}201",
                severity="error",
                message=f"no supported {DOMAIN_NAME} files found",
                file=str(path),
                line=1,
            )
        )
        return diagnostics
    for file_path in files:
        diagnostics.extend(analyze_file(file_path))
    return sorted(diagnostics, key=lambda item: (item.file, item.line, item.code))


def _collect_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if _is_supported(path) else []
    result: list[Path] = []
    for pattern in FILE_PATTERNS:
        result.extend(path.rglob(pattern))
    return sorted({item for item in result if item.is_file()})


def _is_supported(path: Path) -> bool:
    name = path.name.lower()
    suffix = path.suffix.lower()
    return (
        name in FILE_NAMES
        or suffix in FILE_SUFFIXES
        or any(path.match(pattern) for pattern in FILE_PATTERNS)
    )


def analyze_file(path: Path) -> list[Diagnostic]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [
            Diagnostic(f"{CODE_PREFIX}202", "error", "file is not valid UTF-8 text", str(path), 1)
        ]
    if DOMAIN_KIND == "python":
        return _analyze_python(path, content)
    if DOMAIN_KIND == "json":
        return _analyze_json_or_text(path, content)
    return _analyze_text(path, content)


def _analyze_text(path: Path, content: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    meaningful = _meaningful_lines(content)
    present = {line.split()[0].lower() for _, line in meaningful if line.split()}
    for required in REQUIRED_TOKENS:
        if required.lower() not in present and required.lower() not in content.lower():
            diagnostics.append(
                Diagnostic(
                    f"{CODE_PREFIX}101",
                    "warning",
                    f"expected {DOMAIN_NAME} token or setting '{required}' was not found",
                    str(path),
                    1,
                    evidence=["MVP rule derived from MatMaster execution contracts"],
                    suggested_fix={"kind": "add_required_token", "token": required},
                    confidence=0.72,
                )
            )
    for line_no, line in meaningful:
        token = line.split()[0].lower()
        if KNOWN_TOKENS and token not in KNOWN_TOKENS and not token.startswith(("#", "&", "%")):
            diagnostics.append(
                Diagnostic(
                    f"{CODE_PREFIX}001",
                    "warning",
                    f"unknown or currently unsupported {DOMAIN_NAME} keyword: {token}",
                    str(path),
                    line_no,
                    suggested_fix={"kind": "check_keyword_spelling", "keyword": token},
                    confidence=0.55,
                )
            )
    diagnostics.extend(_domain_text_checks(path, content, meaningful))
    return diagnostics


def _domain_text_checks(
    path: Path, content: str, meaningful: list[tuple[int, str]]
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    lower_name = path.name.lower()
    if DOMAIN_ID == "gpumd" and lower_name == "run.in":
        first = meaningful[0][1].split()[0].lower() if meaningful else ""
        if first != "potential":
            diagnostics.append(
                Diagnostic(
                    "GPUMD010",
                    "error",
                    "GPUMD run.in should start with the potential command",
                    str(path),
                    meaningful[0][0] if meaningful else 1,
                    evidence=["MatMaster GPUMD guard: potential must be first non-comment command"],
                    suggested_fix={
                        "kind": "move_command",
                        "command": "potential",
                        "position": "first",
                    },
                    confidence=0.9,
                )
            )
        run_lines = [line_no for line_no, line in meaningful if line.lower().startswith("run ")]
        compute_lines = [
            line_no
            for line_no, line in meaningful
            if line.lower().startswith(("compute_", "dump_"))
        ]
        if compute_lines and run_lines and min(compute_lines) > min(run_lines):
            diagnostics.append(
                Diagnostic(
                    "GPUMD011",
                    "warning",
                    "declare compute/dump commands before their run block",
                    str(path),
                    min(compute_lines),
                    confidence=0.8,
                )
            )
    if DOMAIN_ID == "abinit":
        has_structure = any(
            token in content.lower() for token in ("natom", "xred", "xcart", "znucl", "typat")
        )
        if not has_structure:
            diagnostics.append(
                Diagnostic(
                    "ABINIT010",
                    "warning",
                    "ABINIT input does not expose enough structure variables for static review",
                    str(path),
                    1,
                    suggested_fix={
                        "kind": "add_structure_block",
                        "tokens": ["natom", "znucl", "typat", "xred"],
                    },
                    confidence=0.7,
                )
            )
    return diagnostics


def _analyze_python(path: Path, content: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return [
            Diagnostic(
                f"{CODE_PREFIX}001", "error", exc.msg, str(path), exc.lineno or 1, exc.offset or 1
            )
        ]
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    imports = _import_names(tree)
    for required in REQUIRED_IMPORTS:
        if required not in imports and required not in names:
            diagnostics.append(
                Diagnostic(
                    f"{CODE_PREFIX}101",
                    "warning",
                    f"expected import or symbol '{required}' was not found",
                    str(path),
                    1,
                    suggested_fix={"kind": "add_import", "module": required},
                    confidence=0.75,
                )
            )
    for symbol in REQUIRED_SYMBOLS:
        if symbol not in names and symbol not in attrs and symbol not in content:
            diagnostics.append(
                Diagnostic(
                    f"{CODE_PREFIX}102",
                    "warning",
                    f"expected workflow symbol '{symbol}' was not found",
                    str(path),
                    1,
                    confidence=0.68,
                )
            )
    if (
        DOMAIN_ID == "pyscf"
        and "kernel" in attrs
        and "converged" not in attrs
        and "converged" not in content
    ):
        diagnostics.append(
            Diagnostic(
                "PYSCF010",
                "warning",
                "PySCF scripts should check mf.converged after kernel/run calls",
                str(path),
                1,
                suggested_fix={"kind": "check_convergence", "symbol": "mf.converged"},
                confidence=0.8,
            )
        )
    if DOMAIN_ID == "pyatb" and "HR.dat" not in content and "hr_file" not in content:
        diagnostics.append(
            Diagnostic(
                "PYATB010",
                "warning",
                "PyATB workflow should reference HR.dat or hr_file",
                str(path),
                1,
                confidence=0.75,
            )
        )
    return diagnostics


def _analyze_json_or_text(path: Path, content: str) -> list[Diagnostic]:
    if path.suffix.lower() != ".json":
        return (
            _analyze_python(path, content)
            if path.suffix.lower() == ".py"
            else _analyze_text(path, content)
        )
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        return [Diagnostic(f"{CODE_PREFIX}001", "error", exc.msg, str(path), exc.lineno, exc.colno)]
    diagnostics: list[Diagnostic] = []
    if isinstance(payload, dict):
        for key in REQUIRED_JSON_KEYS:
            if key not in payload:
                diagnostics.append(
                    Diagnostic(
                        f"{CODE_PREFIX}101",
                        "warning",
                        f"manifest is missing required key '{key}'",
                        str(path),
                        1,
                        suggested_fix={"kind": "add_json_key", "key": key},
                        confidence=0.78,
                    )
                )
    return diagnostics


def _import_names(tree: ast.AST) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[0])
    return result


def _meaningful_lines(content: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    for line_no, raw in enumerate(content.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith(COMMENT_PREFIXES):
            continue
        result.append((line_no, stripped))
    return result


def format_text(content: str) -> str:
    lines: list[str] = []
    for raw in content.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith(COMMENT_PREFIXES):
            lines.append(raw.rstrip())
            continue
        if "=" in stripped:
            key, value = stripped.split("=", 1)
            lines.append(f"{key.strip():<24} = {value.strip()}")
        else:
            parts = stripped.split(maxsplit=1)
            if len(parts) == 2 and re.match(r"^[A-Za-z_][A-Za-z0-9_\-.]*$", parts[0]):
                lines.append(f"{parts[0]:<24} {parts[1].strip()}")
            else:
                lines.append(stripped)
    return "\n".join(lines).rstrip() + "\n"
