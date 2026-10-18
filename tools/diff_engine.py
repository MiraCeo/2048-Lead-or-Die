"""Compare the inline <script> of the shipped HTML against the headless engine file.

Purpose: recover the EXACT transform the previous author used to turn the
single-file game into a DOM-stubbed engine, so we can regenerate the engine
from the HTML after every edit instead of hand-syncing two copies.
"""
import re
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _root import PATHS

HTML = str(PATHS.DELIVERABLE)
ENG = str(PATHS.ANALYZE_ENGINE)


def load(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


s = load(HTML)
js = re.findall(r'<script[^>]*>(.*?)</script>', s, re.S)[0]
eng = load(ENG)

print('HTML <script>:', len(js), 'chars,', js.count('\n') + 1, 'lines')
print('engine.js    :', len(eng), 'chars,', eng.count('\n') + 1, 'lines')
print()

a = js.split('\n')
b = eng.split('\n')

sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
print('--- opcodes (html -> engine) ---')
n_diff = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal':
        continue
    n_diff += 1
    print(f'\n[{tag}] html[{i1 + 1}:{i2}] ({i2 - i1}L) -> engine[{j1 + 1}:{j2}] ({j2 - j1}L)')
    for k in range(i1, i2):
        print('   -H:', a[k][:200])
    for k in range(j1, j2):
        print('   +E:', b[k][:200])
if not n_diff:
    print('(no differences)')
print()
print('ratio:', round(sm.ratio(), 6))
