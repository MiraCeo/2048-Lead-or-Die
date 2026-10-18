"""Dump specific lines of src/main.script.js plus every neutral-group reference.

Step 1 deletes the whole-group capture mechanic, so we need the exact text of each
touch point before editing minified source.
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _root import PATHS

ROOT = PATHS.ROOT
SRC = ROOT / 'src' / 'main.script.js'
OUT = ROOT / 'build' / 'reports' / 'step1_lines.txt'

lines = SRC.read_text(encoding='utf-8').split('\n')
out = []


def section(title):
    out.append('')
    out.append('=' * 100)
    out.append(title)
    out.append('=' * 100)


section('A. every line referencing the neutral-group mechanic')
for i, ln in enumerate(lines, 1):
    if re.search(r'neutralGroups|\bng\b|\.ng|ng:', ln):
        hits = len(re.findall(r'neutralGroups|\.ng\b|ng:|\bng\b', ln))
        out.append('L%-4d (%5d ch) hits=%d  %s' % (i, len(ln), hits, ln[:600]))

section('B. the function bodies to edit (full text)')
for n in (23, 24, 27, 38, 47, 51, 71, 72, 74, 94, 109, 130):
    body = lines[n - 1]
    out.append('')
    out.append('----- LINE %d  (%d chars) -----' % (n, len(body)))
    out.append(body)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text('\n'.join(out), encoding='utf-8', newline='')
print('wrote %s (%d chars)' % (OUT, len('\n'.join(out))))
print('total lines in src/main.script.js: %d' % len(lines))
