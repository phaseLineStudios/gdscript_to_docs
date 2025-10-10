from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from .models import ScriptDoc
from .parser import parse_gd_script
from .render import render_script_markdown, render_function_markdown
from .indexer import build_index_for_docs, compute_reference_links_for_function
from .utils import slug, rel_href, split_brief_details

def write_docs(
    src: Path,
    out: Path,
    keep_structure: bool=False,
    single_file: bool=False,
    make_index: bool=False,
    glob: str="**/*.gd",
    style: str="doxygen",
    split_functions: bool=False
) -> None:
    """Generate Markdown docs from a GDScript source tree.

    Workflow:
      1. Glob ``*.gd`` files under ``src``.
      2. Parse each file into :class:`ScriptDoc`.
      3. Build a class index for links and (optionally) function pages.
      4. Render class/function pages and write to ``out``.
      5. Optionally create ``INDEX.md`` (or a bundled ``DOCUMENTATION.md``).

    Args:
        src: Source root directory to scan (resolved to absolute).
        out: Output directory (created if missing).
        keep_structure: Mirror the source folder structure under ``out``.
        single_file: Write a single ``DOCUMENTATION.md`` instead of per-class files.
        make_index: Write a top-level ``INDEX.md`` (ignored if ``single_file``).
        glob: Glob pattern relative to ``src`` (default: ``**/*.gd``).
        style: Rendering style, ``'doxygen'`` (default) or ``'classic'``.
        split_functions: Emit separate pages under ``<ClassName>/functions/``.

    Returns:
        None. Files are written to disk.
    """
    src = src.resolve()
    out.mkdir(parents=True, exist_ok=True)

    scripts = sorted(src.glob(glob))
    if not scripts:
        print(f"No .gd files found under: {src}", file=sys.stderr)  # type: ignore[name-defined]
        return

    docs: List[ScriptDoc] = [parse_gd_script(p) for p in scripts]

    class_index = build_index_for_docs(
        docs=docs, out_root=out, src_root=src,
        keep_structure=keep_structure, split_functions=split_functions
    )

    rendered: List[Tuple[ScriptDoc, str, Path]] = []
    class_page_paths: Dict[str, Path] = {}

    for d in docs:
        p = d.path
        target_dir = (out / p.parent.relative_to(src)) if keep_structure else out
        target_dir.mkdir(parents=True, exist_ok=True)

        class_basename = (d.class_name or p.stem)
        class_md_path = target_dir / f"{class_basename}.md"
        link_dir = None
        if split_functions:
            func_dir = target_dir / class_basename / "functions"
            func_dir.mkdir(parents=True, exist_ok=True)
            link_dir = f"{class_basename}/functions"

        md = render_script_markdown(d, project_root=src, style=style, link_functions_dir=link_dir)
        rendered.append((d, md, class_md_path))
        class_page_paths[class_basename] = class_md_path

        if split_functions:
            for m in d.members:
                if m.kind != "func":
                    continue
                fpath = target_dir / class_basename / "functions" / f"{slug(m.name)}.md"
                current_file_rel = fpath.relative_to(out)
                belongs_to_href = rel_href(class_md_path.relative_to(out), current_file_rel.parent)

                raw = m.doc.raw if (m.doc and m.doc.raw) else ""
                refs_md = compute_reference_links_for_function(
                    func_doc_raw=raw,
                    current_class_title=class_basename,
                    current_file_rel=current_file_rel,
                    index=class_index,
                    split_functions=split_functions,
                )
                fmd = render_function_markdown(
                    d, m, project_root=src, style=style,
                    references_md_lines=refs_md,
                    belongs_to_href=belongs_to_href
                )
                fpath.write_text(fmd, encoding="utf-8")

    if single_file:
        bundle = ["# Project Documentation", ""]
        for _, md, _ in rendered:
            bundle.append(md); bundle.append("\n---\n")
        (out / "DOCUMENTATION.md").write_text("\n".join(bundle).rstrip() + "\n", encoding="utf-8")
    else:
        for _, md, path in rendered:
            path.write_text(md, encoding="utf-8")

    if make_index and not single_file:
        write_index(out=out, rendered=rendered, split_functions=split_functions)

def write_index(
    out: Path,
    rendered: list[tuple["ScriptDoc", str, Path]],
    split_functions: bool,
) -> None:
    """
    Write a structured index under ``out/_index/``.
    Args:
        out: Output directory where docs were written.
        rendered: List of tuples (ScriptDoc, rendered_markdown, class_md_path).
        split_functions: Whether function pages were split out.
    """
    index_dir = out / "_index"
    index_dir.mkdir(parents=True, exist_ok=True)

    class_rows = []
    for d, _, class_md_path in rendered:
        title = d.class_name or d.path.stem
        rel_class_md = class_md_path.relative_to(out)
        parent_rel_dir = rel_class_md.parent
        extends = d.extends or ""
        counts = {
            "func": sum(1 for m in d.members if m.kind == "func"),
            "var":  sum(1 for m in d.members if m.kind == "var"),
            "const":sum(1 for m in d.members if m.kind == "const"),
            "signal":sum(1 for m in d.members if m.kind == "signal"),
            "enum": sum(1 for m in d.members if m.kind == "enum"),
        }
        class_rows.append((title, rel_class_md, parent_rel_dir, extends, counts))

    by_folder_lines = ["# Classes by Folder", ""]
    from collections import defaultdict
    classes_by_folder: dict[str, list[tuple[str, Path, str, dict]]] = defaultdict(list)
    for title, rel_md, parent_dir, extends, counts in class_rows:
        classes_by_folder[parent_dir.as_posix()].append((title, rel_md, extends, counts))
    for folder in sorted(classes_by_folder.keys(), key=lambda s: (s.count("/"), s)):
        depth = 0 if folder == "." else folder.count("/") + (0 if not folder else 1)
        header_prefix = "#" * max(2, min(6, depth + 2))
        folder_label = folder if folder and folder != "." else "(root)"
        by_folder_lines.append(f"{header_prefix} {folder_label}")
        by_folder_lines.append("")
        for title, rel_md, extends, counts in sorted(classes_by_folder[folder], key=lambda r: r[0].lower()):
            href = rel_href(rel_md, start_rel=Path("_index"))  # file lives at _index/by-folder.md
            summary = f"{counts['func']} funcs · {counts['var']} vars · {counts['signal']} signals · {counts['const']} consts · {counts['enum']} enums"
            ext = f" — *inherits* `{extends}`" if extends else ""
            by_folder_lines.append(f"- [{title}]({href}) — {summary}{ext}")
        by_folder_lines.append("")

    (index_dir / "by-folder.md").write_text("\n".join(by_folder_lines).rstrip() + "\n", encoding="utf-8")

    classes_lines = ["# Classes A–Z", ""]
    buckets: dict[str, list[tuple[str, Path, str, dict]]] = defaultdict(list)
    for title, rel_md, _, extends, counts in class_rows:
        first = title[0].upper() if title else "#"
        if not ("A" <= first <= "Z"):
            first = "#"
        buckets[first].append((title, rel_md, extends, counts))

    letters = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"] + ["#"]
    classes_lines.append("**Jump to:** " + " · ".join(f"[{L}](#{L.lower()})" for L in letters))
    classes_lines.append("")

    for L in letters:
        if L not in buckets:
            continue
        classes_lines.append(f"## {L}")
        classes_lines.append("")
        for title, rel_md, extends, counts in sorted(buckets[L], key=lambda r: r[0].lower()):
            href = rel_href(rel_md, start_rel=Path("_index"))
            summary = f"{counts['func']} funcs · {counts['var']} vars · {counts['signal']} signals"
            ext = f" — *inherits* `{extends}`" if extends else ""
            classes_lines.append(f"- [{title}]({href}) — {summary}{ext}")
        classes_lines.append("")

    (index_dir / "classes.md").write_text("\n".join(classes_lines).rstrip() + "\n", encoding="utf-8")

    if split_functions:
        funcs_lines = ["# Functions A–Z", ""]
        fn_buckets: dict[str, list[tuple[str, str, Path, Optional[str]]]] = defaultdict(list)
        for d, _, class_md_path in rendered:
            class_title = d.class_name or d.path.stem
            class_rel = class_md_path.relative_to(out)
            functions_dir = class_rel.parent / class_title / "functions"
            for m in (mm for mm in d.members if mm.kind == "func"):
                fpath = functions_dir / f"{slug(m.name)}.md"
                real_path = out / fpath
                if not real_path.exists():
                    continue
                first = (m.name[0].upper() if m.name else "#")
                if not ("A" <= first <= "Z"):
                    first = "#"
                brief = None
                if m.doc and m.doc.markdown:
                    b, _ = split_brief_details(m.doc.markdown)
                    brief = b or None
                fn_buckets[first].append((class_title, m.name, fpath, brief))

        funcs_lines.append("**Jump to:** " + " · ".join(f"[{L}](#{L.lower()})" for L in letters))
        funcs_lines.append("")

        for L in letters:
            if L not in fn_buckets:
                continue
            funcs_lines.append(f"## {L}")
            funcs_lines.append("")
            for class_title, fname, rel_fn_md, brief in sorted(fn_buckets[L], key=lambda r: (r[1].lower(), r[0].lower())):
                href = rel_href(rel_fn_md, start_rel=Path("_index"))
                title = f"{class_title}::{fname}"
                line = f"- [{title}]({href})"
                if brief:
                    line += f" — {brief}"
                funcs_lines.append(line)
            funcs_lines.append("")
        (index_dir / "functions.md").write_text("\n".join(funcs_lines).rstrip() + "\n", encoding="utf-8")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    main = [
        "# Game API Reference",
        "",
        f"*Generated on:* {now}",
        "",
        "### Navigation",
        "",
        "- **By Folder:** [_index/by-folder.md](_index/by-folder.md)",
        "- **Classes A–Z:** [_index/classes.md](_index/classes.md)",
    ]
    if split_functions:
        main.append("- **Functions A–Z:** [_index/functions.md](_index/functions.md)")
    main += [
        "",
        "### Tips",
        "",
        "- Use your viewer’s search (e.g. GitHub’s file search or browser **Ctrl/⌘+F**).",
        "- Each class page has a summary and detailed sections (functions, signals, etc.).",
    ]
    (out / "INDEX.md").write_text("\n".join(main).rstrip() + "\n", encoding="utf-8")