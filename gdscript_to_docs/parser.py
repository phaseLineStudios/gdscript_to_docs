from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from .models import DocBlock, MemberDoc, ScriptDoc, TutorialLink
from .regexes import (
    CLASS_NAME_RE, CONST_RE, DECORATOR_LINE_RE, DOC_LINE_RE, ENUM_RE, EXTENDS_RE,
    FUNC_RE, SIGNAL_RE, VAR_RE
)
from .utils import capture_function_block
from .bbcode import bbcode_to_markdown
import re

def _collect_docblock(lines: List[str], start_i: int) -> tuple[DocBlock, int]:
    """Collect a contiguous block of ``##`` lines starting at ``start_i``.

    Recognizes ``@deprecated``, ``@experimental``, and ``@tutorial(title?): url``.

    Args:
        lines: File lines.
        start_i: Index where a ``##`` doc line is known to exist.

    Returns:
        (DocBlock, next_index) where ``next_index`` is the first line after the
        consumed docblock.
    """
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

def parse_gd_script(path: Path) -> ScriptDoc:
    """Parse a single .gd file and extract documentation and members.

    This is a lightweight, line-oriented parser tuned for common Godot 4
    idioms. It collects contiguous ``##`` lines as docblocks and associates
    them with the next declaration (function, var, const, signal, enum).

    Args:
        path: Path to the GDScript file.

    Returns:
        :class:`ScriptDoc` with script-level doc (if any) and member list.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    class_name: Optional[str] = None
    extends: Optional[str] = None
    for ln in lines:
        if (m := CLASS_NAME_RE.match(ln)):
            class_name = m.group(1)
        if extends is None and (m2 := EXTENDS_RE.match(ln)):
            extends = m2.group(1).strip()
    i = 0
    script_doc: Optional[DocBlock] = None
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
                end_excl, code = capture_function_block(lines, k)
                start_line = k + 1
                end_line = end_excl
                members.append(MemberDoc(
                    kind="func", name=name, signature=sig,
                    decorators=decorators, doc=db,
                    source_start_line=start_line, source_end_line=end_line, source_code=code
                ))
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

            if script_doc is None:
                script_doc = db
            else:
                script_doc.markdown += "\n\n" + db.markdown
            i = j
            continue

        if m := FUNC_RE.match(line):
            name = m.group(1); args = m.group(2).strip(); ret = (m.group(3) or "").strip()
            sig = f"func {name}({args})" + (f" -> {ret}" if ret else "")
            end_excl, code = capture_function_block(lines, i)
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

    seen = set()
    deduped: List[MemberDoc] = []
    for m in members:
        key = (m.kind, m.name, m.source_start_line or -1)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(m)
    return ScriptDoc(path=path, class_name=class_name, extends=extends, script_doc=script_doc, members=deduped)
