from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .models import ClassIndexEntry, ScriptDoc
from .utils import slug, anchor_id, rel_href
from .references import extract_references_from_text

def build_index_for_docs(
    docs: List[ScriptDoc],
    out_root: Path,
    src_root: Path,
    keep_structure: bool,
    split_functions: bool
) -> Dict[str, ClassIndexEntry]:
    """Build hyperlink index from parsed docs.

    Maps both ``class_name`` (if any) and the file stem to the same entry.

    Args:
        docs: Parsed scripts.
        out_root: Output root directory for relative paths.
        src_root: Source root used to compute relative mirrors when
            ``keep_structure`` is True.
        keep_structure: Mirror source folder structure under the output root.
        split_functions: Whether per-function files are generated.

    Returns:
        Dict keyed by class title (and file stem) → :class:`ClassIndexEntry`.
    """
    index: Dict[str, ClassIndexEntry] = {}
    for d in docs:
        p = d.path
        target_dir = (out_root / p.parent.relative_to(src_root)) if keep_structure else out_root
        class_basename = (d.class_name or p.stem)
        class_page_rel = (target_dir / f"{class_basename}.md").relative_to(out_root)
        functions_dir_rel = None
        if split_functions:
            functions_dir_rel = (target_dir / class_basename / "functions").relative_to(out_root)

        members_by_kind: Dict[str, set] = {}
        function_pages_rel: Dict[str, Path] = {}
        for m in d.members:
            members_by_kind.setdefault(m.kind, set()).add(m.name)
            if split_functions and m.kind == "func":
                function_pages_rel[m.name] = (target_dir / class_basename / "functions" / f"{slug(m.name)}.md").relative_to(out_root)

        entry = ClassIndexEntry(
            title=class_basename,
            class_page_rel=class_page_rel,
            functions_dir_rel=functions_dir_rel,
            members_by_kind=members_by_kind,
            function_pages_rel=function_pages_rel
        )

        keys = [class_basename]
        if d.class_name and d.class_name != class_basename:
            keys.append(d.class_name)
        if p.stem not in keys:
            keys.append(p.stem)

        for k in keys:
            if k not in index:
                index[k] = entry
    return index

def compute_reference_links_for_function(
    func_doc_raw: str,
    current_class_title: str,
    current_file_rel: Path,
    index: Dict[str, ClassIndexEntry],
    split_functions: bool
) -> List[str]:
    """Compute Markdown bullets for references mentioned in a function doc.

    Args:
        func_doc_raw: Raw BBCode docblock text for the function.
        current_class_title: Title (class name or stem) of the current class.
        current_file_rel: Current output file path relative to the output root.
        index: Global class index.
        split_functions: Whether function pages exist for deep linking.

    Returns:
        A list of Markdown list items linking to referenced classes/members.
    """
    refs = extract_references_from_text(func_doc_raw, default_class=current_class_title)
    if not refs:
        return []
    bullets: List[str] = []
    seen: set[Tuple[str, str]] = set()

    for r in refs:
        label_qual = r.raw_target
        label = f"`{r.kind} {label_qual}`"
        href: Optional[str] = None

        kind = r.kind
        cls_name = r.cls or (r.raw_target if kind == "class" else current_class_title)
        entry = index.get(cls_name)

        if not entry:
            bullet = f"- {label}"
            key = (label, "")
            if key not in seen:
                seen.add(key)
                bullets.append(bullet)
            continue

        if kind == "class":
            href = os.path.relpath((Path() / entry.class_page_rel).as_posix(),
                                start=(Path() / current_file_rel).parent.as_posix())
        elif kind == "method":
            if split_functions and r.member and r.member in entry.function_pages_rel:
                target = entry.function_pages_rel[r.member]
                href = os.path.relpath((Path() / target).as_posix(),
                                    start=(Path() / current_file_rel).parent.as_posix())
            else:
                base = os.path.relpath((Path() / entry.class_page_rel).as_posix(),
                                    start=(Path() / current_file_rel).parent.as_posix())
                anchor = anchor_id(r.member or "")
                href = f"{base}#{anchor}"
        else:
            kind_map = {"member": "var", "constant": "const", "signal": "signal", "enum": "enum"}
            idx_kind = kind_map.get(kind)

            if idx_kind and r.member and r.member in (entry.members_by_kind.get(idx_kind) or set()):
                base = os.path.relpath((Path() / entry.class_page_rel).as_posix(),
                                    start=(Path() / current_file_rel).parent.as_posix())
                anchor = anchor_id(r.member)
                href = f"{base}#{anchor}"
            else:
                href = os.path.relpath((Path() / entry.class_page_rel).as_posix(),
                                    start=(Path() / current_file_rel).parent.as_posix())

        bullet = f"- [{label}]({href})" if href else f"- {label}"
        key = (label, href or "")
        if key not in seen:
            seen.add(key)
            bullets.append(bullet)

    return bullets
