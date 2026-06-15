#!/usr/bin/env bash
# refresh-wiki-digest.sh — Recompute raw/assets checksums and verify wiki links.
#
# Usage (from repo root):
#   bash scripts/refresh-wiki-digest.sh
#
# This script does NOT fetch remote documentation. It refreshes the local
# provenance digest so reviewers can confirm captured assets still match the
# recorded checksums in raw/assets/manifest.json.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASSETS="${REPO_ROOT}/raw/assets"
MANIFEST="${ASSETS}/manifest.json"

echo "=== ABINIT LSP wiki/provenance digest refresh ==="
echo "Repo: ${REPO_ROOT}"

if [ ! -f "${MANIFEST}" ]; then
  echo "FAIL: missing ${MANIFEST}"
  exit 1
fi

python3 - "${REPO_ROOT}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
assets = repo / "raw" / "assets"
manifest_path = assets / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
mismatches: list[str] = []

for entry in manifest.get("entries", []):
    rel = entry.get("path")
    if not rel:
        continue
    file_path = assets / rel
    if not file_path.is_file():
        mismatches.append(f"missing file: {rel}")
        continue
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    recorded = entry.get("checksum_sha256")
    if recorded and digest != recorded:
        mismatches.append(f"checksum drift: {rel} (recorded {recorded[:12]}… actual {digest[:12]}…)")

if mismatches:
    print("CHECKSUM MISMATCHES:")
    for item in mismatches:
        print(f"  - {item}")
    raise SystemExit(1)

print(f"OK: {len(manifest.get('entries', []))} manifest entries match on-disk checksums")
print(f"OK: {len(manifest.get('official_source_anchors', []))} official source anchors recorded")
PY

bash "${REPO_ROOT}/scripts/wiki-lint.sh"

echo ""
echo "Digest refresh complete. Update raw/assets/manifest.json checksums only when"
echo "captured assets intentionally change, then commit manifest + wiki updates together."
