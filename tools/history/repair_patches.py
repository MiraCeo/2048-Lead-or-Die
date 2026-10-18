"""Repair stored patch anchors after an engine edit.

When the engine text inside a patch anchor changes, the anchor must change with it.
Both "old" (the engine side) and "new" (the tutorial side) are updated, so the
tutorial receives the same correction as the game.

Each substitution asserts its expected occurrence count, so an unexpected source
shape aborts instead of silently rewriting something else.

Usage: python tools/repair_patches.py
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _root import PATHS

ROOT = PATHS.ROOT
SRC = ROOT / 'src'
PATCHES = SRC / 'tutorial.patches.py'

# (old, new, expected count, label)
SUBS = [
    ("+' / '+new Set(s.g.filter(t=>t?.side==='n'&&t.nc).map(t=>t.nc)).size+'组';",
     "+' / '+new Set(s.g.filter(t=>t?.side==='n'&&t.nc).map(t=>t.nc)).size+'个密集区';",
     2, 'ui: neutral counter label'),
]


def main():
    text = PATCHES.read_text(encoding='utf-8')
    for old, new, expect, label in SUBS:
        c = text.count(old)
        if c != expect:
            sys.exit('REPAIR FAILED: %s -- expected %d occurrence(s), found %d\n  anchor: %r'
                     % (label, expect, c, old[:200]))
        text = text.replace(old, new)
        print('repaired: %-34s (%d occurrence(s))' % (label, c))
    PATCHES.write_text(text, encoding='utf-8', newline='')
    print('patches repaired -> %s' % PATCHES)


if __name__ == '__main__':
    main()
