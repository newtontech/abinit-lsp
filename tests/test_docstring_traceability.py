from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RULE_ID_PATTERN = re.compile(r"^[A-Z0-9]+-[A-Z0-9_]+-[A-Z0-9_]+-\d{3}$")
SCHEMA_VERSION = "openqc.lsp.traceability.v1"


def is_repo_relative(path: str) -> bool:
    return (
        not path.startswith("/")
        and not re.match(r"^[A-Za-z]:[\\/]", path)
        and not path.startswith("file:")
        and ".." not in path.split("/")
    )


def write_traceable_fixture(root: Path, *, linked_docstring: bool = True) -> None:
    root.mkdir(parents=True)
    (root / "src").mkdir()
    (root / "wiki" / "rules").mkdir(parents=True)
    (root / "raw" / "assets").mkdir(parents=True)

    (root / "lsp-capabilities.json").write_text(
        json.dumps({"id": "abinit-lsp", "languageId": "abinit"}),
        encoding="utf-8",
    )
    (root / "raw" / "assets" / "manifest.json").write_text(
        json.dumps(
            {
                "repository": "newtontech/abinit-lsp-fixture",
                "official_source_anchors": [
                    {
                        "type": "official_docs",
                        "url": "https://docs.abinit.org/variables/",
                    }
                ],
                "entries": [
                    {
                        "path": "source.md",
                        "checksum_sha256": "test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (root / "raw" / "assets" / "source.md").write_text("# Source\n", encoding="utf-8")
    (root / "wiki" / "rules" / "ecut.md").write_text(
        "# Ecut\n\nhttps://docs.abinit.org/variables/ecut/\n\n"
        "Raw evidence: `raw/assets/source.md`\n",
        encoding="utf-8",
    )

    wiki_line = "\n\nLLM Wiki: wiki/rules/ecut.md" if linked_docstring else ""
    (root / "src" / "example.py").write_text(
        f'"""Fixture docstring.{wiki_line}"""\n\nVALUE = 1\n',
        encoding="utf-8",
    )


def run_checker(script: Path, root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(root),
            "--report",
            str(root / "reports" / "docstring-wiki-raw-traceability.json"),
            "--write-report",
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def validate_report_shape(report: dict) -> None:
    assert report["schemaVersion"] == SCHEMA_VERSION
    assert report["serverId"] == "abinit-lsp"
    assert report["languageId"] == "abinit"
    assert is_repo_relative(report["repository"])
    summary = report["summary"]
    assert summary["docstringsTotal"] == summary["docstringsLinked"]
    assert summary["brokenWikiLinks"] == 0
    assert summary["wikiSourcesWithoutRaw"] == 0
    assert summary["rawManifestFailures"] == 0

    for entry in report["docstrings"]:
        assert is_repo_relative(entry["path"])
        assert is_repo_relative(entry["wikiPath"])

    for entry in report["wikiSources"]:
        assert is_repo_relative(entry["wikiPath"])
        assert is_repo_relative(entry["rawPath"])

    for entry in report["ruleIds"]:
        assert RULE_ID_PATTERN.match(entry["code"])
        assert is_repo_relative(entry["sourcePath"])

    for entry in report["sourceUrls"]:
        assert is_repo_relative(entry["rawPath"])

    raw_manifest = report["rawManifest"]
    assert raw_manifest["path"] == "raw/assets/manifest.json"
    assert raw_manifest["ok"] is True
    assert is_repo_relative(raw_manifest["path"])


def test_docstring_traceability_checker_accepts_linked_fixture(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fixture_root = tmp_path / "linked"
    write_traceable_fixture(fixture_root)

    result = run_checker(repo_root / "scripts" / "check_docstring_traceability.py", fixture_root)

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(
        (fixture_root / "reports" / "docstring-wiki-raw-traceability.json").read_text(
            encoding="utf-8"
        )
    )
    validate_report_shape(report)
    assert report["summary"]["docstringsTotal"] == 1
    assert report["summary"]["docstringsLinked"] == 1


def test_docstring_traceability_checker_rejects_unlinked_docstring(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fixture_root = tmp_path / "unlinked"
    write_traceable_fixture(fixture_root, linked_docstring=False)

    result = run_checker(repo_root / "scripts" / "check_docstring_traceability.py", fixture_root)

    assert result.returncode == 1
    report = json.loads(
        (fixture_root / "reports" / "docstring-wiki-raw-traceability.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["summary"]["docstringsTotal"] == 1
    assert report["summary"]["docstringsLinked"] == 0


def test_committed_traceability_report_matches_openqc_contract() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report_path = repo_root / "reports" / "docstring-wiki-raw-traceability.json"
    assert report_path.is_file(), "missing reports/docstring-wiki-raw-traceability.json"

    report = json.loads(report_path.read_text(encoding="utf-8"))
    validate_report_shape(report)
    assert report["repository"] == "newtontech/abinit-lsp"
    assert report["ruleIds"]
    assert report["wikiSources"]
    assert report["sourceUrls"]


def test_docstring_wiki_raw_traceability_is_complete() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "check_docstring_traceability.py"),
            "--root",
            str(repo_root),
            "--strict",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
