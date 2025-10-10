from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
from .bbcode import bbcode_to_markdown
from .models import MemberDoc, ScriptDoc
from .utils import slug, split_brief_details, extract_params_and_return
import re

def _inline_sig(m: MemberDoc) -> str:
    """Build a compact inline signature for list views."""
    if m.kind == "func":
        return f"`{m.signature}`" if m.signature else f"`func {m.name}()`"
    if m.kind == "var":
        t = (m.type_hint or "").strip()
        return f"`{t} {m.name}`".strip() if t else f"`{m.name}`"
    if m.kind == "const":
        t = (m.type_hint or "").strip()
        return f"`const {m.name}" + (f": {t}`" if t else "`")
    if m.kind == "signal":
        return f"`{m.signature}`" if m.signature else f"`signal {m.name}`"
    if m.kind == "enum":
        return f"`enum {m.name}`"
    return f"`{m.name}`"

def _block_sig(m: MemberDoc) -> List[str]:
    """Build a fenced signature block for detailed sections."""
    if m.kind == "func":
        return ["```gdscript", m.signature or f"func {m.name}()", "```"]
    if m.kind == "var":
        t = (m.type_hint or "").strip()
        return ["```gdscript", f"var {m.name}" + (f": {t}" if t else ""), "```"]
    if m.kind == "const":
        t = (m.type_hint or "").strip()
        return ["```gdscript", f"const {m.name}" + (f": {t}" if t else ""), "```"]
    if m.kind == "signal":
        return ["```gdscript", m.signature or f"signal {m.name}", "```"]
    if m.kind == "enum":
        return ["```gdscript", f"enum {m.name}", "```"]
    return []

def _render_script_markdown_classic(doc: ScriptDoc, project_root: Path) -> str:
    """Render a single class page in the compact 'classic' style.

    Args:
        doc: Parsed script documentation.
        project_root: Root used to present relative file paths.

    Returns:
        The Markdown page content.
    """
    title = doc.class_name or doc.path.stem
    rel = doc.path.relative_to(project_root) if hasattr(Path, "is_relative_to") and doc.path.is_relative_to(project_root) else doc.path
    lines = [f"# {title}", "", f"*File:* `{rel.as_posix()}`"]
    if doc.class_name: lines.append(f"*Class name:* `{doc.class_name}`")
    if doc.extends: lines.append(f"*Extends:* `{doc.extends}`")
    lines.append("")
    if doc.script_doc:
        if doc.script_doc.deprecated: lines.append("> **Deprecated**")
        if doc.script_doc.experimental: lines.append("> **Experimental**")
        if doc.script_doc.tutorials:
            tuts = " • ".join(f"[{t.title}]({t.url})" if t.title else f"<{t.url}>" for t in doc.script_doc.tutorials)
            lines += [f"> Tutorials: {tuts}", ""]
        lines += [doc.script_doc.markdown, ""]
    if doc.members:
        by_kind: Dict[str, List[MemberDoc]] = {}
        for m in doc.members: by_kind.setdefault(m.kind, []).append(m)
        for kind, heading in [("func","Functions"),("var","Variables"),("const","Constants"),("signal","Signals"),("enum","Enums")]:
            if kind not in by_kind: continue
            lines += [f"## {heading}", ""]
            for m in by_kind[kind]:
                nm = f"**{m.name}**"; meta=[]
                if m.type_hint: meta.append(f"`{m.type_hint.strip()}`")
                if m.signature: meta.append(f"`{m.signature}`")
                if m.decorators: meta.append(", ".join(f"`{d}`" for d in m.decorators))
                bullet = nm if not meta else f"{nm} — " + "; ".join(meta)
                lines.append(f"- {bullet}")
                if m.doc and m.doc.markdown:
                    if m.doc.deprecated: lines.append("  - **Deprecated**")
                    if m.doc.experimental: lines.append("  - **Experimental**")
                    if m.doc.tutorials:
                        tuts = " • ".join(f"[{t.title}]({t.url})" if t.title else f"<{t.url}>" for t in m.doc.tutorials)
                        lines.append(f"  - Tutorials: {tuts}")
                    md = m.doc.markdown.replace("\n","\n  ")
                    lines.append(f"  - {md}")
                lines.append("")
    else:
        lines.append("_No members found._")
    return "\n".join(lines).rstrip() + "\n"

def render_script_markdown(
    doc: ScriptDoc,
    project_root: Path,
    *,
    style: str = "doxygen",
    link_functions_dir: str | None = None
) -> str:
    """Render a class page in Doxygen-like or classic style.

    Args:
        doc: Parsed script documentation.
        project_root: Root used to present relative file paths.
        style: One of ``'doxygen'`` (default) or ``'classic'``.
        link_functions_dir: If set, function summary entries link to per-function
            pages under ``<link_functions_dir>/<slug>.md``.

    Returns:
        The Markdown page content.
    """
    if style not in ("classic", "doxygen"):
        style = "doxygen"
    if style == "classic":
        return _render_script_markdown_classic(doc, project_root)

    title = doc.class_name or doc.path.stem
    rel = doc.path.relative_to(project_root) if hasattr(Path, "is_relative_to") and doc.path.is_relative_to(project_root) else doc.path
    lines = [f"# {title} Class Reference", "", f"*File:* `{rel.as_posix()}`"]
    if doc.class_name: lines.append(f"*Class name:* `{doc.class_name}`")
    if doc.extends: lines.append(f"*Inherits:* `{doc.extends}`")
    if doc.script_doc and (doc.script_doc.deprecated or doc.script_doc.experimental):
        flags = []
        if doc.script_doc.deprecated: flags.append("**Deprecated**")
        if doc.script_doc.experimental: flags.append("**Experimental**")
        lines.append("> " + " • ".join(flags))
    lines.append("")

    lines += ["## Synopsis", ""]
    syn = ["```gdscript"]
    if doc.class_name: syn.append(f"class_name {doc.class_name}")
    if doc.extends: syn.append(f"extends {doc.extends}")
    syn.append("```")
    lines += syn + [""]

    brief, details = ("", "")
    if doc.script_doc and doc.script_doc.markdown:
        brief, details = split_brief_details(doc.script_doc.markdown)
    if brief:
        lines += ["## Brief", "", brief, ""]
    if details:
        lines += ["## Detailed Description", "", details, ""]
    elif doc.script_doc and not brief:
        lines += ["## Detailed Description", "", doc.script_doc.markdown, ""]
    if doc.script_doc and doc.script_doc.tutorials:
        tuts = " • ".join(f"[{t.title}]({t.url})" if t.title else f"<{t.url}>" for t in doc.script_doc.tutorials)
        lines += [f"**Tutorials:** {tuts}", ""]

    by_kind: Dict[str, List[MemberDoc]] = {}
    for m in doc.members:
        by_kind.setdefault(m.kind, []).append(m)

    sections = [
        ("func", "Public Member Functions"),
        ("var", "Public Attributes"),
        ("const", "Public Constants"),
        ("signal", "Signals"),
        ("enum", "Enumerations"),
    ]
    any_members = any(by_kind.get(k) for k, _ in sections)
    if any_members:
        for kind, heading in sections:
            if kind not in by_kind or not by_kind[kind]:
                continue
            lines += [f"## {heading}", ""]
            for m in by_kind[kind]:
                bullet = f"- {_inline_sig(m)}"
                if kind == "func" and link_functions_dir:
                    mfile = f"{link_functions_dir}/{slug(m.name)}.md"
                    bullet = f"- [{_inline_sig(m)}]({mfile})"
                if m.doc and m.doc.markdown:
                    b, _ = split_brief_details(m.doc.markdown)
                    if b:
                        flags = []
                        if m.doc.deprecated: flags.append("**Deprecated**")
                        if m.doc.experimental: flags.append("**Experimental**")
                        bullet += f" — {b}" + (f" {' '.join(flags)}" if flags else "")
                lines.append(bullet)
            lines.append("")
    else:
        lines.append("_No members found._")

    def _detail(kind: str, heading: str):
        items = by_kind.get(kind) or []
        if not items: return
        lines.extend([f"## {heading}", ""])
        for m in items:
            lines.append(f"### {m.name}")
            lines.append("")
            lines.extend(_block_sig(m))
            if m.decorators:
                lines.append("")
                lines.append("Decorators: " + ", ".join(f"`{d}`" for d in m.decorators))
            if m.doc:
                if m.doc.deprecated: lines.append("\n> **Deprecated**")
                if m.doc.experimental: lines.append("\n> **Experimental**")
                if m.doc.tutorials:
                    tuts = " • ".join(f"[{t.title}]({t.url})" if t.title else f"<{t.url}>" for t in m.doc.tutorials)
                    lines.append(f"\n**Tutorials:** {tuts}")
                if m.doc.markdown:
                    lines.extend(["", m.doc.markdown])
            lines.append("")

    _detail("func",   "Member Function Documentation")
    _detail("var",    "Member Data Documentation")
    _detail("const",  "Constant Documentation")
    _detail("signal", "Signal Documentation")
    _detail("enum",   "Enumeration Type Documentation")

    return "\n".join(lines).rstrip() + "\n"

def render_function_markdown(
    doc: ScriptDoc,
    func: MemberDoc,
    project_root: Path,
    *,
    style: str = "doxygen",
    references_md_lines: Optional[List[str]] = None,
    belongs_to_href: Optional[str] = None,
) -> str:
    """Render a single function reference page.

    Args:
        doc: Parent script.
        func: Function member to render.
        project_root: Root used to present relative file paths.
        style: Currently unused; reserved for parity with class rendering.
        references_md_lines: Optional bullet list of “References” to append.

    Returns:
        The Markdown page content.
    """
    title = doc.class_name or doc.path.stem
    rel = doc.path.relative_to(project_root) if hasattr(Path, "is_relative_to") and doc.path.is_relative_to(project_root) else doc.path

    header = f"{title}::{func.name}"
    lines = [f"# {header} Function Reference", ""]

    if func.source_start_line and func.source_end_line:
        lines.append(f"*Defined at:* `{rel.as_posix()}` (lines {func.source_start_line}–{func.source_end_line})</br>")
    else:
        lines.append(f"*File:* `{rel.as_posix()}`")

    # Robust “Belongs to” link (computed in writer, fallback is ../../Title.md)
    fallback = f"../../{title}.md"
    lines.append(f"*Belongs to:* [{title}]({belongs_to_href or fallback})")
    lines.append("")

    lines += ["**Signature**", "", "```gdscript", func.signature or f"func {func.name}()", "```", ""]
    params: list[tuple[str, str]] = []
    ret_text: Optional[str] = None
    desc_md: Optional[str] = None

    if func.doc:
        p, r, remaining_raw = extract_params_and_return(func.doc.raw or "")
        params, ret_text = p, r
        remaining_raw = re.sub(r"\[param\s+([^\]]+)\]", r"`\1`", remaining_raw)
        desc_md = bbcode_to_markdown(remaining_raw) if remaining_raw.strip() else None

    if params:
        for nm, ds in params:
            bullet = f"- **{nm}**"
            if ds:
                ds = re.sub(r"\[param\s+([^\]]+)\]", r"`\1`", ds)
                bullet += f": {bbcode_to_markdown(ds)}"
            lines.append(bullet)
    if ret_text:
        ret_text = re.sub(r"\[param\s+([^\]]+)\]", r"`\1`", ret_text)
        lines.append(f"- **Return Value**: {bbcode_to_markdown(ret_text)}")
    if params or ret_text:
        lines.append("")

    if func.decorators:
        lines.append("**Decorators:** " + ", ".join(f"`{d}`" for d in func.decorators))
        lines.append("")
    if func.doc:
        flags = []
        if func.doc.deprecated: flags.append("**Deprecated**")
        if func.doc.experimental: flags.append("**Experimental**")
        if flags:
            lines.append("> " + " • ".join(flags))
            lines.append("")
        if func.doc.tutorials:
            tuts = " • ".join(f"[{t.title}]({t.url})" if t.title else f"<{t.url}>" for t in func.doc.tutorials)
            lines.append(f"**Tutorials:** {tuts}")
            lines.append("")
        if func.doc.markdown:
            desc_to_use = desc_md or (func.doc.markdown if func.doc and func.doc.markdown else None)
            if desc_to_use:
                lines.append("## Description")
                lines.append("")
                lines.append(desc_to_use)
                lines.append("")

    if func.source_code:
        lines.append("## Source")
        lines.append("")
        lines.append("```gdscript")
        lines.append(func.source_code.rstrip())
        lines.append("```")
        lines.append("")

    if references_md_lines:
        lines.append("## References")
        lines.append("")
        lines.extend(references_md_lines)
        if references_md_lines and references_md_lines[-1] != "":
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
