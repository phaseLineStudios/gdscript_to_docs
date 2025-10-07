from pathlib import Path
from gdscript_to_docs.writer import write_docs

SRC = """\
## Doc.
class_name Demo
extends Node

## Adds two numbers.
func add(a: int, b: int) -> int:
    var c = a + b
    return c

## Empty body style still valid.
func noop() -> void:
    pass
"""

def test_function_page_has_source_and_location(tmp_path: Path):
    proj = tmp_path / "proj"; proj.mkdir()
    (proj / "demo.gd").write_text(SRC, encoding="utf-8")
    out = tmp_path / "docs"

    write_docs(src=proj, out=out, split_functions=True)

    f_add = out / "Demo" / "functions" / "add.md"
    assert f_add.exists()
    txt = f_add.read_text(encoding="utf-8")

    assert "*Defined at:* `demo.gd`" in txt or "*Defined at:* `proj/demo.gd`" in txt or "Defined at:* `demo.gd`" in txt
    assert "lines " in txt
    assert "**Signature**" in txt
    assert "func add(a: int, b: int) -> int" in txt
    assert "## Source" in txt
    assert "var c = a + b" in txt
    assert "return c" in txt

    f_noop = out / "Demo" / "functions" / "noop.md"
    assert f_noop.exists()
    t2 = f_noop.read_text(encoding="utf-8")
    assert "func noop() -> void" in t2
    assert "pass" in t2
