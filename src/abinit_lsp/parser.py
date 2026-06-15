"""Structured parser for ABINIT input files.

ABINIT input files consist of keyword-value pairs. Keywords may have dataset
suffixes (e.g. ``ecut1``, ``ecut2`` for multi-dataset runs). Values can span
multiple lines for arrays/matrices. Comments start with ``#``, ``!``, or ``;``.

LLM Wiki: wiki/entities/ABINIT.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AbinitEntry:
    """A single keyword entry in an ABINIT file.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """

    keyword: str
    values: list[str]
    line: int
    raw_line: str = ""

    @property
    def base_keyword(self) -> str:
        """Strip trailing dataset index digits to get the base keyword.

        LLM Wiki: wiki/synthesis/openqc-agent-context.md
        """
        m = re.match(r"^(.*?)(\d+)$", self.keyword)
        return m.group(1) if m else self.keyword

    @property
    def dataset(self) -> int | None:
        """Return the dataset index (trailing digits) if present.

        LLM Wiki: wiki/synthesis/openqc-agent-context.md
        """
        m = re.match(r"^(.*?)(\d+)$", self.keyword)
        return int(m.group(2)) if m else None


@dataclass
class AbinitFile:
    """Parsed representation of an ABINIT input file.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """

    path: Path
    entries: list[AbinitEntry] = field(default_factory=list)
    comments: list[tuple[int, str]] = field(default_factory=list)

    def keywords(self) -> set[str]:
        """Return the set of unique keywords (including dataset suffixes).

        LLM Wiki: wiki/synthesis/openqc-agent-context.md
        """
        return {e.keyword for e in self.entries}

    def has_keyword(self, name: str) -> bool:
        """Check if a keyword is present (case-insensitive).

        LLM Wiki: wiki/synthesis/openqc-agent-context.md
        """
        name_lower = name.lower()
        return any(e.keyword == name_lower for e in self.entries)

    def get_entries_for(self, keyword: str) -> list[AbinitEntry]:
        """Return all entries matching a given keyword.

        LLM Wiki: wiki/synthesis/openqc-agent-context.md
        """
        keyword_lower = keyword.lower()
        return [e for e in self.entries if e.keyword == keyword_lower]


# Tokens that accept multi-line values (arrays / matrices).
# The parser will keep reading following lines that don't start with a known
# keyword pattern.
_MULTILINE_KEYWORDS: set[str] = {
    "rprim",
    "acell",
    "scalecart",
    "xcart",
    "xred",
    "xangst",
    "vel",
    "velcart",
    "fcart",
    "fred",
    "typat",
    "znucl",
    "amu",
}

# Regex for a keyword token: starts with a letter, may contain letters, digits,
# underscores, dots, hyphens. May end with dataset digits.
_KEYWORD_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-.]*$")

# Comment prefixes
_COMMENT_PREFIXES = ("#", "!", ";")


def parse(path: Path) -> AbinitFile:
    """Parse an ABINIT file from a path.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    path = Path(path)
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return AbinitFile(path=path)
    return parse_content(path, content)


def parse_content(path: Path, content: str) -> AbinitFile:
    """Parse ABINIT content string into structured representation.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    af = AbinitFile(path=path)
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        line_no = i + 1  # 1-based line numbers

        # Skip blank lines
        if not stripped:
            i += 1
            continue

        # Track comments
        if stripped.startswith(_COMMENT_PREFIXES):
            af.comments.append((line_no, stripped))
            i += 1
            continue

        # Parse keyword + values
        keyword, values = _parse_keyword_line(stripped)
        if keyword is None:
            i += 1
            continue

        keyword = keyword.lower()

        # Handle multiline entries for known array keywords
        if keyword in _MULTILINE_KEYWORDS and not values:
            # Values are on following lines
            i += 1
            while i < len(lines):
                next_stripped = lines[i].strip()
                if not next_stripped or next_stripped.startswith(_COMMENT_PREFIXES):
                    i += 1
                    continue
                # Check if this line starts a new keyword
                potential_kw = next_stripped.split()[0].lower()
                if _KEYWORD_RE.match(potential_kw) and (
                    potential_kw == potential_kw.rstrip("0123456789").rstrip("_")
                ):
                    # It's a new keyword - stop multiline
                    break
                # It's value continuation
                values.extend(next_stripped.split())
                i += 1
            af.entries.append(
                AbinitEntry(keyword=keyword, values=values, line=line_no, raw_line=raw)
            )
            continue
        elif keyword in _MULTILINE_KEYWORDS and values:
            # Values may be incomplete - check if we need more lines
            # Common for rprim to have values spread across lines
            i += 1
            while i < len(lines):
                next_stripped = lines[i].strip()
                if not next_stripped or next_stripped.startswith(_COMMENT_PREFIXES):
                    i += 1
                    continue
                potential_kw = next_stripped.split()[0].lower()
                if _KEYWORD_RE.match(potential_kw):
                    break
                values.extend(next_stripped.split())
                i += 1
            af.entries.append(
                AbinitEntry(keyword=keyword, values=values, line=line_no, raw_line=raw)
            )
            continue
        else:
            af.entries.append(
                AbinitEntry(keyword=keyword, values=values, line=line_no, raw_line=raw)
            )
            i += 1

    return af


def _parse_keyword_line(line: str) -> tuple[str | None, list[str]]:
    """Parse a single line into (keyword, [values]).

    Supports both ``keyword value1 value2`` and ``keyword = value`` syntaxes.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    # Handle equals syntax
    if "=" in line:
        parts = line.split("=", 1)
        kw = parts[0].strip()
        if not kw:
            return None, []
        val_str = parts[1].strip()
        values = val_str.split() if val_str else []
        return kw, values

    # Space-separated syntax
    parts = line.split()
    if not parts:
        return None, []

    kw = parts[0]
    # Validate it looks like a keyword
    if not _KEYWORD_RE.match(kw):
        return None, []

    values = parts[1:]
    return kw, values
