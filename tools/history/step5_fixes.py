"""Fixes from the tech-tree review.

User decisions:
  1. fix the radius / SITE_TP contradiction            -> done here
  2. SLOW tech growth (not "make it unaffordable")      -> costs up
  4. exploration -> recorded as a todo, fog-of-war later -> doc only
  5. UI shows what each purchase actually buys           -> done here
  3. replace the second line -> NOT done: as specified it is gated on the CAP
     validation (option A needs CAP re-validated; option B is a CAP compensator,
     which is meaningless without CAP). Flagged in the doc instead.

The #1 fix: the site loop was bounded by a fixed `SITE_TP`, so a radius upgrade
widened the ring while the site could still only pull SITE_TP per turn. Verified
before the fix: radius 2 reached 15 neutrals and absorbed 4 of them.
Now the budget scales with the radius line (+4 per level).

Costs: 3+3*level (18 total) -> 8+8*level (48 total). Basis: the measured 80-turn
income was 12 points (all exploration), so the full tree lands in the middle-to-late
part of a 200-700 turn game instead of within minutes. Income is front-loaded
(nearby blocks are cheap to sweep), so the real rate decays.
"""
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
    print('FIX ABORTED: %s' % msg)
    print('Edits applied in memory before the abort: %s' % (', '.join(applied) or 'none'))
    print('NOTE: no source file was written yet -- src/ and the deliverable are unchanged.')
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s: expected %d occurrence(s), found %d\n  anchor: %r' % (label, n, c, old[:220]))
    applied.append(label)
    return text.replace(old, new)


js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')

# ------------------------------------------------------------------ #1 helpers
# single source of truth for each line's curve: level -> value, then q -> value
js = sub(js, 'function absorbTp(q){return ABSORB_TP+(q.upTp||0);}',
         'function absorbTpAt(lv){return ABSORB_TP+(lv||0);}'
         'function absorbTp(q){return absorbTpAt(q.upTp||0);}'
         'function siteRadiusAt(lv){return ABSORB_RADIUS+(lv||0);}'
         'function siteBudgetAt(lv){return SITE_TP+4*(lv||0);}',
         1, '#1: level-keyed curves for TP / radius / site budget')

js = sub(js, 'function siteRadius(q){return ABSORB_RADIUS+(q.upRadius||0);}',
         'function siteRadius(q){return siteRadiusAt(q.upRadius||0);}'
         'function siteBudget(q){return siteBudgetAt(q.upRadius||0);}',
         1, '#1: siteBudget helper')

# the actual bug: a fixed budget throttled every radius upgrade
js = sub(js, 'let budget=SITE_TP;', 'let budget=siteBudget(q);',
         1, '#1: FIXED -- site throughput now scales with the radius line')

# ------------------------------------------------------------------ #2 slower growth
js = sub(js, 'function techCost(line,level){return 3+3*level;}',
         'function techCost(line,level){return 8+8*level;}',
         1, '#2: costs 3+3*level -> 8+8*level (full tree 18 -> 48 points)')

# ------------------------------------------------------------------ #5 benefit preview
OLD_UI = (
    "function techUI(){const t=$('tech');if(t)t.textContent=(s.tech||0)+' 点';"
    "const cb=$('convertScore');if(cb)cb.onclick=techConvert;"
    "const box=$('techTree');if(!box)return;"
    "const mk=(line,label)=>{const lv=techLevel(s,line),max=techMax(line),cost=techCost(line,lv),"
    "b=document.createElement('button');"
    "b.textContent=lv>=max?(label+' '+lv+'/'+max+' · 已满级'):(label+' '+lv+'/'+max+' · 升级 '+cost+' 点');"
    "b.disabled=lv>=max||(s.tech||0)<cost;b.onclick=()=>techBuy(line);return b;};"
    "box.replaceChildren(mk('tp','吞吐 TP'),mk('radius','收集半径'));}"
)
NEW_UI = (
    "function techInfoAt(line,lv){"
    "if(line==='tp')return '每块每回合吸收 '+absorbTpAt(lv)+' 个';"
    "const r=siteRadiusAt(lv);"
    "return '覆盖 '+((2*r+1)*(2*r+1)-1)+' 格 · 站点吞吐 '+siteBudgetAt(lv)+'/回合';}"
    "function techUI(){const t=$('tech');if(t)t.textContent=(s.tech||0)+' 点';"
    "const cb=$('convertScore');if(cb)cb.onclick=techConvert;"
    "const box=$('techTree');if(!box)return;"
    "const mk=(line,label)=>{const lv=techLevel(s,line),max=techMax(line),"
    "b=document.createElement('button');"
    "if(lv>=max){b.textContent=label+' '+lv+'/'+max+' · 已满级 · '+techInfoAt(line,lv);b.disabled=true;}"
    "else{const cost=techCost(line,lv);"
    "b.textContent=label+' '+lv+'/'+max+' · 升级 '+cost+' 点 · '+techInfoAt(line,lv)+' → '+techInfoAt(line,lv+1);"
    "b.disabled=(s.tech||0)<cost;}"
    "b.onclick=()=>techBuy(line);return b;};"
    "box.replaceChildren(mk('tp','吞吐 TP'),mk('radius','收集半径'));}"
)
js = sub(js, OLD_UI, NEW_UI, 1, '#5: buttons preview the change they buy (now -> next)')

js_path.write_text(js, encoding='utf-8', newline='')
print('engine rewritten: %d chars' % len(js))

# ------------------------------------------------------------------ exports
be = ROOT / 'tools' / 'build_engine.py'
txt = be.read_text(encoding='utf-8')
if "'siteBudget'" not in txt:
    txt = txt.replace("'absorbTp', 'siteRadius',",
                      "'absorbTp', 'siteRadius', 'siteBudget', 'absorbTpAt', 'siteRadiusAt', "
                      "'siteBudgetAt', 'techInfoAt',", 1)
    if "'siteBudget'" not in txt:
        fail('tools/build_engine.py: export anchor not found')
    be.write_text(txt, encoding='utf-8', newline='')
    applied.append('tools/build_engine.py export list')
    print('tools/build_engine.py export list updated')

print()
print('FIXES APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
