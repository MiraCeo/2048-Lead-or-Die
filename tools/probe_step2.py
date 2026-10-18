"""Probe the anchors step 2 needs before editing.

Absorption must be called between moveMain and growFighters inside worldStep.
worldStep is covered by a stored patch (its tutorial copy differs), so the probe
reports how many times the insertion anchor occurs in the engine and in the patch
store, and dumps both worldStep variants for inspection.
"""
import importlib.util
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
SRC = ROOT / 'src'
OUT = ROOT / 'build' / 'reports' / 'step2_probe.txt'

NEEDLE = 'if(!q.dead)growFighters(q);'

js = (SRC / 'main.script.js').read_text(encoding='utf-8')
pat_text = (SRC / 'tutorial.patches.py').read_text(encoding='utf-8')

spec = importlib.util.spec_from_file_location('topic', SRC / 'tutorial.patches.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

L = []
L.append('insertion anchor: %r' % NEEDLE)
L.append('count in src/main.script.js   : %d' % js.count(NEEDLE))
L.append('count in src/tutorial.patches.py : %d' % pat_text.count(NEEDLE))
L.append('')
L.append('anchor for the new function block: %r' % 'function growFighters(q){')
L.append('count in src/main.script.js   : %d' % js.count('function growFighters(q){'))
L.append('')

for p in mod.PATCHES:
    new = (SRC / p['new_file']).read_text(encoding='utf-8') if 'new_file' in p else p['new']
    for tag, body in (('OLD', p['old']), ('NEW', new)):
        if 'function worldStep' in body:
            i = body.find('function worldStep')
            L.append('=' * 90)
            L.append('patch %s  [%s] worldStep  (%d chars in body)' % (p['name'], tag, len(body)))
            L.append('=' * 90)
            L.append(body[i:i + 1500])
            L.append('')
            L.append('  contains insertion anchor: %s' % (NEEDLE in body))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text('\n'.join(L), encoding='utf-8', newline='')
print('wrote %s' % OUT)
print('anchor in engine      : %d' % js.count(NEEDLE))
print('anchor in patch store : %d' % pat_text.count(NEEDLE))
