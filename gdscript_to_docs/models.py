from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class TutorialLink:
    """External tutorial reference attached to a docblock.

    Attributes:
        title: Optional link text to display.
        url: Absolute or relative URL.
    """
    title: Optional[str]
    url: str

@dataclass
class DocBlock:
    """Parsed documentation block (script-level or member-level).

    Attributes:
        raw: Cleaned raw text (BBCode kept for link extraction).
        markdown: Markdown-rendered form of ``raw``.
        deprecated: True if a ``@deprecated`` tag was present.
        experimental: True if an ``@experimental`` tag was present.
        tutorials: Collected tutorial links from ``@tutorial(...)`` tags.
    """
    raw: str
    markdown: str
    deprecated: bool = False
    experimental: bool = False
    tutorials: List[TutorialLink] = field(default_factory=list)

@dataclass
class MemberDoc:
    """Documentation for a single script member (func/var/const/signal/enum).

    Attributes:
        kind: One of ``func``, ``var``, ``const``, ``signal``, ``enum``.
        name: Declared identifier.
        signature: Pretty signature (for functions/signals).
        type_hint: Type annotation (for vars/consts), if parsed.
        decorators: Lines of decorators (``@tool`` etc.).
        doc: Attached :class:`DocBlock` if found.
        source_start_line: 1-based start line in source (inclusive), if captured.
        source_end_line: 1-based end line in source (exclusive), if captured.
        source_code: Extracted source snippet for the declaration, if captured.
    """
    kind: str
    name: str
    signature: Optional[str] = None
    type_hint: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    doc: Optional[DocBlock] = None
    source_start_line: Optional[int] = None
    source_end_line: Optional[int] = None
    source_code: Optional[str] = None

@dataclass
class ScriptDoc:
    """Documentation for a single GDScript file.

    Attributes:
        path: Absolute path to the .gd file.
        class_name: Value of ``class_name`` if present.
        extends: Value of ``extends`` if present.
        script_doc: Script-level :class:`DocBlock` (or None).
        members: Collected member docs in file order (deduped).
    """
    path: Path
    class_name: Optional[str]
    extends: Optional[str]
    script_doc: Optional[DocBlock]
    members: List[MemberDoc] = field(default_factory=list)

@dataclass
class ParsedReference:
    """A parsed ``[method|member|signal|constant|enum|class ...]`` reference.

    Attributes:
        kind: Reference kind.
        raw_target: The raw target text inside the tag.
        cls: Parsed class part (if provided or inferred).
        member: Parsed member part (if any).
    """
    kind: str
    raw_target: str
    cls: Optional[str]
    member: Optional[str]

@dataclass
class ClassIndexEntry:
    """Index entry for hyperlinking between pages.

    Attributes:
        title: Class name or file stem used as display title.
        class_page_rel: Relative path to the class page from output root.
        functions_dir_rel: Relative dir for per-function pages (if split).
        members_by_kind: Mapping of kind → set of member names.
        function_pages_rel: Mapping function name → relative file path.
    """
    title: str
    class_page_rel: Path
    functions_dir_rel: Optional[Path]
    members_by_kind: Dict[str, set]
    function_pages_rel: Dict[str, Path]
