#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 path/to/abinit_lsp-*.whl" >&2
  exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEEL="$1"
if [[ "$WHEEL" != /* ]]; then
  WHEEL="$(pwd)/$WHEEL"
fi
if [ ! -f "$WHEEL" ]; then
  echo "wheel not found: $WHEEL" >&2
  exit 2
fi

PYTHON_BIN="${PYTHON:-python3}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

"$PYTHON_BIN" -m venv "$TMP_DIR/venv"
VENV_PYTHON="$TMP_DIR/venv/bin/python"
BIN="$TMP_DIR/venv/bin"
"$VENV_PYTHON" -m pip install --disable-pip-version-check "$WHEEL"

(
  cd "$TMP_DIR"
  # Server CLI: abinit-lsp --stdio
  printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    | "$BIN/abinit-lsp" --stdio >"$TMP_DIR/server.out" 2>"$TMP_DIR/server.err"
)

VALID="$REPO_ROOT/tests/fixtures/valid/silicon_scf.abi"
INVALID="$REPO_ROOT/tests/fixtures/invalid/missing_natom.abi"
LOG_FILE="$REPO_ROOT/tests/fixtures/logs/scf_not_converged.out"

# Agent CLI: abinit-lsp-tool check
"$BIN/abinit-lsp-tool" check "$VALID" --fail-on-blocking >"$TMP_DIR/valid.json"

if "$BIN/abinit-lsp-tool" check "$INVALID" --fail-on-blocking >"$TMP_DIR/invalid.json"; then
  echo "invalid fixture unexpectedly passed" >&2
  exit 1
fi

"$BIN/abinit-lsp-tool" check "$LOG_FILE" >"$TMP_DIR/log.json"

"$VENV_PYTHON" - "$TMP_DIR" <<'PY'
import importlib.metadata
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
assert importlib.metadata.version("abinit-lsp") == "0.1.1"

server = (root / "server.out").read_text()
valid = json.loads((root / "valid.json").read_text())
invalid = json.loads((root / "invalid.json").read_text())
log = json.loads((root / "log.json").read_text())

assert '"name": "abinit-lsp"' in server
assert '"version": "0.1.1"' in server
assert valid["ok"] is True
assert invalid["ok"] is False
assert any(item["code"] == "ABINIT102" for item in invalid["diagnostics"])
assert log["ok"] is False
assert any(item["code"] == "ABINIT200" for item in log["diagnostics"])
PY

echo "Fresh-wheel smoke passed: stdio server, agent CLI, valid/invalid/log fixtures"
