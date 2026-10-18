"""Step 2: auto-collect (auto absorption) + site collection radius.

Signed decisions:
  - absorption runs AFTER the move and BEFORE growth  (phase: move -> absorb -> fight -> enemy -> supply)
  - upgrading does NOT full-heal; hp is preserved proportionally
  - a site's radius feeds the NEAREST non-fixed friendly tile that is still under the cap
  - every site has a per-turn throughput cap
  - initial values: radius 1, CAP 8, TP 2

Hard constraints carried over from the handover doc:
  - valid() forces n to be a power of two, so absorption must go through `payload`
    accounting; 4+2 may never become 6
  - rescale() must be called after absorbing, or caps drift from sharedCore

Also: the cap rule is enforced on the RECEIVER as well as the absorbing tile, so a
site that sits at the cap never vacuums neutrals (this is what keeps the "at cap =
no absorption" rule true and testable in the tutorial).

Touches:
    src/main.script.js        engine: constants, helpers, autoCollect, call site, hover text
    src/tutorial.patches.py   the same call site in both worldStep variants + lesson gate
    src/tutorial.lessons.js   lesson 02 -> teaches auto-collect
    src/guide.html            player-facing manual section
    tools/build_engine.py     export list
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
    print('STEP 2 ABORTED: %s' % msg)
    print('Edits already written this run: %s' % (', '.join(applied) or 'none'))
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s: expected %d occurrence(s), found %d\n  anchor: %r' % (label, n, c, old[:200]))
    applied.append(label)
    return text.replace(old, new)


def sub_re(text, pattern, new, n, label, flags=0):
    c = len(re.findall(pattern, text, flags))
    if c != n:
        fail('%s: expected %d match(es), found %d\n  pattern: %r' % (label, n, c, pattern[:200]))
    applied.append(label)
    return re.sub(pattern, new, text, flags=flags)


# ======================================================================
# 1. engine
# ======================================================================
NEW_BLOCK = (
    "const ABSORB_CAP=8,ABSORB_TP=2,ABSORB_RADIUS=1,SITE_TP=4;\n"
    "function ringCells(i,R){const out=[],r=Math.floor(i/N),c=i%N;for(let dr=-R;dr<=R;dr++)for(let dc=-R;dc<=R;dc++){"
    "if(!dr&&!dc)continue;const rr=r+dr,cc=c+dc;if(rr<0||rr>=N||cc<0||cc>=N)continue;out.push(rr*N+cc);}return out;}\n"
    "function absorbValue(q,t,value,lvCore){if(!t||t.side!=='p'||t.support)return 0;let grown=0;"
    "t.payload=(t.payload||0)+value;"
    "while(t.payload>=t.n&&t.n*2<=ABSORB_CAP){t.payload-=t.n;"
    "const oldCap=t.cap||1,oldHp=t.hp??oldCap;t.n*=2;t.cap=3**lvl(t.n)*lvCore;"
    "t.hp=Math.max(1,Math.min(t.cap,Math.round(oldHp*t.cap/oldCap)));grown++;}"
    "return grown;}\n"
    "function autoCollect(q){const lvCore=lvl(sharedCore(q));let grown=0,absorbed=0;"
    "for(let s=0;s<N*N;s++){const site=q.g[s];"
    "if(!site||site.side!=='p'||!(site.core||site.support))continue;"
    "const R=site.collectRadius??ABSORB_RADIUS,ring=ringCells(s,R);"
    "const receivers=ring.filter(i=>{const t=q.g[i];return !!t&&t.side==='p'&&!t.support&&t.n<ABSORB_CAP;});"
    "let budget=SITE_TP;"
    "const cands=ring.filter(j=>{const u=q.g[j];return !!u&&u.side==='n'&&u.n<=ABSORB_CAP;})"
    ".sort((a,b)=>dist2(s,a)-dist2(s,b)||a-b);"
    "for(const j of cands){if(budget<=0)break;const u=q.g[j];if(!u||u.side!=='n')continue;"
    "let recv=-1,bestD=Infinity;"
    "for(const i of receivers){const d=dist2(i,j);if(d<bestD||(d===bestD&&i<recv)){bestD=d;recv=i;}}"
    "if(recv<0&&!site.support&&site.n<ABSORB_CAP)recv=s;"
    "if(recv<0)continue;const v=u.n;q.g[j]=null;absorbed++;budget--;"
    "grown+=absorbValue(q,q.g[recv],v,lvCore);}}"
    "for(let i=0;i<N*N;i++){const t=q.g[i];"
    "if(!t||t.side!=='p'||t.support||t.n>=ABSORB_CAP)continue;"
    "let used=0;"
    "for(const d in dirs){if(used>=ABSORB_TP||t.n>=ABSORB_CAP)break;"
    "const j=neighbor(i,d);if(j<0)continue;const u=q.g[j];"
    "if(!u||u.side!=='n'||u.n>ABSORB_CAP)continue;"
    "const v=u.n;q.g[j]=null;absorbed++;used++;grown+=absorbValue(q,t,v,lvCore);}"
    "}"
    "if(grown||absorbed)rescale(q);return grown;}\n"
)

js = (SRC / 'main.script.js').read_text(encoding='utf-8')

js = sub(js, 'function growFighters(q){', NEW_BLOCK + 'function growFighters(q){',
         1, 'engine: absorb helpers + autoCollect inserted')

js = sub(js, 'if(!q.dead)growFighters(q);',
         'if(!q.dead)autoCollect(q);if(!q.dead)growFighters(q);',
         1, 'engine: call absorption after move, before growth')

js = sub(js, '，射程8格。',
         "，射程8格。${t.side==='p'&&!t.support?'吸收上限 '+ABSORB_CAP+'（'+(t.n>=ABSORB_CAP?'已达上限，不再吸收':'可吸收 · 累积 '+(t.payload||0))+'）':''}",
         1, 'engine: hover shows absorption state')

(SRC / 'main.script.js').write_text(js, encoding='utf-8', newline='')
print('engine rewritten: %d chars' % len(js))

# ======================================================================
# 2. patches
# ======================================================================
pat_path = SRC / 'tutorial.patches.py'
pat = pat_path.read_text(encoding='utf-8')

pat = sub(pat, 'if(!q.dead)growFighters(q);',
          'if(!q.dead)autoCollect(q);if(!q.dead)growFighters(q);',
          2, 'patches: call site in both worldStep variants')

pat = sub(pat, 'q.turn++;q.tutorialContacts=(q.tutorialContacts||0)+(r.contacts||0);',
          'q.turn++;if(q.lesson===1&&!q.dead)autoCollect(q);q.tutorialContacts=(q.tutorialContacts||0)+(r.contacts||0);',
          1, 'patches: absorption enabled for the auto-collect lesson only')

pat_path.write_text(pat, encoding='utf-8', newline='')
print('patches updated: %d chars' % len(pat))

# ======================================================================
# 3. tutorial lesson 02 -> teaches auto-collect
# ======================================================================
les_path = SRC / 'tutorial.lessons.js'
les = les_path.read_text(encoding='utf-8')

les = sub(les,
          "{title:'接触才会收编',intro:'相邻不代表归属。推动或合并一个中立块，才会把它纳入你的队伍；散落中立要逐个吃掉。'}",
          "{title:'自动收集',intro:'己方数字未满上限时会自己吸收相邻的中立数字；已经达到上限的方块不再吸收，只能靠推动或合并。'}",
          1, 'lesson02: title + intro')

les = sub(les, 'else if(level===1){for(const i of [5052,5053,5054])add(i,2);}',
          "else if(level===1){add(5051,4,'p');add(4951,2);add(5053,4);}",
          1, 'lesson02: board -> absorber 4, neutral 4, neutral 2 beside the capped core')

les = sub(les,
          "if(q.lesson===1)return !q.g.some(t=>t?.side==='n')&&q.g.some(t=>t?.side==='p'&&!t.core);",
          "if(q.lesson===1)return q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=8)&&q.g.some(t=>t?.side==='n'&&t.n===2);",
          1, 'lesson02: win condition -> absorber upgraded AND capped core left the neutral alone')

les = sub(les,
          "task=s.turn?'继续推，把中立块逐个吃掉':'先向右，靠近中立块';hint=s.turn?'再按 →：同值中立会合并并归你，其余散落中立要逐个推走。':'先按 → 后观察：即使核心已经挨着它们，三个数字仍是中立。';",
          "task=s.turn?'看看满上限的方块会不会吸收':'按 →，观察自动吸收';hint=s.turn?'核心已经是 8，达到上限，它上方的中立 2 不会自动被吃掉——要收编它必须手动推动或合并。':'右下方那个己方 4 会吸收相邻的中立 4 并升到 8；核心 8 已达上限，不参与吸收。';",
          1, 'lesson02: task/hint text')

les = sub(les, "s.lesson===1&&s.turn===1&&neutral===3?'观察成功：相邻时仍有3个中立数字。'",
          "s.lesson===1&&s.turn===1&&neutral===1?'观察成功：4 已升到 8，而满上限的核心没有吸收旁边的中立。'",
          1, 'lesson02: observation message')

les = sub(les, "q.lesson===1?q.g.map((t,i)=>t?.side==='n'?i:-1).filter(i=>i>=0)",
          "q.lesson===1?q.g.map((t,i)=>t&&(t.side==='n'||(t.side==='p'&&!t.core))?i:-1).filter(i=>i>=0)",
          1, 'lesson02: highlight the absorber as well as the neutrals')

les_path.write_text(les, encoding='utf-8', newline='')
print('lessons updated: %d chars' % len(les))

# ======================================================================
# 4. guide: player-facing manual
# ======================================================================
g_path = SRC / 'guide.html'
guide = g_path.read_text(encoding='utf-8')

guide = sub(guide, '<h3>实心底色与整体轮廓</h3>',
            '<h3>自动收集：贴身吸收与站点半径</h3><p>'
            '己方方块数字<strong>未达吸收上限（8）</strong>时，每回合自动吸收四向相邻的中立数字：'
            '中立消失，数值计入该方块的累积量；累积到当前数字即翻倍升级。'
            '升级后血量<strong>按比例保留，不回满</strong>。已达上限的方块不再吸收，只能靠推动或合并。</p>'
            '<p>收集站与分核心另外提供<strong>收集半径</strong>：半径内的中立会被吸给半径内最近的、'
            '仍未达上限的己方方块。每个站点每回合有<strong>吞吐上限</strong>，'
            '所以半径买到的是覆盖面，不能替代经营。</p>'
            '<h3>实心底色与整体轮廓</h3>',
            1, 'guide: auto-collect section')

g_path.write_text(guide, encoding='utf-8', newline='')
print('guide updated: %d chars' % len(guide))

# ======================================================================
# 5. headless tooling export list
# ======================================================================
be = ROOT / 'tools' / 'build_engine.py'
txt = be.read_text(encoding='utf-8')
if "'autoCollect'" not in txt:
    txt = txt.replace("'neutralClusters', 'enemySlots'",
                      "'neutralClusters', 'autoCollect', 'absorbValue', 'ringCells', 'enemySlots'", 1)
    if "'autoCollect'" not in txt:
        fail('tools/build_engine.py: export anchor not found')
    be.write_text(txt, encoding='utf-8', newline='')
    applied.append('tools/build_engine.py export list')
    print('tools/build_engine.py export list updated')

print()
print('STEP 2 EDITS APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
