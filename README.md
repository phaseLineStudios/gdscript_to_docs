# gdscript_to_docs

[![CI](https://github.com/phaseLineStudios/gdscript_to_docs/actions/workflows/ci.yml/badge.svg)](https://github.com/phaseLineStudios/gdscript_to_docs/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/gdscript-to-docs.svg)](https://pypi.org/project/gdscript-to-docs/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#license)

Export **Godot 4.x GDScript documentation comments** (`##` blocks) into clean Markdown, Doxygen-style class pages, and optional **per-function** pages — with **BBCode → Markdown** conversion and **cross-links** to referenced classes/methods/signals.

- Parses `##` doc comments placed right above the member (as per Godot docs)
- Recognizes `func`, `var`, `const`, `signal`, `enum`
- Converts BBCode (`[b]`, `[i]`, `[code]`, `[codeblock]`, `[url]`, `[img]`, `[br]`, etc.)
- Renders **Doxygen-like** class pages (Synopsis, Brief, Detailed, member summaries + detailed sections)
- `--split-functions` emits **one Markdown file per function** with full source, file/line range, and a **References** section that links `[method Class.name]`, `[class Class]`, `[signal Class.sig]`, etc.
- Optional classic list style via `--style classic`
- Optional index `INDEX.md` and single-file bundle `DOCUMENTATION.md`

> Compatible with Windows, macOS, and Linux. Tested on Python 3.9–3.13.

---

## Install

```bash
# From PyPI
pip install gdscript-to-docs

# Latest from source (editable)
pip install -e .
```

## Quick Start
From your Godot project root (or any folder containing `.gd` files):
```bash
gdscript_to_docs path/to/project \
  --out docs/ \
  --make-index \
  --split-functions
```

Windows example (be sure to quote paths with spaces / backslashes):
```powershell
gdscript_to_docs "E:\Godot Projects\MyGame\src" --out ".\docs" --keep-structure --make-index --split-functions
```

This generates:
```bash
docs/
├── INDEX.md
├── Player.md                     # Class page (Doxygen-style)
└── Player/
    └── functions/
        ├── move.md               # Per-function page
        └── jump.md
```

## CLI
```bash
usage: gdscript_to_docs [-h] [--out OUT] [--keep-structure] [--single-file]
                        [--make-index] [--glob GLOB]
                        [--style {doxygen,classic}] [--split-functions]
                        src

Export Godot GDScript documentation comments to Markdown.

positional arguments:
  src                   Project root (or any folder) to scan for .gd files

options:
  -h, --help            show this help message and exit
  --out OUT             Output directory (default: docs_godot)
  --keep-structure      Mirror source folder structure under output
  --single-file         Write a single DOCUMENTATION.md instead of per-script files
  --make-index          Generate an INDEX.md linking all generated files
  --glob GLOB           Glob pattern for .gd scripts (default: **/*.gd)
  --style {doxygen,classic}
                        Markdown style (default: doxygen)
  --split-functions     Also generate separate Markdown files for each function
```

## Output style
### Doxygen-style class pages (default)
- # ClassName Class Reference
- **Synopsis** with `class_name` and `extends`
- **Brief** and **Detailed Description**
- **Public Member Functions/Attributes/Constants/Signals/Enumerations** summaries
- Detailed sections (e.g. **Member Function Documentation**)

### Per-function pages (--split-functions)
- Title: `ClassName::method Function Reference`
- **Defined at**: `<file>` with line range
- **Signature** (code block)
- **Decorators** (e.g. @export)
- **Description** (from the ## docblock)
- **Source**: full function body (code block)
- **References**: links generated from doc tags like:
  - `[method Class.foo]` → either the per-function page (if split) or class page + anchor
  - `[class Foo]` → class page
  - `[signal Class.sig]`, `[member Class.var]`, `[constant Class.NAME]`, `[enum Class.Enum]` → class page + anchor

If a target isn’t found in the generated docs, it’s rendered as plain text to avoid broken links.

## BBCode → Markdown
**Supported**: [b], [i], [u], [code], [codeblock], [url], [img], [br], plus Godot doc refs:<br/>
[method …], [member …], [signal …], [constant …], [enum …], [class …].

Example:
```gdscript
## Moves the player.
## [b]Use with care[/b]. [method CharacterBody2D.move_and_slide]
func move(delta: float) -> void:
    pass
```

Renders to:
- Summary bullet: `func move(delta: float) -> void — Use with care.`
- Function page includes the doc text and a References link to `CharacterBody2D::move_and_slide`.

## Index & single-file bundle
- `--make-index` writes an `INDEX.md` that lists class pages and, if split, function pages beneath each class.
- `--single-file` writes a `DOCUMENTATION.md` that concatenates all class pages (helpful for quick review or importing into docs tools).

## Known limitations / roadmap
- Multi-line function signatures aren’t yet parsed; signatures are expected on a single line.
- Links to external Godot classes (i.e., not in your project) are rendered as plain labels; you can map those to the online docs in a future --godot-api-links option.
- Anchors for members use a conservative GitHub-style ID; if you post-process headers, anchors may change.

Want any of the above? Please open an issue or a PR—contributions welcome!

## Development
```bash
# Clone and install in editable mode
git clone https://github.com/<YOUR_GH_USER>/<YOUR_REPO>.git
cd <YOUR_REPO>
pip install -e .[dev]

# Run tests
pytest -q --cov --cov-report=term-missing:skip-covered

# Build
python -m pip install build
python -m build  # dist/*.whl and dist/*.tar.gz
```

## License
MIT © Phase Line Studios