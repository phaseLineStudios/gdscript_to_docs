from __future__ import annotations
import re

_CODE_INLINE_MAX = 80 # Inline code max length before promoted to fenced block.

def _code_repl(s: str) -> str:
    """Render a BBCode inline/code block snippet as Markdown.

    Inserts a zero-width space before backticks inside inline code to prevent
    premature closing. Promotes multi-line or long content to a fenced block.

    Args:
        s: Raw code snippet content from a [code] tag.

    Returns:
        Markdown string for inline code or a fenced code block.
    """
    s_stripped = s.strip("\n")
    if "\n" in s_stripped or len(s_stripped) > _CODE_INLINE_MAX:
        return f"\n```\n{s_stripped}\n```\n"
    return f"`{s_stripped.replace('`', '\u200b`')}`"

def bbcode_to_markdown(text: str) -> str:
    """Convert a subset of Godot BBCode to Markdown.

    Supported tags include [code], [codeblock], [b], [i], [u], [url], [img],
    [center], [color], [font], and Godot reference tags like
    [method Foo.bar]. Line breaks via [br] are preserved.

    Args:
        text: Input string with BBCode markup.

    Returns:
        Markdown string with inline formatting and code blocks converted.
    """
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
    t = re.sub(
        r"\[(method|member|signal|constant|enum|class|Class|annotation|constructor|operator|theme_item)\s+([^\]]+)\]",
        lambda m: f"`{m.group(1).lower()} {m.group(2)}`",
        t,
    )
    t = re.sub(r"\[param\s+([^\]]+)\]", r"`\1`", t)
    t = t.replace("[br]", "  \n")
    return t.strip()
