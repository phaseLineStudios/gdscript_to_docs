from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import os
import re

def slug(s: str) -> str:
    """Create a filesystem-safe slug from a member name."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", s).strip("-")

def anchor_id(s: str) -> str:
    """Generate a conservative GitHub-style anchor ID from a heading text."""
    s = s.strip().lower()
    s = re.sub(r"[^\w\- ]+", "", s)
    return s.replace(" ", "-")

def indent_level(line: str) -> int:
    """Count leading indentation characters (spaces/tabs)."""
    i = 0
    while i < len(line) and line[i] in (" ", "\t"):
        i += 1
    return i

def capture_function_block(lines: List[str], func_start_idx: int) -> Tuple[int, str]:
    """Capture a function's indented block to compute end line and source.

    Args:
        lines: All file lines.
        func_start_idx: Index of the ``func`` declaration line.

    Returns:
        (next_index, code) where ``next_index`` is the first line after the
        captured block; ``code`` is the extracted source string (with newline).
    """
    start = func_start_idx
    base_indent = indent_level(lines[start])
    end = start + 1
    while end < len(lines):
        ln = lines[end]
        if ln.strip() == "":
            end += 1
            continue
        if indent_level(ln) <= base_indent:
            break
        end += 1
    code = "\n".join(lines[start:end]).rstrip() + "\n"
    return end, code

def split_brief_details(md: str) -> Tuple[str, str]:
    """Split a Markdown paragraph into brief sentence and remainder.

    The brief is the first sentence ending with ``. ! ?`` if present; otherwise
    the first line.

    Args:
        md: Markdown text.

    Returns:
        (brief, details) where either may be empty strings.
    """
    s = (md or "").strip()
    if not s:
        return "", ""
    m = re.match(r"(?s)\s*(.*?[\.\!\?])(\s+.*)?$", s)
    if m:
        return m.group(1).strip(), (m.group(2) or "").strip()
    parts = s.splitlines()
    return parts[0].strip(), "\n".join(parts[1:]).strip()

def rel_href(target_rel: Path, start_rel: Path) -> str:
    """Return a POSIX relative href from start_rel → target_rel.

    Both paths must be relative to the same root (the output root).
    """
    return Path(os.path.relpath(target_rel, start=start_rel)).as_posix()
