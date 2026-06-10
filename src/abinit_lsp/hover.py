"""Hover documentation for ABINIT keywords.

Provides documentation strings for keywords when hovering in an editor.
Handles dataset-suffixed keywords (e.g. ``ecut1``) by looking up the base
keyword.
"""

from __future__ import annotations

import re

from .completion import KEYWORD_DOCS


def get_hover_docs(keyword: str) -> str | None:
    """Return hover documentation for an ABINIT keyword.

    Returns ``None`` if the keyword is unknown.  Strips trailing dataset
    index digits before lookup (``ecut1`` → ``ecut``).
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
