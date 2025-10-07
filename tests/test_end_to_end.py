from pathlib import Path
from gdscript_to_docs.writer import write_docs

SAMPLE_GD = """\
## Player controller
## @tutorial(Guide): https://example.com/guide
## @experimental
class_name Player
extends CharacterBody2D

## Player speed
@export
var speed: float = 100.0

## Moves the player.
## [b]Use with care[/b]. [method CharacterBody2D.move_and_slide]
func move(delta: float) -> void:
    pass

signal jumped(height)

## Type of state
enum State { IDLE, RUN }

const GRAVITY: float = 400.0
"""

def test_write_docs_generates_markdown(tmp_path: Path):
    project = tmp_path / "proj"
    src = project / "scripts"
    out = tmp_path / "docs"
    src.mkdir(parents=True)
    (src / "player.gd").write_text(SAMPLE_GD, encoding="utf-8")

    write_docs(src=project, out=out, keep_structure=False, single_file=False, make_index=True, glob="**/*.gd")

    md_file = out / "Player.md"
    assert md_file.exists()
    text = md_file.read_text(encoding="utf-8")

    assert text.startswith("# Player Class Reference")
    assert "## Synopsis" in text and "class_name Player" in text and "extends CharacterBody2D" in text
    assert "## Brief" in text and "Player controller" in text
    assert "## Public Member Functions" in text
    assert "## Public Attributes" in text and "`float speed`" in text
    assert "## Public Constants" in text and "`const GRAVITY: float`" in text
    assert "## Signals" in text and "`signal jumped(height)`" in text
    assert "## Member Function Documentation" in text and "### move" in text
    assert "**Use with care**" in text and "`method CharacterBody2D.move_and_slide`" in text
    assert "## Member Data Documentation" in text and "### speed" in text and "Decorators: `@export`" in text

    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "[Player](Player.md)" in index

def test_single_file_mode(tmp_path: Path):
    project = tmp_path / "p"
    out = tmp_path / "d"
    project.mkdir()
    (project / "a.gd").write_text("## Doc\nclass_name A\n", encoding="utf-8")

    write_docs(src=project, out=out, single_file=True, make_index=False)
    doc = (out / "DOCUMENTATION.md")
    assert doc.exists()
    assert "# Project Documentation" in doc.read_text(encoding="utf-8")
