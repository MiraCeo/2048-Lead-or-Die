"""Step 4 (engine foundation): tech points and the two tech-tree lines.

Signed decisions in force:
  - tech points cost score (spending is real -- a tradeoff between scoring and growing)
  - the tree carries only THROUGHPUT (TP) and RADIUS; the CAP line is deliberately
    deferred until it has been re-validated across seeds (the handover doc's
    "CAP reversal" is a single-seed result, and single-seed A/B is unreliable here)
  - sources: score conversion + kills + exploration

This turn implements the ENGINE side only: state, the three sources, the two
upgrade lines, and their effect on absorption. The side-panel UI comes next,
because it touches main.shell.html and the patched ui() line.

Design choices worth knowing:
  - score conversion is MANUAL and lossy-by-choice: floor(score / 100) points, and
    those points are deducted from score. Automatic conversion would remove the
    tradeoff the doc wanted.
  - exploration counts 10x10 blocks of the 100x100 world (100 blocks). Entering a
    block for the first time is worth 1 point. A block is "entered" when any
    friendly tile stands in it, so it needs no new data structure beyond a map.
  - `survey()` is invoked from inside autoCollect rather than from worldStep.
    worldStep is covered by a tutorial patch, and every insertion there forces the
    patch to be re-anchored; autoCollect already runs once per turn from that same
    call site, so this keeps the patch surface untouched.
  - TP upgrades raise the per-tile absorb budget; radius upgrades raise every
    site's ring. Both read through helpers so a single tune point controls them.
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
    print('STEP 4 ABORTED: %s' % msg)
    print('Edits applied in memory before the abort: %s' % (', '.join(applied) or 'none'))
    print('NOTE: no source file was written yet -- src/ and the deliverable are unchanged.')
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s: expected %d occurrence(s), found %d\n  anchor: %r' % (label, n, c, old[:220]))
    applied.append(label)
    return text.replace(old, new)


js = (SRC / 'main.script.js').read_text(encoding='utf-8')

# ---------------------------------------------------------------- constants + API
NEW_BLOCK = (
    "const SCORE_PER_TECH=100,TECH_TP_MAX=2,TECH_RADIUS_MAX=2;\n"
    "function absorbTp(q){return ABSORB_TP+(q.upTp||0);}\n"
    "function siteRadius(q){return ABSORB_RADIUS+(q.upRadius||0);}\n"
    "function techLevel(q,line){return line==='tp'?(q.upTp||0):(q.upRadius||0);}\n"
    "function techMax(line){return line==='tp'?TECH_TP_MAX:TECH_RADIUS_MAX;}\n"
    "function techCost(line,level){return 3+3*level;}\n"
    "function survey(q){q.visited=q.visited||{};let found=0;"
    "for(let i=0;i<N*N;i++){const t=q.g[i];"
    "if(!t||t.side!=='p'||t.support)continue;"
    "const b=Math.floor(i/N/10)*10+Math.floor(i%N/10);"
    "if(!q.visited[b]){q.visited[b]=1;found++;}}"
    "if(found)q.tech=(q.tech||0)+found;return found;}\n"
    "function convertScore(q){const pts=Math.floor((q.score||0)/SCORE_PER_TECH);"
    "if(pts<=0)return 0;q.score-=pts*SCORE_PER_TECH;q.tech=(q.tech||0)+pts;return pts;}\n"
    "function buyTech(q,line){const lv=techLevel(q,line);"
    "if(lv>=techMax(line))return{error:'这条线已经满级。'};"
    "const cost=techCost(line,lv);"
    "if((q.tech||0)<cost)return{error:'科技点不足：需要 '+cost+'，现有 '+(q.tech||0)+'。'};"
    "q.tech-=cost;"
    "if(line==='tp')q.upTp=lv+1;else q.upRadius=lv+1;"
    "return{line,level:lv+1,cost,left:q.tech};}\n"
)

js = sub(js, 'function growFighters(q){', NEW_BLOCK + 'function growFighters(q){',
         1, 'engine: tech constants + survey/convertScore/buyTech/helpers')

# ---------------------------------------------------------------- state fields
js = sub(js, 'serial:1,score:0,shots:0,kills:0,logs:[]',
         'serial:1,score:0,shots:0,kills:0,tech:0,upTp:0,upRadius:0,visited:null,logs:[]',
         1, 'engine: initial() carries tech state')

# ---------------------------------------------------------------- source: kills
js = sub(js, "if(t.side==='e')q.kills++;",
         "if(t.side==='e'){q.kills++;q.tech=(q.tech||0)+1;}",
         1, 'engine: kills award a tech point')

# ---------------------------------------------------------------- wire the lines
js = sub(js, 'function autoCollect(q){const lvCore=lvl(sharedCore(q));let grown=0,absorbed=0;',
         'function autoCollect(q){const lvCore=lvl(sharedCore(q));let grown=0,absorbed=0;'
         'const tps=absorbTp(q);survey(q);',
         1, 'engine: autoCollect picks up TP upgrade + runs the exploration survey')

js = sub(js, 'const R=site.collectRadius??ABSORB_RADIUS,ring=ringCells(s,R);',
         'const R=site.collectRadius??siteRadius(q),ring=ringCells(s,R);',
         1, 'engine: site radius reads the upgrade line')

js = sub(js, 'for(const d in dirs){if(used>=ABSORB_TP||t.n>=ABSORB_CAP)break;',
         'for(const d in dirs){if(used>=tps||t.n>=ABSORB_CAP)break;',
         1, 'engine: absorb throughput reads the upgrade line')

(SRC / 'main.script.js').write_text(js, encoding='utf-8', newline='')
print('engine rewritten: %d chars' % len(js))

# ---------------------------------------------------------------- exports
be = ROOT / 'tools' / 'build_engine.py'
txt = be.read_text(encoding='utf-8')
if "'buyTech'" not in txt:
    txt = txt.replace("'settleTiles', 'ringCells'",
                      "'settleTiles', 'ringCells', 'survey', 'convertScore', 'buyTech', "
                      "'techCost', 'techLevel', 'techMax', 'absorbTp', 'siteRadius'", 1)
    if "'buyTech'" not in txt:
        fail('tools/build_engine.py: export anchor not found')
    be.write_text(txt, encoding='utf-8', newline='')
    applied.append('tools/build_engine.py export list')
    print('tools/build_engine.py export list updated')

print()
print('STEP 4 (engine) EDITS APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
