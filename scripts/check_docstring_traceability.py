#!/usr/bin/env python3
"""Check code docstrings, LLM Wiki pages, and raw evidence traceability.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "openqc.lsp.traceability.v1"
RULE_ID_PATTERN = re.compile(r"^[A-Z0-9]+-[A-Z0-9_]+-[A-Z0-9_]+-\d{3}$")
OFFICIAL_URL_RE = re.compile(r"https://docs\.abinit\.org/[A-Za-z0-9_./%-]+")

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "docs",
    "node_modules",
    "out",
    "raw",
    "target",
    "tests",
    "venv",
    "wiki",
}

WIKI_RE = re.compile(r"(?<![A-Za-z0-9_./-])(wiki/[A-Za-z0-9_./%+@:#=-]+?\.md)(?:#[A-Za-z0-9_.-]+)?")
RAW_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])(raw/[A-Za-z0-9_./%+@:#=-]+\.[A-Za-z0-9][A-Za-z0-9_-]*)"
)

RULE_ROLE_CATEGORY: dict[str, tuple[str, str, str]] = {
    "ABINIT101": ("LINT", "INPUT", "src/abinit_lsp/lint.py"),
    "ABINIT102": ("LINT", "STRUCTURE", "src/abinit_lsp/lint.py"),
    "ABINIT103": ("LINT", "STRUCTURE", "src/abinit_lsp/lint.py"),
    "ABINIT104": ("LINT", "VARIABLE", "src/abinit_lsp/lint.py"),
    "ABINIT105": ("LINT", "MULTIDATASET", "src/abinit_lsp/lint.py"),
    "ABINIT106": ("LINT", "SCF", "src/abinit_lsp/lint.py"),
    "ABINIT107": ("LINT", "INPUT", "src/abinit_lsp/lint.py"),
    "ABINIT108": ("LINT", "INPUT", "src/abinit_lsp/lint.py"),
    "ABINIT109": ("LINT", "STRUCTURE", "src/abinit_lsp/lint.py"),
    "ABINIT110": ("LINT", "STRUCTURE", "src/abinit_lsp/lint.py"),
    "ABINIT111": ("LINT", "VARIABLE", "src/abinit_lsp/lint.py"),
    "ABINIT112": ("LINT", "MULTIDATASET", "src/abinit_lsp/lint.py"),
    "ABINIT200": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT201": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT202": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT203": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT204": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT205": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT206": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT207": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT208": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
    "ABINIT209": ("LOG", "RUNTIME", "src/abinit_lsp/log_parser.py"),
}


@dataclass
class DocstringRecord:
    file: str
    line: int
    kind: str
    symbol: str
    linked: bool
    wiki_refs: list[str]
    broken_wiki_refs: list[str]


@dataclass
class WikiRecord:
    file: str
    raw_refs: list[str]
    missing_raw_refs: list[str]
    refs_missing_from_manifest: list[str]


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def load_lsp_metadata(root: Path) -> tuple[str, str, str]:
    server_id = "abinit-lsp"
    language_id = "abinit"
    repository = "newtontech/abinit-lsp"
    capabilities = root / "lsp-capabilities.json"
    if capabilities.is_file():
        try:
            data = json.loads(capabilities.read_text(encoding="utf-8"))
            if isinstance(data.get("id"), str) and data["id"]:
                server_id = data["id"]
            if isinstance(data.get("languageId"), str) and data["languageId"]:
                language_id = data["languageId"]
        except json.JSONDecodeError:
            pass
    manifest = root / "raw" / "assets" / "manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if isinstance(data.get("repository"), str) and data["repository"]:
                repository = data["repository"]
        except json.JSONDecodeError:
            pass
    return server_id, language_id, repository


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def extract_wiki_refs(text: str) -> list[str]:
    return sorted(set(match.group(1).rstrip(".,);]") for match in WIKI_RE.finditer(text)))


def extract_raw_refs(text: str) -> list[str]:
    refs = []
    for match in RAW_RE.finditer(text):
        ref = match.group(1).rstrip(".,);]")
        if ref.endswith("`"):
            ref = ref[:-1]
        refs.append(ref)
    return sorted(set(refs))


def extract_official_urls(text: str) -> list[str]:
    return sorted(set(OFFICIAL_URL_RE.findall(text)))


def resolve_existing_wiki_refs(root: Path, refs: Iterable[str]) -> list[str]:
    broken = []
    for ref in refs:
        if not (root / ref).is_file():
            broken.append(ref)
    return broken


def iter_python_docstrings(path: Path) -> Iterable[tuple[int, int, int, int, str, str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return

    nodes: list[tuple[ast.AST, str]] = [(tree, "<module>")]
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef, ast.FunctionDef)):
            nodes.append((node, node.name))

    for node, symbol in nodes:
        if not getattr(node, "body", None):
            continue
        first = node.body[0]  # type: ignore[index]
        value = getattr(first, "value", None)
        if not (
            isinstance(first, ast.Expr)
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and hasattr(first, "end_lineno")
            and hasattr(first, "end_col_offset")
        ):
            continue
        yield (
            first.lineno,
            first.col_offset,
            first.end_lineno,
            first.end_col_offset,
            value.value,
            symbol,
        )


def scan_docstrings(root: Path) -> list[DocstringRecord]:
    records: list[DocstringRecord] = []

    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        for line, _col, _end_line, _end_col, docstring, symbol in iter_python_docstrings(path):
            refs = extract_wiki_refs(docstring)
            records.append(
                DocstringRecord(
                    file=relpath(path, root),
                    line=line,
                    kind="python-docstring",
                    symbol=symbol,
                    linked=bool(refs),
                    wiki_refs=refs,
                    broken_wiki_refs=resolve_existing_wiki_refs(root, refs),
                )
            )

    for path in sorted(
        [*root.rglob("*.js"), *root.rglob("*.jsx"), *root.rglob("*.ts"), *root.rglob("*.tsx")]
    ):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in re.finditer(r"/\*\*([\s\S]*?)\*/", text):
            line = text.count("\n", 0, match.start()) + 1
            block = match.group(0)
            refs = extract_wiki_refs(block)
            records.append(
                DocstringRecord(
                    file=relpath(path, root),
                    line=line,
                    kind="jsdoc",
                    symbol="<jsdoc>",
                    linked=bool(refs),
                    wiki_refs=refs,
                    broken_wiki_refs=resolve_existing_wiki_refs(root, refs),
                )
            )

    for path in sorted(root.rglob("*.rs")):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        block: list[tuple[int, str]] = []
        for number, line in [*enumerate(lines, start=1), (len(lines) + 1, "")]:
            if line.lstrip().startswith(("///", "//!")):
                block.append((number, line))
                continue
            if not block:
                continue
            text = "\n".join(item for _line_number, item in block)
            refs = extract_wiki_refs(text)
            records.append(
                DocstringRecord(
                    file=relpath(path, root),
                    line=block[0][0],
                    kind="rustdoc",
                    symbol="<rustdoc>",
                    linked=bool(refs),
                    wiki_refs=refs,
                    broken_wiki_refs=resolve_existing_wiki_refs(root, refs),
                )
            )
            block = []

    return records


def collect_manifest_paths(value: Any) -> set[str]:
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and key in {
                "asset",
                "file",
                "filename",
                "path",
                "raw_path",
            }:
                paths.add(child)
                if not child.startswith("raw/"):
                    paths.add(f"raw/assets/{child}")
            else:
                paths.update(collect_manifest_paths(child))
    elif isinstance(value, list):
        for child in value:
            paths.update(collect_manifest_paths(child))
    elif isinstance(value, str) and value.startswith("raw/"):
        paths.add(value)
    return paths


def load_manifest(root: Path) -> tuple[set[str], list[str], dict[str, Any]]:
    manifest = root / "raw" / "assets" / "manifest.json"
    if not manifest.is_file():
        return set(), ["raw/assets/manifest.json is missing"], {}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return set(), [f"raw/assets/manifest.json is invalid JSON: {exc}"], {}
    paths = collect_manifest_paths(data)
    if not paths:
        return set(), ["raw/assets/manifest.json contains no raw asset paths"], data
    return paths, [], data


def scan_wiki(root: Path, manifest_paths: set[str]) -> list[WikiRecord]:
    records: list[WikiRecord] = []
    wiki_root = root / "wiki"
    if not wiki_root.is_dir():
        return records

    for path in sorted(wiki_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        refs = extract_raw_refs(text)
        missing_refs = [ref for ref in refs if not (root / ref).is_file()]
        not_manifested = [
            ref
            for ref in refs
            if manifest_paths and ref not in manifest_paths and ref[11:] not in manifest_paths
        ]
        records.append(
            WikiRecord(
                file=relpath(path, root),
                raw_refs=refs,
                missing_raw_refs=missing_refs,
                refs_missing_from_manifest=not_manifested,
            )
        )
    return records


def choose_default_wiki(root: Path) -> str:
    candidates = [
        "wiki/synthesis/openqc-agent-context.md",
        "wiki/concepts/diagnostic-engine-v1.md",
    ]
    for candidate in candidates:
        if (root / candidate).is_file():
            return candidate
    wiki_pages = sorted((root / "wiki").rglob("*.md")) if (root / "wiki").is_dir() else []
    if not wiki_pages:
        raise SystemExit("No wiki page found; cannot choose a default docstring source")
    return relpath(wiki_pages[0], root)


def choose_default_raw(root: Path) -> str:
    candidates = [
        "raw/assets/upstream-sources.md",
        "raw/assets/README.md",
        "raw/assets/DIAGNOSTIC_ENGINE_V1.md",
    ]
    for candidate in candidates:
        if (root / candidate).is_file():
            return candidate
    raw_assets = sorted(
        path
        for path in (root / "raw" / "assets").rglob("*")
        if path.is_file() and path.name != "manifest.json"
    )
    if not raw_assets:
        raise SystemExit("No raw asset found; cannot choose a default wiki source")
    return relpath(raw_assets[0], root)


def line_offsets(text: str) -> list[int]:
    offsets = [0]
    for match in re.finditer("\n", text):
        offsets.append(match.end())
    return offsets


def add_link_to_python_literal(segment: str, wiki_ref: str, fallback_indent: str = "") -> str:
    source_leading = segment[: len(segment) - len(segment.lstrip())]
    doc_indent = source_leading or fallback_indent
    body = segment[len(source_leading) :]
    delimiter = ""
    for candidate in ('"""', "'''"):
        if candidate in body[:8]:
            delimiter = candidate
            break
    if delimiter:
        close = body.rfind(delimiter)
        if close <= 0:
            return segment
        insertion = f"\n\n{doc_indent}LLM Wiki: {wiki_ref}\n{doc_indent}"
        return source_leading + body[:close].rstrip() + insertion + body[close:]

    try:
        value = ast.literal_eval(body)
    except (SyntaxError, ValueError):
        return segment
    return (
        f'{source_leading}"""{value.rstrip()}\n\n'
        f'{doc_indent}LLM Wiki: {wiki_ref}\n{doc_indent}"""'
    )


def fix_python_docstrings(root: Path, wiki_ref: str) -> int:
    changed = 0
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        offsets = line_offsets(text)
        replacements: list[tuple[int, int, str]] = []
        for line, col, end_line, end_col, docstring, _symbol in iter_python_docstrings(path):
            if extract_wiki_refs(docstring):
                continue
            start = offsets[line - 1] + col
            end = offsets[end_line - 1] + end_col
            fallback_indent = text[offsets[line - 1] : offsets[line - 1] + col]
            replacements.append(
                (start, end, add_link_to_python_literal(text[start:end], wiki_ref, fallback_indent))
            )
        if not replacements:
            continue
        for start, end, replacement in sorted(replacements, reverse=True):
            text = text[:start] + replacement + text[end:]
        path.write_text(text, encoding="utf-8")
        changed += len(replacements)
    return changed


def fix_jsdoc_blocks(root: Path, wiki_ref: str) -> int:
    changed = 0
    for path in sorted(
        [*root.rglob("*.js"), *root.rglob("*.jsx"), *root.rglob("*.ts"), *root.rglob("*.tsx")]
    ):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")

        def replace(match: re.Match[str], source_text: str = text) -> str:
            nonlocal changed
            block = match.group(0)
            if extract_wiki_refs(block):
                return block
            line_start = source_text.rfind("\n", 0, match.start()) + 1
            indent = re.match(r"[ \t]*", source_text[line_start : match.start()])
            prefix = indent.group(0) if indent else ""
            changed += 1
            return (
                block[:-2].rstrip()
                + f"\n{prefix} *\n{prefix} * LLM Wiki: {wiki_ref}\n{prefix} */"
            )

        updated = re.sub(r"/\*\*([\s\S]*?)\*/", replace, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    return changed


def fix_rust_doc_comments(root: Path, wiki_ref: str) -> int:
    changed = 0
    for path in sorted(root.rglob("*.rs")):
        relative = path.relative_to(root)
        if should_skip(relative):
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
        output: list[str] = []
        block: list[str] = []
        file_changed = 0
        for line in [*lines, ""]:
            stripped = line.lstrip()
            if stripped.startswith(("///", "//!")):
                block.append(line)
                continue
            if block:
                if not any(extract_wiki_refs(item) for item in block):
                    marker = "//!" if block[-1].lstrip().startswith("//!") else "///"
                    indent = re.match(r"[ \t]*", block[-1]).group(0)  # type: ignore[union-attr]
                    newline = "\n" if block[-1].endswith("\n") else ""
                    block.append(f"{indent}{marker} LLM Wiki: {wiki_ref}{newline}")
                    file_changed += 1
                output.extend(block)
                block = []
            if line:
                output.append(line)
        if file_changed:
            path.write_text("".join(output), encoding="utf-8")
            changed += file_changed
    return changed


def fix_wiki_raw_links(root: Path, raw_ref: str) -> int:
    changed = 0
    wiki_root = root / "wiki"
    if not wiki_root.is_dir():
        return changed
    for path in sorted(wiki_root.rglob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if extract_raw_refs(text):
            continue
        suffix = "\n" if text.endswith("\n") else "\n\n"
        text = (
            text
            + suffix
            + "## Traceability Sources\n\n"
            + f"- Raw evidence: `{raw_ref}`\n"
        )
        path.write_text(text, encoding="utf-8")
        changed += 1
    return changed


def write_manifest(root: Path) -> None:
    assets_root = root / "raw" / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)
    entries = []
    for path in sorted(assets_root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(assets_root).as_posix(),
                "raw_path": relpath(path, root),
                "bytes": len(data),
                "checksum_sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    server_id, _, repository = load_lsp_metadata(root)
    manifest = {
        "manifest_version": "1.0.0",
        "schema_version": "provenance-manifest-v1",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository": repository,
        "pipeline": "official-docs -> raw/assets -> wiki -> docstrings -> LSP runtime",
        "entries": entries,
    }
    (assets_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def traceability_rule_code(legacy_code: str) -> str:
    if legacy_code in RULE_ROLE_CATEGORY:
        role, category, _ = RULE_ROLE_CATEGORY[legacy_code]
        suffix = legacy_code.replace("ABINIT", "")
        return f"ABINIT-{role}-{category}-{suffix}"
    digits = re.sub(r"\D", "", legacy_code) or "001"
    return f"ABINIT-SRC-RULE-{digits.zfill(3)}"


def build_rule_ids(root: Path) -> list[dict[str, str]]:
    rule_ids: list[dict[str, str]] = []
    for legacy_code, (role, category, source_path) in sorted(RULE_ROLE_CATEGORY.items()):
        rule_ids.append(
            {
                "code": traceability_rule_code(legacy_code),
                "sourcePath": source_path,
            }
        )
    return rule_ids


def build_wiki_sources(root: Path, wiki_records: list[WikiRecord]) -> list[dict[str, str]]:
    wiki_sources: list[dict[str, str]] = []
    for record in wiki_records:
        if not record.raw_refs or record.missing_raw_refs:
            continue
        text = (root / record.file).read_text(encoding="utf-8", errors="ignore")
        urls = extract_official_urls(text)
        source_url = urls[0] if urls else "https://docs.abinit.org/"
        wiki_sources.append(
            {
                "wikiPath": record.file,
                "sourceUrl": source_url,
                "rawPath": record.raw_refs[0],
            }
        )
    return wiki_sources


def build_source_urls(manifest_data: dict[str, Any]) -> list[dict[str, str]]:
    source_urls: list[dict[str, str]] = []
    default_raw = "raw/assets/upstream-sources.md"
    for anchor in manifest_data.get("official_source_anchors", []):
        if not isinstance(anchor, dict):
            continue
        url = anchor.get("url")
        if not isinstance(url, str) or not url:
            continue
        entry: dict[str, str] = {
            "url": url,
            "rawPath": default_raw,
        }
        kind = anchor.get("type")
        if isinstance(kind, str) and kind:
            entry["kind"] = kind
        source_urls.append(entry)
    if not source_urls:
        source_urls.append(
            {
                "url": "https://docs.abinit.org/variables/",
                "kind": "official_docs",
                "rawPath": default_raw,
            }
        )
    return source_urls


def build_report(root: Path) -> dict[str, Any]:
    manifest_paths, manifest_errors, manifest_data = load_manifest(root)
    docstring_records = scan_docstrings(root)
    wiki_records = scan_wiki(root, manifest_paths)
    broken_wiki = sum(len(item.broken_wiki_refs) for item in docstring_records)
    wiki_source_failures = sum(
        1
        for item in wiki_records
        if not item.raw_refs or item.missing_raw_refs or item.refs_missing_from_manifest
    )
    summary = {
        "docstringsTotal": len(docstring_records),
        "docstringsLinked": sum(1 for item in docstring_records if item.linked),
        "brokenWikiLinks": broken_wiki,
        "wikiSourcesWithoutRaw": wiki_source_failures,
        "rawManifestFailures": len(manifest_errors),
    }
    server_id, language_id, repository = load_lsp_metadata(root)
    docstrings = [
        {
            "path": item.file,
            "symbol": item.symbol,
            "wikiPath": item.wiki_refs[0],
        }
        for item in docstring_records
        if item.linked and not item.broken_wiki_refs
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "serverId": server_id,
        "repository": repository,
        "languageId": language_id,
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", ".000Z"
        ),
        "summary": summary,
        "docstrings": docstrings,
        "wikiSources": build_wiki_sources(root, wiki_records),
        "ruleIds": build_rule_ids(root),
        "sourceUrls": build_source_urls(manifest_data),
        "rawManifest": {
            "path": "raw/assets/manifest.json",
            "ok": len(manifest_errors) == 0,
        },
        "manifestErrors": manifest_errors,
        "docstringViolations": [
            asdict(item)
            for item in docstring_records
            if not item.linked or item.broken_wiki_refs
        ],
        "wikiViolations": [
            asdict(item)
            for item in wiki_records
            if not item.raw_refs or item.missing_raw_refs or item.refs_missing_from_manifest
        ],
    }


def report_has_failures(report: dict[str, Any]) -> bool:
    summary = report["summary"]
    return any(
        [
            summary["docstringsTotal"] != summary["docstringsLinked"],
            summary["brokenWikiLinks"],
            summary["wikiSourcesWithoutRaw"],
            summary["rawManifestFailures"],
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/docstring-wiki-raw-traceability.json"),
    )
    parser.add_argument("--write-report", action="store_true", help="Write the JSON report")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when traceability is incomplete",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Add missing docstring and wiki source links",
    )
    parser.add_argument(
        "--refresh-manifest",
        action="store_true",
        help="Regenerate raw/assets/manifest.json",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if args.fix:
        wiki_ref = choose_default_wiki(root)
        raw_ref = choose_default_raw(root)
        changed = {
            "python_docstrings": fix_python_docstrings(root, wiki_ref),
            "jsdoc_blocks": fix_jsdoc_blocks(root, wiki_ref),
            "rustdoc_blocks": fix_rust_doc_comments(root, wiki_ref),
            "wiki_pages": fix_wiki_raw_links(root, raw_ref),
        }
        print(json.dumps({"fixed": changed, "wiki_ref": wiki_ref, "raw_ref": raw_ref}, indent=2))

    manifest_path = root / "raw" / "assets" / "manifest.json"
    if args.refresh_manifest or (args.fix and not manifest_path.is_file()):
        write_manifest(root)

    report = build_report(root)
    if args.write_report:
        report_path = args.report if args.report.is_absolute() else root / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    if args.strict and report_has_failures(report):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
