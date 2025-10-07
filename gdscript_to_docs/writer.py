from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
from .models import ScriptDoc
from .parser import parse_gd_script
from .render import render_script_markdown, render_function_markdown
from .indexer import build_index_for_docs, compute_reference_links_for_function
from .utils import slug, rel_href

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
        index_lines = ["# Index", ""]
        for d, _, path in rendered:
            rel = path.relative_to(out)
            index_lines.append(f"- [{d.class_name or d.path.stem}]({rel.as_posix()})")
            if split_functions:
                class_basename = d.class_name or d.path.stem
                func_root = rel.parent / class_basename / "functions"
                real_func_root = out / func_root
                if real_func_root.exists():
                    for m in [m for m in d.members if m.kind == "func"]:
                        f = real_func_root / f"{slug(m.name)}.md"
                        if f.exists():
                            index_lines.append(f"  - [{m.name}]({(rel.parent / class_basename / 'functions' / f.name).as_posix()})")
        (out / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
