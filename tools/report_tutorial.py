"""Dump the tutorial's lesson hooks to a report file for reading.

The tutorial carries its own copy of the engine plus lesson scaffolding. Before
we delete the 'whole neutral group capture' mechanic we need to see exactly which
lessons depend on it. Console encoding on this box is GBK, so write a UTF-8 file.
"""
import base64
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HTML = Path(r'D:\2048\2048小游戏-教程七关.html')
OUT = Path(r'D:\2048\build\reports\tutorial_hooks.txt')
OUT.parent.mkdir(parents=True, exist_ok=True)

html = HTML.read_text(encoding='utf-8')
blobs = re.findall(r"atob\('([A-Za-z0-9+/=]+)'\)", html)
tutorial = base64.b64decode(blobs[1]).decode('utf-8')
tut_js = re.findall(r'<script[^>]*>(.*?)</script>', tutorial, re.S)[0]
tut_js = re.sub(r"atob\('[A-Za-z0-9+/=]+'\)", "atob('<BLOB>')", tut_js)

lines = []


def section(title, text):
    lines.append('\n' + '=' * 78)
    lines.append(title)
    lines.append('=' * 78)
    lines.append(text.strip())


# --- the lessons table ------------------------------------------------------
m = re.search(r'const lessons=\[.*?\}\];', tut_js, re.S)
section('lessons[] table', m.group(0) if m else 'NOT FOUND')


def grab(name):
    """Extract `function name(...)` up to the line containing its closing brace."""
    m = re.search(r'function\s+' + re.escape(name) + r'\s*\(', tut_js)
    if not m:
        return None
    # functions here are one-per-line, so take to end of that line
    end = tut_js.find('\n', m.start())
    return tut_js[m.start():end]


for fn in ('tutorialInitial', 'tutorialDone', 'tutorialHighlights'):
    body = grab(fn)
    section('function ' + fn, body if body else 'NOT FOUND')

# tutorialUI is long; keep the first 4000 chars
body = grab('tutorialUI')
section('function tutorialUI (head 4000)', (body or 'NOT FOUND')[:4000])

# --- every reference to the group mechanic in the tutorial ------------------
hits = []
for i, ln in enumerate(tut_js.split('\n')):
    if re.search(r'\bng\b|neutralGroups|整组|中立组|金色', ln):
        hits.append('L%d: %s' % (i + 1, ln[:400]))
section('tutorial lines referencing the neutral-group mechanic (%d)' % len(hits),
        '\n\n'.join(hits) if hits else 'none')

# --- highlight code: which cells get the golden teaching frame --------------
m = re.search(r'lessonTargets|highlightCells|tutorialTarget', tut_js)
section('highlight helper presence',
        'matched: %s' % (m.group(0) if m else 'NONE of lessonTargets/highlightCells/tutorialTarget'))

OUT.write_text('\n'.join(lines), encoding='utf-8')
print('wrote %s (%d chars)' % (OUT, len('\n'.join(lines))))
