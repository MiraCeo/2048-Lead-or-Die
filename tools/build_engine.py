"""Regenerate the headless engine from the shipped single-file HTML.

The previous author's transform, recovered by tools/diff_engine.py, is exactly:

    engine  ==  <script> contents of the HTML,
                with its final '})();' line replaced by
                'globalThis.__CF__={...};})();'

So the HTML is the single source of truth and the engine is a *build artifact*.
No hand-syncing of two copies is needed after an edit -- just rerun this script.

Line endings: the generated file mirrors the HTML's own convention (LF here).
The `.analyze/` snapshots are CRLF only because the original extraction ran
Python's default Windows text-mode write, so --verify compares with newlines
normalised and reports the raw hashes for the record.

Usage:
    python tools/build_engine.py --out build/core-fleet.engine.js
    python tools/build_engine.py --out build/engine.js --verify .analyze/core-fleet.engine.js
    python tools/build_engine.py --out build/engine.js --add-export autoCollect
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _root import PATHS

DEFAULT_HTML = str(PATHS.DELIVERABLE)
CLOSER = '})();'

# Functions the headless harnesses reach through globalThis.__CF__.
# Add new engine entry points here (or --add-export) so experiments can call them.
EXPORTS = [
    'initial', 'worldStep', 'moveMain', 'spawn', 'ai', 'fire', 'camera', 'cores',
    'sharedCore', 'fmt', 'lvl', 'valid', 'neutralClusters', 'autoCollect', 'absorbValue', 'settleTiles', 'ringCells', 'survey', 'convertScore', 'buyTech', 'techCost', 'techLevel', 'techMax', 'absorbTp', 'siteRadius', 'siteBudget', 'absorbTpAt', 'siteRadiusAt', 'siteBudgetAt', 'techInfoAt', 'absorbThreshold', 'absorbThresholdAt', 'aiAbsorbCeiling', 'regenTiles', 'markCombat', 'tileBody', 'draw', 'techUI', 'techBuy', 'techConvert', 'enemySlots',
    'desiredSize', 'waveSpec', 'kill', 'reinforce', 'replenish', 'spawnSupport',
    'checkGoal', 'neutralMultiplier', 'collect', 'normalize', 'rescale', 'copy',
    'rand', 'contact', 'capture', 'teamCore', 'connected', 'visible', 'dist2',
    'memberValue', 'fillEnemy', 'growFighters', 'extraStep',
]


def extract_script(html: str) -> str:
    blocks = re.findall(r'<script[^>]*>(.*?)</script>', html, re.S)
    if len(blocks) != 1:
        sys.exit('expected exactly 1 <script> block, found %d' % len(blocks))
    return blocks[0]


def dominant_newline(path: str) -> str:
    raw = Path(path).read_bytes().decode('utf-8')
    crlf = raw.count('\r\n')
    lf = raw.count('\n') - crlf
    return '\r\n' if crlf > lf else '\n'


def build(html_path: str, extra_exports=None) -> str:
    """Return the engine source as text (LF-terminated)."""
    html = Path(html_path).read_text(encoding='utf-8')
    js = extract_script(html)
    lines = js.split('\n')

    idx = max(i for i, ln in enumerate(lines) if ln.strip())
    if lines[idx].strip() != CLOSER:
        sys.exit('last non-empty script line is not %r: %r'
                 % (CLOSER, lines[idx][:90]))

    names = list(EXPORTS)
    for n in (extra_exports or []):
        if n not in names:
            names.append(n)
    lines[idx] = 'globalThis.__CF__={' + ','.join(names) + '};' + CLOSER
    return '\n'.join(lines)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', default=DEFAULT_HTML)
    ap.add_argument('--out', required=True)
    ap.add_argument('--verify', help='reference engine expected to match in content')
    ap.add_argument('--add-export', action='append', default=[],
                    help='extra function name to expose on globalThis.__CF__')
    args = ap.parse_args()

    engine = build(args.html, args.add_export)
    nl = dominant_newline(args.html)
    payload = engine.replace('\n', nl).encode('utf-8')

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)

    print('html     : %s  (source of truth, newline=%s)'
          % (args.html, 'CRLF' if nl == '\r\n' else 'LF'))
    print('engine   : %s' % out)
    print('           %d chars, %d lines, %d bytes'
          % (len(engine), engine.count('\n') + 1, len(payload)))
    print('sha256   : %s' % sha256_bytes(payload))

    if args.verify:
        ref = Path(args.verify).read_text(encoding='utf-8')
        mine = engine.replace('\n', '\n')
        ref_norm = ref.replace('\r\n', '\n')
        same = (mine == ref_norm)
        print('verify   : %s' % args.verify)
        print('reference: %s  (content-normalised)' % sha256_bytes(ref_norm.encode('utf-8')))
        print('generated: %s  (content-normalised)' % sha256_bytes(mine.encode('utf-8')))
        print('MATCH    : %s' % ('YES -- pipeline reproduces the original transform'
                                 if same else 'NO -- transform differs'))
        if not same:
            for i, (x, y) in enumerate(zip(mine.split('\n'), ref_norm.split('\n'))):
                if x != y:
                    print('  first differing line %d:' % (i + 1))
                    print('    mine: %s' % x[:160])
                    print('    ref : %s' % y[:160])
                    break
            sys.exit(1)


if __name__ == '__main__':
    main()
