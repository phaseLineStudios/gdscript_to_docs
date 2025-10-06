from pathlib import Path
from gdscript_to_docs.cli import main

def test_cli_runs_and_creates_files(tmp_path: Path):
    proj = tmp_path / "g"
    out = tmp_path / "docs"
    proj.mkdir()
    (proj / "thing.gd").write_text("## T\nclass_name Thing\n", encoding="utf-8")

    main([str(proj), "--out", str(out), "--make-index"])

    assert (out / "Thing.md").exists()
    assert (out / "INDEX.md").exists()
