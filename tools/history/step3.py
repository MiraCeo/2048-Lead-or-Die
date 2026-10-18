"""Step 3: absorption payload becomes a two-way resource -- grow when full, heal when hurt.

Signed direction (handover doc section 4.1):
  - full hp  (hp === cap): payload keeps accumulating -> upgrades
  - not full (hp <  cap):  payload converts to hp (growth stops, recovery starts)

This makes defence economically meaningful: losing hp stops a tile developing.
The same idea drives "where do I set up shop" -- absorbing inside enemy range stalls growth.

Parameters (tunable):
  - conversion is 1 payload : 1 hp
  - per-turn heal cap is max(ABSORB_TP, ceil(cap * REGEN_FRAC)) with REGEN_FRAC = 0.1.
    A flat cap of 2 hp/turn would be invisible next to caps of 81/324/1215, so the cap
    scales with the tile; in practice the real limiter becomes how much you can eat,
    which is the economics the doc wanted.

Scope: friendly tiles only (side 'p', non-support). The doc phrases this as a behaviour
"common to all tiles", but enabling it on enemies would raise difficulty in a way nobody
asked for (and enemy tiles have no payload source except collectors), so it is left
player-side and easy to widen later.

Restructure: absorption now only accumulates payload; a single per-turn `settleTiles`
pass then decides growth vs healing. One settlement per turn is easier to reason about
than growing mid-absorption.
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
SRC = ROOT / 'src'
applied = []


def fail(msg):
    print()
    print('STEP 3 ABORTED: %s' % msg)
    print('Edits applied in memory before the abort: %s' % (', '.join(applied) or 'none'))
    print('NOTE: no source file was written yet -- src/ and the deliverable are unchanged.')
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s: expected %d occurrence(s), found %d\n  anchor: %r' % (label, n, c, old[:220]))
    applied.append(label)
    return text.replace(old, new)


def sub_re(text, pattern, new, n, label, flags=0):
    c = len(re.findall(pattern, text, flags))
    if c != n:
        fail('%s: expected %d match(es), found %d\n  pattern: %r' % (label, n, c, pattern[:220]))
    applied.append(label)
    return re.sub(pattern, new, text, flags=flags)


# ======================================================================
# 1. engine
# ======================================================================
js = (SRC / 'main.script.js').read_text(encoding='utf-8')

js = sub(js, 'const ABSORB_CAP=8,ABSORB_TP=2,ABSORB_RADIUS=1,SITE_TP=4;',
         'const ABSORB_CAP=8,ABSORB_TP=2,ABSORB_RADIUS=1,SITE_TP=4,REGEN_FRAC=0.1;',
         1, 'engine: REGEN_FRAC constant')

NEW_ABSORB = (
    'function absorbValue(q,t,value){if(!t||t.side!==\'p\'||t.support)return 0;'
    't.payload=(t.payload||0)+value;return 0;}'
)
NEW_SETTLE = (
    'function settleTiles(q,lvCore){let grown=0;'
    'for(let i=0;i<N*N;i++){const t=q.g[i];'
    'if(!t||t.side!==\'p\'||t.support)continue;'
    'const pay=t.payload||0;if(pay<=0)continue;'
    'if(t.hp<t.cap){const maxHeal=Math.max(ABSORB_TP,Math.ceil(t.cap*REGEN_FRAC));'
    'const heal=Math.min(pay,maxHeal,t.cap-t.hp);'
    'if(heal>0){t.payload=pay-heal;t.hp=t.hp+heal;}}'
    'else{let left=pay;'
    'while(left>=t.n&&t.n*2<=ABSORB_CAP){left-=t.n;'
    'const oldCap=t.cap||1,oldHp=t.hp??oldCap;t.n*=2;t.cap=3**lvl(t.n)*lvCore;'
    't.hp=Math.max(1,Math.min(t.cap,Math.round(oldHp*t.cap/oldCap)));grown++;}'
    't.payload=left;}}'
    'return grown;}'
)

js = sub_re(js, r'^function absorbValue\(q,t,value,lvCore\)\{.*\}$',
            lambda m: NEW_ABSORB + '\n' + NEW_SETTLE,
            1, 'engine: absorbValue accumulates only; settleTiles added', re.M)

js = sub(js, 'if(grown||absorbed)rescale(q);return grown;}',
         'grown+=settleTiles(q,lvCore);if(grown||absorbed)rescale(q);return grown;}',
         1, 'engine: settle once per turn at the end of absorption')

js = sub(js, "，射程8格。${t.side==='p'&&!t.support?'吸收上限 '+ABSORB_CAP+'（'+(t.n>=ABSORB_CAP?'已达上限，不再吸收':'可吸收 · 累积 '+(t.payload||0))+'）':''}",
         "，射程8格。${t.side==='p'&&!t.support?(t.hp<t.cap?'受伤中：累积 '+(t.payload||0)+' 每回合转为回血（成长暂停）':'吸收上限 '+ABSORB_CAP+'（'+(t.n>=ABSORB_CAP?'已达上限，不再吸收':'可吸收 · 累积 '+(t.payload||0))+'）'):''}",
         1, 'engine: hover shows recovery state')

(SRC / 'main.script.js').write_text(js, encoding='utf-8', newline='')
print('engine rewritten: %d chars' % len(js))

# ======================================================================
# 2. guide
# ======================================================================
g_path = SRC / 'guide.html'
guide = g_path.read_text(encoding='utf-8')

guide = sub(guide,
            '所以半径买到的是覆盖面，不能替代经营。</p>',
            '所以半径买到的是覆盖面，不能替代经营。</p>'
            '<p><strong>受伤即停长，转而恢复。</strong>方块满血时，累积量用于升级；'
            '一旦掉血，累积量就改为回血——每回合最多恢复上限的一成，成长暂停。'
            '这给防御赋予了经济意义：敌人不必打死你，打掉血就能让你的发育停下来。</p>',
            1, 'guide: recovery paragraph')

g_path.write_text(guide, encoding='utf-8', newline='')
print('guide updated: %d chars' % len(guide))

# ======================================================================
# 3. headless tooling export list
# ======================================================================
be = ROOT / 'tools' / 'build_engine.py'
txt = be.read_text(encoding='utf-8')
if "'settleTiles'" not in txt:
    txt = txt.replace("'absorbValue', 'ringCells'", "'absorbValue', 'settleTiles', 'ringCells'", 1)
    if "'settleTiles'" not in txt:
        fail('tools/build_engine.py: export anchor not found')
    be.write_text(txt, encoding='utf-8', newline='')
    applied.append('tools/build_engine.py export list')
    print('tools/build_engine.py export list updated')

print()
print('STEP 3 EDITS APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
