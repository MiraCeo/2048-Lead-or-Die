"""Generate an engine variant with auto-collect injected at a chosen stage of worldStep.

WHY THIS EXISTS
---------------
The handover doc (section 7) records an unresolved anomaly: the same seed, same
CAP, same throughput, absorbing once per turn, gives 208 turns / peak 64 when
absorption runs after growFighters ("internal"), versus 694 turns / peak 16384
when it runs at end of turn ("external"). The doc's own conclusion is that the
difference is structural, not noise, and that tuning numbers before locating it
would just be compensating for an unknown bias.

The old tool (make_collect_engine.py) hardcoded ONE injection point. To isolate
which stage is responsible the injection point becomes a parameter, and the
insertion can be either before or after its anchor so that a conditional stage
(e.g. replenish, which only runs on turn%10==0) can be bracketed by two
unconditional call sites.

The __autoCollect body is byte-for-byte the doc's section 2.2 / the old tool's
version (CAP=8, TP=2, full heal). Only the CALL SITE varies.

Usage:
    python tools/build_variant.py --position grow --out build/variants/grow.js
    python tools/build_variant.py --position prespawn --out build/variants/prespawn.js
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_engine import build, dominant_newline, DEFAULT_HTML  # noqa: E402

AUTO_COLLECT = (
    "function __autoCollect(q){"
    "const CAP={CAP},TP={TP},lvCore=lvl(sharedCore(q));let grown=0;"
    "for(let i=0;i<N*N;i++){"
    "const t=q.g[i];"
    "if(!t||t.side!=='p'||t.support||t.n>=CAP)continue;"
    "let used=0;"
    "for(const d in dirs){"
    "if(used>=TP||t.n>=CAP)break;"
    "const j=neighbor(i,d);if(j<0)continue;"
    "const u=q.g[j];"
    "if(!u||u.side!=='n'||u.n>CAP)continue;"
    "t.payload=(t.payload||0)+u.n;q.g[j]=null;used++;"
    "while(t.payload>=t.n&&t.n*2<=CAP){t.payload-=t.n;t.n*=2;t.cap=3**lvl(t.n)*lvCore;t.hp=t.cap;grown++;}"
    "if(t.payload<t.n)break;"
    "}}"
    "if(grown)rescale(q);"
    "return grown;}"
)

CALL = 'if(!q.dead)__autoCollect(q);'

# name -> (anchor substring, 'after'|'before'|None)
#
# worldStep order: moveMain → turn++ → growFighters → fire('p') → ai() → fire('e')
#                  → { normalize → replenish(t%10) → reinforce(t==nextWave)
#                      → spawnSupport(t>=nextSupport) → spawn() } → log → return
POSITIONS = {
    'move':     ('const r=moveMain(q,dir);if(!r)return null;', 'after'),
    'grow':     ('if(!q.dead)growFighters(q);', 'after'),
    'fire':     ("const playerShots=fire(q,'p',fx);", 'after'),
    'ai':       ('if(!q.dead&&q.turn%2===0)enemyMoves=ai(q);', 'after'),
    'efire':    ("if(!q.dead)enemyShots=fire(q,'e',fx,t=>q.turn%2===0||teamCore(q,t.team)?.kind==='bunker');", 'after'),
    'norm':     ('if(!q.dead){normalize(q);', 'after'),
    # unconditional, AFTER replenish/reinforce/spawnSupport but BEFORE spawn() --
    # splits the norm→supply boundary into "the conditional top-ups" vs "spawn itself"
    'prespawn': ('supply=spawn(q);', 'before'),
    'supply':   ('supply=spawn(q);', 'after'),
    'end':      (None, None),
}

WORLDSTEP_DEF = 'function worldStep(q,dir){'


def make_variant(html_path: str, position: str, cap: int, tp: int) -> str:
    if position not in POSITIONS:
        sys.exit('unknown position %r; choose from %s'
                 % (position, ', '.join(sorted(POSITIONS))))

    body = AUTO_COLLECT.replace('{CAP}', str(cap)).replace('{TP}', str(tp))

    engine = build(html_path, extra_exports=['__autoCollect'])

    if engine.count(WORLDSTEP_DEF) != 1:
        sys.exit('worldStep definition not unique (%d)' % engine.count(WORLDSTEP_DEF))
    engine = engine.replace(WORLDSTEP_DEF, body + WORLDSTEP_DEF, 1)

    anchor, where = POSITIONS[position]
    if anchor is not None:
        n = engine.count(anchor)
        if n != 1:
            sys.exit('anchor for %r matched %d times (expected exactly 1): %r'
                     % (position, n, anchor))
        replacement = CALL + anchor if where == 'before' else anchor + CALL
        engine = engine.replace(anchor, replacement, 1)

    return engine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', default=DEFAULT_HTML)
    ap.add_argument('--position', required=True, choices=sorted(POSITIONS))
    ap.add_argument('--cap', type=int, default=8, help='absorb ceiling (n >= CAP stops growing)')
    ap.add_argument('--tp', type=int, default=2, help='absorb throughput per tile per turn')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    engine = make_variant(args.html, args.position, args.cap, args.tp)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    nl = dominant_newline(args.html)
    out.write_bytes(engine.replace('\n', nl).encode('utf-8'))

    anchor, where = POSITIONS[args.position]
    print('position : %s   (call %s %s, cap=%d, tp=%d)'
          % (args.position,
             'inside worldStep' if anchor is not None else 'outside worldStep',
             where or '', args.cap, args.tp))
    print('out      : %s  (%d chars)' % (out, len(engine)))


if __name__ == '__main__':
    main()
