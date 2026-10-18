"""Check every stored patch anchor against the current engine source.

Run this after editing src/main.script.js. Any anchor that no longer matches
exactly once is a patch that must be repaired before the build will succeed.
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

spec = importlib.util.spec_from_file_location('topic', SRC / 'tutorial.patches.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

js = (SRC / 'main.script.js').read_text(encoding='utf-8')

bad = []
for p in mod.PATCHES:
    n = js.count(p['old'])
    ok = (n == 1)
    if not ok:
        bad.append(p)
    print('%s  %-32s matches=%d  old=%dch' % ('OK  ' if ok else 'STALE', p['name'], n, len(p['old'])))

print()
print('stale patches: %d / %d' % (len(bad), len(mod.PATCHES)))
for p in bad:
    print()
    print('--- %s ---' % p['name'])
    print('anchor head: %r' % p['old'][:160])
