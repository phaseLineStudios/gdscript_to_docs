from __future__ import annotations
"""GDScript documentation extractor and Markdown renderer.

Public API:
- write_docs
- parse_gd_script
- bbcode_to_markdown
- render_script_markdown
- render_function_markdown
- extract_references_from_text
"""

from .writer import write_docs
from .parser import parse_gd_script
from .bbcode import bbcode_to_markdown
from .render import render_script_markdown, render_function_markdown
from .references import extract_references_from_text
from ._version import __version__


__all__ = [
    "write_docs",
    "parse_gd_script",
    "bbcode_to_markdown",
    "render_script_markdown",
    "render_function_markdown",
    "extract_references_from_text",
    "__version__"
]
