from __future__ import annotations
import re

# GDScript declaration patterns (approximate but fast).
FUNC_RE = re.compile(r"^\s*(?:static\s+)?func\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:->\s*([^:]+))?\s*:")
VAR_RE = re.compile(r"^\s*(?:@[^\n]*?\s+)*var\s+([A-Za-z_]\w*)(?:\s*:\s*([^=]+?))?(?:\s*=|\s*$)")
CONST_RE = re.compile(r"^\s*const\s+([A-Za-z_]\w*)(?:\s*:\s*([^=]+?))?\s*=")
SIGNAL_RE = re.compile(r"^\s*signal\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?")
ENUM_RE = re.compile(r"^\s*enum(?:\s+([A-Za-z_]\w*))?\s*(?:\{.*?\})?\s*$")
CLASS_NAME_RE = re.compile(r"^\s*class_name\s+([A-Za-z_]\w*)")
EXTENDS_RE = re.compile(r"^\s*extends\s+(.+)$")
DECORATOR_LINE_RE = re.compile(r"^\s*@[\w\(\)\.,\s:\"']+$")
DOC_LINE_RE = re.compile(r"^\s*##(.*)$")
PARAM_SOL_RE = re.compile(r"^\s*\[param\s+([^\]]+)\]\s*(.*)$")
RETURN_SOL_RE = re.compile(r"^\s*\[return\]\s*(.*)$")
DECORATOR_KEYWORDS_RE = re.compile(r"\b(?:var|const|signal|func|enum)\b")
INLINE_DECOS_BEFORE_VAR = re.compile(r"(@[^\s]+(?:\([^)]*\))?)\s+(?=var\b)")

# Reference tags inside doc text
REF_TAG_RE = re.compile(
    r"\[(method|member|signal|constant|enum|class|Class|annotation|constructor|operator|theme_item)\s+([^\]]+)\]"
)
