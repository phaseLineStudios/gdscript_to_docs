from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Iterable
import re, sys
import os

# =========================================
# BBCode → Markdown helpers
# =========================================

_CODE_INLINE_MAX = 80

def _code_repl(s: str) -> str:
    s_stripped = s.strip("\n")
    if "\n" in s_stripped or len(s_stripped) > _CODE_INLINE_MAX:
        return f"\n```\n{s_stripped}\n```\n"
    # insert a real zero-width space before any backtick inside inline code
    return f"`{s_stripped.replace('`', '\u200b`')}`"

def bbcode_to_markdown(text: str) -> str:
    t = text.replace("\r\n", "\n")
    t = re.sub(r"\[codeblock\](.*?)\[/codeblock\]", lambda m: f"\n```\n{m.group(1).strip()}\n```\n", t, flags=re.S)
    t = re.sub(r"\[code\](.*?)\[/code\]", lambda m: _code_repl(m.group(1)), t, flags=re.S)
    for pat, rep in [(r"\[b\](.*?)\[/b\]", r"**\1**"), (r"\[i\](.*?)\[/i\]", r"*\1*"), (r"\[u\](.*?)\[/u\]", r"__\1__")]:
        t = re.sub(pat, rep, t, flags=re.S)
    t = re.sub(r"\[url\](.*?)\[/url\]", r"<\1>", t, flags=re.S)
    t = re.sub(r"\[url=(.*?)\](.*?)\[/url\]", r"[\2](\1)", t, flags=re.S)
    t = re.sub(r"\[img\](.*?)\[/img\]", r"![image](\1)", t, flags=re.S)
    t = re.sub(r"\[center\](.*?)\[/center\]", r"\1", t, flags=re.S)
    t = re.sub(r"\[color=[^\]]+\](.*?)\[/color\]", r"\1", t, flags=re.S)
    t = re.sub(r"\[font=[^\]]+\](.*?)\[/font\]", r"\1", t, flags=re.S)
    # Transforms Godot refs for display; linking is handled separately using the 'raw' text
    t = re.sub(r"\[(method|member|signal|constant|enum|class)\s+([^\]]+)\]", r"`\1 \2`", t)
    t = t.replace("[br]", "  \n")
    return t.strip()

# =========================================
# Data structures
# =========================================

@dataclass
class TutorialLink:
    title: Optional[str]
    url: str

@dataclass
class DocBlock:
    raw: str
    markdown: str
    deprecated: bool=False
    experimental: bool=False
    tutorials: List[TutorialLink] = field(default_factory=list)

@dataclass
class MemberDoc:
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
    path: Path
    class_name: Optional[str]
    extends: Optional[str]
    script_doc: Optional[DocBlock]
    members: List[MemberDoc]=field(default_factory=list)

# For reference extraction and linking
@dataclass
class ParsedReference:
    kind: str                  # method|member|signal|constant|enum|class
    raw_target: str            # as in the tag, e.g., 'CharacterBody2D.move_and_slide' or 'move_and_slide'
    cls: Optional[str]         # parsed class part (if any)
    member: Optional[str]      # parsed member part (if any)

@dataclass
class ClassIndexEntry:
    title: str                               # class_name or file stem
    class_page_rel: Path                     # Path relative to output root
    functions_dir_rel: Optional[Path]        # e.g., ClassName/functions
    members_by_kind: Dict[str, set]          # kind -> {names}
    function_pages_rel: Dict[str, Path]      # name -> relative path to per-function file (if split)

# =========================================
# Regexes
# =========================================

FUNC_RE = re.compile(r"^\s*(?:static\s+)?func\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:->\s*([^:]+))?\s*:")
VAR_RE  = re.compile(r"^\s*(?:@[\w\(\)\.,\s:\"']+\s+)*var\s+([A-Za-z_]\w*)(?:\s*:\s*([^=]+?))?(?:\s*=|\s*$)")
CONST_RE = re.compile(r"^\s*const\s+([A-Za-z_]\w*)(?:\s*:\s*([^=]+?))?\s*=")
SIGNAL_RE = re.compile(r"^\s*signal\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?")
ENUM_RE = re.compile(r"^\s*enum(?:\s+([A-Za-z_]\w*))?\s*(?:\{.*?\})?\s*$")
CLASS_NAME_RE = re.compile(r"^\s*class_name\s+([A-Za-z_]\w*)")
EXTENDS_RE = re.compile(r"^\s*extends\s+(.+)$")
DECORATOR_LINE_RE = re.compile(r"^\s*@[\w\(\)\.,\s:\"']+$")
DOC_LINE_RE = re.compile(r"^\s*##(.*)$")

# =========================================
# Internal helpers
# =========================================

def _collect_docblock(lines: List[str], start_i: int) -> tuple[DocBlock, int]:
    buff: List[str] = []
    i = start_i
    while i < len(lines):
        m = DOC_LINE_RE.match(lines[i])
        if not m: break
        buff.append(m.group(1).lstrip())
        i += 1
    deprecated = any("@deprecated" in ln for ln in buff)
    experimental = any("@experimental" in ln for ln in buff)
    tuts: List[TutorialLink] = []
    tut_re = re.compile(r"@tutorial(?:\((.*?)\))?:\s*(\S+)")
    for ln in buff:
        for tm in tut_re.finditer(ln):
            tuts.append(TutorialLink(title=tm.group(1), url=tm.group(2)))
    cleaned = "\n".join(ln for ln in buff if not ln.strip().startswith(("@tutorial","@deprecated","@experimental"))).rstrip()
    db = DocBlock(
        raw=cleaned,
        markdown=bbcode_to_markdown(cleaned),
        deprecated=deprecated,
        experimental=experimental,
        tutorials=tuts,
    )
    return db, i

def _split_brief_details(md: str) -> tuple[str, str]:
    s = (md or "").strip()
    if not s:
        return "", ""
    m = re.match(r"(?s)\s*(.*?[\.\!\?])(\s+.*)?$", s)
    if m:
        brief = m.group(1).strip()
        rest = (m.group(2) or "").strip()
        return brief, rest
    parts = s.splitlines()
    return parts[0].strip(), "\n".join(parts[1:]).strip()

def _inline_sig(m: MemberDoc) -> str:
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

def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", s).strip("-")

def _anchor_id(s: str) -> str:
    # Conservative GitHub-like anchor
    s = s.strip().lower()
    s = re.sub(r"[^\w\- ]+", "", s)   # keep word chars, dash, space, underscore
    s = s.replace(" ", "-")
    return s

def _indent_level(line: str) -> int:
    i = 0
    while i < len(line) and line[i] in (" ", "\t"):
        i += 1
    return i

def _capture_function_block(lines: List[str], func_start_idx: int) -> tuple[int, str]:
    start = func_start_idx
    func_line = lines[start]
    base_indent = _indent_level(func_line)
    end = start + 1
    while end < len(lines):
        ln = lines[end]
        if ln.strip() == "":
            end += 1
            continue
        if _indent_level(ln) <= base_indent:
            break
        end += 1
    code = "\n".join(lines[start:end]).rstrip() + "\n"
    return end, code

# =========================================
# Reference extraction
# =========================================

REF_TAG_RE = re.compile(r"\[(method|member|signal|constant|enum|class)\s+([^\]]+)\]")

def extract_references_from_text(text_with_bbcode: str, default_class: Optional[str]) -> List[ParsedReference]:
    refs: List[ParsedReference] = []
    for kind, target in REF_TAG_RE.findall(text_with_bbcode or ""):
        target = target.strip()
        cls = None
        member = None
        if "." in target:
            parts = target.split(".", 1)
            cls = parts[0].strip() or None
            member = parts[1].strip() or None
        else:
            # If no class provided, assume current class for members/methods/etc.
            cls = default_class if kind != "class" else target
            member = None if kind == "class" else target
        refs.append(ParsedReference(kind=kind, raw_target=target, cls=cls, member=member))
    return refs

# =========================================
# Rendering
# =========================================

def _render_script_markdown_classic(doc: ScriptDoc, project_root: Path) -> str:
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

    # Synopsis
    lines += ["## Synopsis", ""]
    syn = ["```gdscript"]
    if doc.class_name: syn.append(f"class_name {doc.class_name}")
    if doc.extends: syn.append(f"extends {doc.extends}")
    syn.append("```")
    lines += syn + [""]

    # Brief / Detailed
    brief, details = ("", "")
    if doc.script_doc and doc.script_doc.markdown:
        brief, details = _split_brief_details(doc.script_doc.markdown)
    if brief:
        lines += ["## Brief", "", brief, ""]
    if details:
        lines += ["## Detailed Description", "", details, ""]
    elif doc.script_doc and not brief:
        lines += ["## Detailed Description", "", doc.script_doc.markdown, ""]
    if doc.script_doc and doc.script_doc.tutorials:
        tuts = " • ".join(f"[{t.title}]({t.url})" if t.title else f"<{t.url}>" for t in doc.script_doc.tutorials)
        lines += [f"**Tutorials:** {tuts}", ""]

    # Summary sections
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
                    mfile = f"{link_functions_dir}/{_slug(m.name)}.md"
                    bullet = f"- [{_inline_sig(m)}]({mfile})"
                if m.doc and m.doc.markdown:
                    b, _ = _split_brief_details(m.doc.markdown)
                    if b:
                        flags = []
                        if m.doc.deprecated: flags.append("**Deprecated**")
                        if m.doc.experimental: flags.append("**Experimental**")
                        bullet += f" — {b}" + (f" {' '.join(flags)}" if flags else "")
                lines.append(bullet)
            lines.append("")
    else:
        lines.append("_No members found._")

    # Detailed sections
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
    references_md_lines: Optional[List[str]] = None
) -> str:
    """Render a single function page in Doxygen-like style."""
    title = doc.class_name or doc.path.stem
    rel = doc.path.relative_to(project_root) if hasattr(Path, "is_relative_to") and doc.path.is_relative_to(project_root) else doc.path

    header = f"{title}::{func.name}"
    lines = [f"# {header} Function Reference", ""]

    if func.source_start_line and func.source_end_line:
        lines.append(f"*Defined at:* `{rel.as_posix()}` (lines {func.source_start_line}–{func.source_end_line})</br>")
    else:
        lines.append(f"*File:* `{rel.as_posix()}`")
    lines.append(f"*Belongs to:* [{title}](../{title}.md)")
    lines.append("")

    lines += ["**Signature**", "", "```gdscript", func.signature or f"func {func.name}()", "```", ""]

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
            lines.append("## Description")
            lines.append("")
            lines.append(func.doc.markdown)
            lines.append("")
            
    if func.source_code:
        lines.append("## Source")
        lines.append("")
        lines.append("```gdscript")
        lines.append(func.source_code.rstrip())
        lines.append("```")
        lines.append("")

    # New: References section (if any)
    if references_md_lines:
        lines.append("## References")
        lines.append("")
        lines.extend(references_md_lines)
        if references_md_lines and references_md_lines[-1] != "":
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"

# =========================================
# Parser
# =========================================

def parse_gd_script(path: Path) -> ScriptDoc:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    class_name = None
    extends = None
    for ln in lines:
        if (m := CLASS_NAME_RE.match(ln)):
            class_name = m.group(1)
        if extends is None and (m2 := EXTENDS_RE.match(ln)):
            extends = m2.group(1).strip()
    i = 0
    script_doc = None
    members: List[MemberDoc] = []

    while i < len(lines):
        line = lines[i]
        if DOC_LINE_RE.match(line):
            db, j = _collect_docblock(lines, i)
            k = j
            decorators: List[str] = []
            while k < len(lines) and (not lines[k].strip() or DECORATOR_LINE_RE.match(lines[k])):
                if DECORATOR_LINE_RE.match(lines[k]):
                    decorators.append(lines[k].strip())
                k += 1
            target = lines[k] if k < len(lines) else ""
            if m := FUNC_RE.match(target):
                name = m.group(1)
                args = m.group(2).strip()
                ret = (m.group(3) or "").strip()
                sig = f"func {name}({args})" + (f" -> {ret}" if ret else "")
                end_excl, code = _capture_function_block(lines, k)
                start_line = k + 1
                end_line = end_excl
                members.append(MemberDoc(
                    kind="func", name=name, signature=sig,
                    decorators=decorators, doc=db,
                    source_start_line=start_line, source_end_line=end_line, source_code=code
                ))
                # jump past function definition to avoid duplicate
                i = end_excl
                continue
            elif m := VAR_RE.match(target):
                name = m.group(1); typ = (m.group(2) or "").strip() or None
                members.append(MemberDoc(kind="var", name=name, type_hint=typ, decorators=decorators, doc=db))
                i = k + 1
                continue
            elif m := CONST_RE.match(target):
                name = m.group(1); typ = (m.group(2) or "").strip() or None
                members.append(MemberDoc(kind="const", name=name, type_hint=typ, decorators=decorators, doc=db))
                i = k + 1
                continue
            elif m := SIGNAL_RE.match(target):
                name = m.group(1); args = (m.group(2) or "").strip()
                sig = f"signal {name}({args})" if args else f"signal {name}"
                members.append(MemberDoc(kind="signal", name=name, signature=sig, decorators=decorators, doc=db))
                i = k + 1
                continue
            elif m := ENUM_RE.match(target):
                name = (m.group(1) or "").strip() or "<anonymous>"
                members.append(MemberDoc(kind="enum", name=name, decorators=decorators, doc=db))
                i = k + 1
                continue
            # orphan script-level doc
            if script_doc is None:
                script_doc = db
            else:
                script_doc.markdown += "\n\n" + db.markdown
            i = j
            continue

        if m := FUNC_RE.match(line):
            name = m.group(1); args = m.group(2).strip(); ret = (m.group(3) or "").strip()
            sig = f"func {name}({args})" + (f" -> {ret}" if ret else "")
            end_excl, code = _capture_function_block(lines, i)
            members.append(MemberDoc(
                kind="func", name=name, signature=sig,
                source_start_line=i+1, source_end_line=end_excl, source_code=code
            ))
            i = end_excl
            continue
        elif m := VAR_RE.match(line):
            name = m.group(1); typ = (m.group(2) or "").strip() or None
            members.append(MemberDoc(kind="var", name=name, type_hint=typ))
        elif m := CONST_RE.match(line):
            name = m.group(1); typ = (m.group(2) or "").strip() or None
            members.append(MemberDoc(kind="const", name=name, type_hint=typ))
        elif m := SIGNAL_RE.match(line):
            name = m.group(1); args = (m.group(2) or "").strip()
            sig = f"signal {name}({args})" if args else f"signal {name}"
            members.append(MemberDoc(kind="signal", name=name, signature=sig))
        elif m := ENUM_RE.match(line):
            name = (m.group(1) or "").strip() or "<anonymous>"
            members.append(MemberDoc(kind="enum", name=name))
        i += 1

    # De-duplicate members by (kind, name, start_line)
    seen = set()
    deduped: List[MemberDoc] = []
    for m in members:
        key = (m.kind, m.name, m.source_start_line or -1)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(m)
    return ScriptDoc(path=path, class_name=class_name, extends=extends, script_doc=script_doc, members=deduped)

# =========================================
# Indexing and linking
# =========================================

def _build_index_for_docs(
    docs: List[ScriptDoc],
    out_root: Path,
    src_root: Path,
    keep_structure: bool,
    split_functions: bool
) -> Dict[str, ClassIndexEntry]:
    """
    Build an index of classes by 'title' (class_name or file stem).
    Maps both the class_name (if any) and the file stem to the same entry.
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
                function_pages_rel[m.name] = (target_dir / class_basename / "functions" / f"{_slug(m.name)}.md").relative_to(out_root)

        entry = ClassIndexEntry(
            title=class_basename,
            class_page_rel=class_page_rel,
            functions_dir_rel=functions_dir_rel,
            members_by_kind=members_by_kind,
            function_pages_rel=function_pages_rel
        )

        # Map by class name and by file stem (so links work even if no class_name)
        keys = [class_basename]
        if d.class_name and d.class_name != class_basename:
            keys.append(d.class_name)
        if p.stem not in keys:
            keys.append(p.stem)

        for k in keys:
            if k not in index:
                index[k] = entry
            # prefer explicit class_name key if collisions happen; leave first insertion
    return index

def _compute_reference_links_for_function(
    func_doc_raw: str,
    current_class_title: str,
    current_file_rel: Path,
    index: Dict[str, ClassIndexEntry],
    split_functions: bool
) -> List[str]:
    """
    Returns markdown bullet list lines linking to referenced objects found in func_doc_raw.
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

        if r.kind == "class":
            # link to class page if we know it
            cls_name = r.cls or r.raw_target
            entry = index.get(cls_name)
            if entry:
                href = os.path.relpath((Path() / entry.class_page_rel).as_posix(), start=(Path() / current_file_rel).parent.as_posix())
        else:
            # member kinds
            cls_name = r.cls or current_class_title
            entry = index.get(cls_name)
            if entry:
                if r.kind == "method":
                    if split_functions and r.member and r.member in entry.function_pages_rel:
                        target = entry.function_pages_rel[r.member]
                        href = os.path.relpath((Path() / target).as_posix(), start=(Path() / current_file_rel).parent.as_posix())
                    else:
                        anchor = _anchor_id(r.member or "")
                        href = os.path.relpath((Path() / entry.class_page_rel).as_posix(), start=(Path() / current_file_rel).parent.as_posix())
                        href = f"{href}#{anchor}"
                else:
                    # member, signal, constant, enum -> link to class page with anchor to '### name'
                    anchor = _anchor_id(r.member or "")
                    href = os.path.relpath((Path() / entry.class_page_rel).as_posix(), start=(Path() / current_file_rel).parent.as_posix())
                    href = f"{href}#{anchor}"

        if href:
            bullet = f"- [{label}]({href})"
        else:
            bullet = f"- {label}"

        key = (label, href or "")
        if key not in seen:
            seen.add(key)
            bullets.append(bullet)

    return bullets

# =========================================
# High-level write
# =========================================

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
    src = src.resolve()
    out.mkdir(parents=True, exist_ok=True)

    scripts = sorted(src.glob(glob))
    if not scripts:
        print(f"No .gd files found under: {src}", file=sys.stderr)
        return

    # Pass 1: parse all
    docs: List[ScriptDoc] = [parse_gd_script(p) for p in scripts]

    # Build index (paths relative to out root)
    class_index = _build_index_for_docs(
        docs=docs, out_root=out, src_root=src,
        keep_structure=keep_structure, split_functions=split_functions
    )

    # Pass 2: render & write
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
        # Render the class page
        md = render_script_markdown(d, project_root=src, style=style, link_functions_dir=link_dir)
        rendered.append((d, md, class_md_path))
        class_page_paths[class_basename] = class_md_path

        # Per-function pages (with References)
        if split_functions:
            for m in d.members:
                if m.kind != "func":
                    continue
                fpath = (target_dir / class_basename / "functions" / f"{_slug(m.name)}.md")
                # Compute reference links from the docblock 'raw' text (BBCode form)
                raw = m.doc.raw if (m.doc and m.doc.raw) else ""
                current_file_rel = fpath.relative_to(out)
                refs_md = _compute_reference_links_for_function(
                    func_doc_raw=raw,
                    current_class_title=class_basename,
                    current_file_rel=current_file_rel,
                    index=class_index,
                    split_functions=split_functions,
                )
                fmd = render_function_markdown(d, m, project_root=src, style=style, references_md_lines=refs_md)
                fpath.write_text(fmd, encoding="utf-8")

    # Write class pages (or bundle)
    if single_file:
        bundle = ["# Project Documentation", ""]
        for _, md, _ in rendered:
            bundle.append(md); bundle.append("\n---\n")
        (out / "DOCUMENTATION.md").write_text("\n".join(bundle).rstrip() + "\n", encoding="utf-8")
    else:
        for _, md, path in rendered:
            path.write_text(md, encoding="utf-8")

    # Index
    if make_index and not single_file:
        index_lines = ["# Index", ""]
        for d, _, path in rendered:
            rel = path.relative_to(out)
            index_lines.append(f"- [{d.class_name or d.path.stem}]({rel.as_posix()})")
            if split_functions:
                class_basename = d.class_name or d.path.stem
                func_root = out / rel.parent / class_basename / "functions"
                if func_root.exists():
                    for m in [m for m in d.members if m.kind == "func"]:
                        f = func_root / f"{_slug(m.name)}.md"
                        if f.exists():
                            index_lines.append(f"  - [{m.name}]({(rel.parent / class_basename / 'functions' / f.name).as_posix()})")
        (out / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
