from __future__ import annotations
from typing import List, Optional
from .models import ParsedReference
from .regexes import REF_TAG_RE

def extract_references_from_text(text_with_bbcode: str, default_class: Optional[str]) -> List[ParsedReference]:
    """Extract all Godot reference tags from doc text.

    The parser supports both explicit targets (``Class.member``) and
    implicit ones (``member``), in which case ``default_class`` is used for
    non-class kinds.

    Args:
        text_with_bbcode: Source doc text (BBCode allowed).
        default_class: Current class title to resolve implicit members.

    Returns:
        A list of :class:`ParsedReference` entries, in document order.
    """
    refs: List[ParsedReference] = []
    for kind, target in REF_TAG_RE.findall(text_with_bbcode or ""):
        target = target.strip()
        cls = None
        member = None
        if "." in target:
            cls, member = (p.strip() or None for p in target.split(".", 1))
        else:
            cls = default_class if kind != "class" else target
            member = None if kind == "class" else target
        refs.append(ParsedReference(kind=kind, raw_target=target, cls=cls, member=member))
    return refs
