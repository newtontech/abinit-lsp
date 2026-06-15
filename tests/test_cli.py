"""Tests for CLI entrypoints."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import patch

from abinit_lsp.cli import fmt_main, lint_main, lsp_main
from abinit_lsp.cli import test_main as cli_test_main

FIXTURES = Path(__file__).parent / "fixtures"


class TestLintCLI:
    def test_valid_file_returns_0(self, tmp_path: Path) -> None:
        f = tmp_path / "good.abi"
        f.write_text('ecut 30\npseudos "Si.psp8"\nnatom 1\ntypat 1\nznucl 1\nxred 0 0 0\n')
        assert lint_main([str(f)]) == 0

    def test_error_file_returns_1(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.abi"
        f.write_bytes(b"\x80\x81")
        assert lint_main([str(f)]) == 1

    def test_json_output(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text('ecut 30\npseudos "Si.psp8"\nnatom 1\ntypat 1\nznucl 1\nxred 0 0 0\n')
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            lint_main([str(f), "--json"])
        data = json.loads(out.getvalue())
        assert isinstance(data, list)

    def test_directory_mode(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text('ecut 30\npseudos "Si.psp8"\nnatom 1\ntypat 1\nznucl 1\nxred 0 0 0\n')
        assert lint_main([str(tmp_path)]) == 0


class TestFmtCLI:
    def test_write_mode(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\n")
        assert fmt_main(["-w", str(f)]) == 0

    def test_stdout_mode(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\n")
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            rc = fmt_main([str(f)])
        assert rc == 0
        assert "ecut" in out.getvalue()


class TestTestCLI:
    def test_static_delegates_to_lint(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text('ecut 30\npseudos "Si.psp8"\nnatom 1\ntypat 1\nznucl 1\nxred 0 0 0\n')
        rc = cli_test_main(["static", str(f)])
        assert rc == 0

    def test_static_json(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text('ecut 30\npseudos "Si.psp8"\nnatom 1\ntypat 1\nznucl 1\nxred 0 0 0\n')
        with patch("sys.stdout", new_callable=io.StringIO):
            rc = cli_test_main(["static", str(f), "--json"])
        assert rc == 0


class TestLSPCLI:
    def test_lsp_stdio_flag(self) -> None:
        rc = lsp_main(["--stdio"])
        assert rc == 0
