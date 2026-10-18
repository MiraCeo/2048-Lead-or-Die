"""Quantify the fork between the shipped game script and the tutorial's embedded copy.

The tutorial is base64-embedded in the HTML and carries its OWN copy of the rules
engine (moveMain/worldStep/normalize/... are each defined inside it too), plus
lesson scaffolding. Before a major engine overhaul we need to know how big that
fork actually is, because every engine change would otherwise have to be applied
twice by hand.

Reports:
  - sizes of both scripts (base64 blobs excluded, since they are embedded docs)
  - a line-level diff opcode summary of the two scripts
  - which functions are defined only in one side
"""
import base64
import difflib
import re
import sys
from pathlib import Path

# Windows Python defaults to GBK on stdout here, which cannot encode '✓' etc.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HTML = Path(r'D:\2048\2048小游戏-教程七关.html')
BLOB_RE = re.compile(r"atob\('([A-Za-z0-9+/=]+)'\)")

html = HTML.read_text(encoding='utf-8')

# --- main game script -------------------------------------------------------
main_js = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)[0]

# --- embedded documents -----------------------------------------------------
blobs = BLOB_RE.findall(html)
docs = [base64.b64decode(b).decode('utf-8') for b in blobs]
guide, tutorial = docs[0], docs[1]

tut_js = re.findall(r'<script[^>]*>(.*?)</script>', tutorial, re.S)[0]


def strip_blobs(src: str) -> str:
    """Replace embedded base64 document literals with a short placeholder."""
    return BLOB_RE.sub("atob('<BLOB>')", src)


main_clean = strip_blobs(main_js)
tut_clean = strip_blobs(tut_js)

print('=== sizes ===')
print('main script     : %6d chars (raw), %6d chars (blobs stripped)'
      % (len(main_js), len(main_clean)))
print('tutorial script : %6d chars (raw), %6d chars (blobs stripped)'
      % (len(tut_js), len(tut_clean)))
print('tutorial doc    : %6d chars   guide doc: %6d chars' % (len(tutorial), len(guide)))

FUNC_DEF = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')


def defs(src: str):
    return set(FUNC_DEF.findall(src))


md, td = defs(main_clean), defs(tut_clean)
print()
print('=== function definitions ===')
print('main only     (%2d): %s' % (len(md - td), ', '.join(sorted(md - td))))
print('tutorial only (%2d): %s' % (len(td - md), ', '.join(sorted(td - md))))
print('shared        (%2d)' % len(md & td))

print()
print('=== line-level diff of the two scripts (opcode summary) ===')
a = main_clean.split('\n')
b = tut_clean.split('\n')
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
print('similarity ratio: %.4f   (main lines=%d, tutorial lines=%d)'
      % (sm.ratio(), len(a), len(b)))
n_eq = n_diff = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        n_eq += i2 - i1
        continue
    n_diff += 1
    print('\n[%s] main[%d:%d] (%dL) -> tutorial[%d:%d] (%dL)'
          % (tag, i1 + 1, i2, i2 - i1, j1 + 1, j2, j2 - j1))
    for k in range(i1, i2):
        print('   -M:', a[k][:150])
    for k in range(j1, j2):
        print('   +T:', b[k][:150])
print('\nequal lines: %d   differing hunks: %d' % (n_eq, n_diff))
