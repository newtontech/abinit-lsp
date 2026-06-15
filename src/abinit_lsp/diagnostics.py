from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    file: str
    line: int
    column: int = 1
    evidence: list[str] = field(default_factory=list)
    suggested_fix: dict[str, Any] | None = None
    confidence: float = 1.0
    # Optional envelope fields. When populated, rich_diagnostics serializes
    # them into the DiagnosticEnvelope/v1 payload so OpenQC consumers can
    # trace every diagnostic back to its official source. Producers that do
    # not evidence these fields leave them as None and the envelope omits
    # them, preserving the legacy shape for existing callers.
    source_provenance: dict[str, Any] | None = None
    manual_ref: str | None = None
    version_scope: dict[str, str] | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)
