import argparse
from pathlib import Path
from .writer import write_docs

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Export Godot GDScript documentation comments to Markdown."
    )
    ap.add_argument("src", type=Path, help="Project root (or any folder) to scan for .gd files")
    ap.add_argument("--out", type=Path, default=Path("docs_godot"), help="Output directory")
    ap.add_argument("--keep-structure", action="store_true", help="Mirror source folder structure under output")
    ap.add_argument("--single-file", action="store_true", help="Write a single DOCUMENTATION.md instead of per-script files")
    ap.add_argument("--make-index", action="store_true", help="Generate an INDEX.md linking all generated files")
    ap.add_argument("--glob", default="**/*.gd", help="Glob pattern for .gd scripts (default: **/*.gd)")
    ap.add_argument("--style", choices=["doxygen", "classic"], default="doxygen", help="Markdown style (default: doxygen)")
    ap.add_argument("--split-functions", action="store_true", help="Also generate separate Markdown files for each function")
    args = ap.parse_args(argv)

    write_docs(
        src=args.src,
        out=args.out,
        keep_structure=args.keep_structure,
        single_file=args.single_file,
        make_index=args.make_index,
        glob=args.glob,
        style=args.style,
        split_functions=args.split_functions,
    )
