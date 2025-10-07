import re
from gdscript_to_docs.bbcode import bbcode_to_markdown

def test_bbcode_basic():
    src = "[b]bold[/b] [i]it[/i] [u]u[/u] [url=https://x.y]z[/url] [br] line2"
    md = bbcode_to_markdown(src)
    assert "**bold**" in md
    assert "*it*" in md
    assert "__u__" in md
    assert "[z](https://x.y)" in md
    assert "  \n" in md  # markdown line break

def test_bbcode_code_and_blocks():
    inline = bbcode_to_markdown("[code]print('hi')[/code]")
    assert inline.startswith("`") and inline.endswith("`")
    block = bbcode_to_markdown("[codeblock]\nline1\nline2\n[/codeblock]")
    assert "```" in block and "line1" in block and "line2" in block

def test_godot_refs_and_img():
    s = "See [method CharacterBody2D.move_and_slide] and [img]https://img[/img]"
    md = bbcode_to_markdown(s)
    assert "`method CharacterBody2D.move_and_slide`" in md
    assert "![image](https://img)" in md

def test_inline_code_backtick_is_escaped():
    s = bbcode_to_markdown("[code]a`b[/code]")
    assert "\u200b`" in s
