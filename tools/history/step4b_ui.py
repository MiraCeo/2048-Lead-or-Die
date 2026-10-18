"""Step 4 (continued): meaningful kill income + the tech-tree UI panel.

Two user decisions:
  1. kill points only for MEANINGFUL kills -- enemy cores and bunkers, not every
     member tile. (The doc's 694-turn reference run logged 674 kills; at 1 point
     each that alone would swamp an 18-point tree.)
  2. the tech-tree UI panel.

UI placement notes:
  - the panel goes into the left aside in main.shell.html, next to ACTIONS,
    matching the signed layout decision ("侧栏与 AP 面板同列").
  - `ui()` is covered by a tutorial patch, so the `techUI();` call must be mirrored
    into BOTH sides of that patch (old = engine side, new = tutorial side). The
    tutorial's shell has no tech elements, so techUI() early-returns there via its
    null guards -- harmless, and it keeps one code path.
  - converting score and buying upgrades go through the existing
    remember()/save()/ui() pattern used by every other action, so undo works.
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
    print('STEP 4 (UI) ABORTED: %s' % msg)
    print('Edits applied in memory before the abort: %s' % (', '.join(applied) or 'none'))
    print('NOTE: no source file was written yet -- src/ and the deliverable are unchanged.')
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s: expected %d occurrence(s), found %d\n  anchor: %r' % (label, n, c, old[:220]))
    applied.append(label)
    return text.replace(old, new)


# ======================================================================
# 1. meaningful kills only
# ======================================================================
js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')

js = sub(js, "if(t.side==='e'){q.kills++;q.tech=(q.tech||0)+1;}",
         "if(t.side==='e'){q.kills++;if(t.core||t.kind==='bunker')q.tech=(q.tech||0)+1;}",
         1, 'engine: kill income only for enemy cores and bunkers')

# ======================================================================
# 2. UI functions, inserted ahead of growFighters (outside every patched hunk)
# ======================================================================
UI_BLOCK = (
    "function techBuy(line){const q=copy(s),r=buyTech(q,line);"
    "if(r.error){say(r.error);draw();return;}"
    "remember();s=q;save();ui();"
    "say('科技树：'+(line==='tp'?'吞吐':'收集半径')+' 升到 '+r.level+' 级，消耗 '+r.cost+' 点。');}\n"
    "function techConvert(){const q=copy(s),got=convertScore(q);"
    "if(!got){say('积分不足 '+SCORE_PER_TECH+'，无法兑换。');draw();return;}"
    "remember();s=q;save();ui();"
    "say('兑换 '+got+' 点科技点，消耗 '+(got*SCORE_PER_TECH)+' 积分。');}\n"
    "function techUI(){const t=$('tech');if(t)t.textContent=(s.tech||0)+' 点';"
    "const cb=$('convertScore');if(cb)cb.onclick=techConvert;"
    "const box=$('techTree');if(!box)return;"
    "const mk=(line,label)=>{const lv=techLevel(s,line),max=techMax(line),cost=techCost(line,lv),"
    "b=document.createElement('button');"
    "b.textContent=lv>=max?(label+' '+lv+'/'+max+' · 已满级'):(label+' '+lv+'/'+max+' · 升级 '+cost+' 点');"
    "b.disabled=lv>=max||(s.tech||0)<cost;b.onclick=()=>techBuy(line);return b;};"
    "box.replaceChildren(mk('tp','吞吐 TP'),mk('radius','收集半径'));}\n"
)

js = sub(js, 'function growFighters(q){', UI_BLOCK + 'function growFighters(q){',
         1, 'engine: techBuy / techConvert / techUI')

# ======================================================================
# 3. call it from ui() -- mirrored into the patch below
# ======================================================================
js = sub(js, 'drawMinimap();', 'drawMinimap();techUI();',
         1, 'engine: ui() refreshes the tech panel')

js_path.write_text(js, encoding='utf-8', newline='')
print('engine rewritten: %d chars' % len(js))

# ======================================================================
# 4. mirror the ui() insertion into both sides of the tutorial patch
# ======================================================================
pat_path = SRC / 'tutorial.patches.py'
pat = pat_path.read_text(encoding='utf-8')
pat = sub(pat, 'drawMinimap();', 'drawMinimap();techUI();',
          2, 'patches: ui() call mirrored into old + new')
pat_path.write_text(pat, encoding='utf-8', newline='')
print('patches updated: %d chars' % len(pat))

# ======================================================================
# 5. the panel markup
# ======================================================================
shell_path = SRC / 'main.shell.html'
shell = shell_path.read_text(encoding='utf-8')

PANEL = (
    '<div class="panel"><h2>TECH / 科技点</h2>'
    '<div class="inline-bank"><strong id="tech"></strong>'
    '<span class="mini-detail">科技点<br>击破核心/碉堡 · 探索新区块 · 兑换积分</span></div>'
    '<div id="techTree" class="compact-list"></div>'
    '<button id="convertScore" title="每 100 积分兑换 1 点科技点，会消耗积分">兑换积分 → 科技点</button>'
    '</div>'
)

shell = sub(shell, '<div class="panel"><h2>FLEETS / 切换与回到核心</h2>',
            PANEL + '<div class="panel"><h2>FLEETS / 切换与回到核心</h2>',
            1, 'shell: TECH panel added beside ACTIONS')

shell_path.write_text(shell, encoding='utf-8', newline='')
print('shell updated: %d chars' % len(shell))

print()
print('STEP 4 (UI) EDITS APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
