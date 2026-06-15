"""Hover documentation for ABINIT keywords.

Provides documentation strings for keywords when hovering in an editor.
Handles dataset-suffixed keywords (e.g. ``ecut1``) by looking up the base
keyword.

Source provenance: KEYWORD_DOCS entries trace to official ABINIT documentation
at https://docs.abinit.org/variables/ . The wiki manifest at
raw/assets/upstream-sources.md maps each variable to its canonical URL.

LLM Wiki: wiki/entities/ecut.md

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import re

from .completion import KEYWORD_DOCS


def get_hover_docs(keyword: str) -> str | None:
    """Return hover documentation for an ABINIT keyword.

    Returns ``None`` if the keyword is unknown.  Strips trailing dataset
    index digits before lookup (``ecut1`` → ``ecut``).

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    kw_lower = keyword.lower().strip()

    # Direct lookup
    if kw_lower in KEYWORD_DOCS:
        return KEYWORD_DOCS[kw_lower]

    # Strip trailing digits (dataset index)
    base = re.sub(r"\d+$", "", kw_lower)
    if base and base in KEYWORD_DOCS:
        return KEYWORD_DOCS[base]

    return None
