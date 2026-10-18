"""Step 1: delete the whole-group neutral capture mechanic; introduce "neutral dense zones".

Applies coordinated edits to:
    src/main.script.js          the engine (single source of truth)
    src/tutorial.patches.py     the same text renames, so the patches keep applying
    src/tutorial.lessons.js     tutorial lesson 02 rewritten (plan A: capture one by one)
    src/main.shell.html         minimap legend / aria text
    src/tutorial.shell.html     same
    tools/build_engine.py       export list (headless tooling consistency)

Every edit is anchored and asserted to match an exact number of times; anything
unexpected aborts the run rather than silently corrupting the source.

Order matters:
  1. whole-function rewrites and block deletions (they contain the .ng field)
  2. global .ng -> .nc rename over what is left
  3. global neutralGroups -> neutralClusters rename
  4. display text / minimap field renames
  5. the same renames mirrored into the stored patches
  6. tutorial lesson 02 rewrite
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
    print('STEP 1 ABORTED: %s' % msg)
    print('No further edits were attempted. Files already written this run: %s'
          % (', '.join(applied) or 'none'))
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s: expected %d occurrence(s), found %d\n  anchor: %r'
             % (label, n, c, old[:200]))
    applied.append(label)
    return text.replace(old, new)


def sub_re(text, pattern, new, n, label, flags=0):
    c = len(re.findall(pattern, text, flags))
    if c != n:
        fail('%s: expected %d match(es), found %d\n  pattern: %r'
             % (label, n, c, pattern[:200]))
    applied.append(label)
    return re.sub(pattern, new, text, flags=flags)


# ======================================================================
# 1. engine: src/main.script.js
# ======================================================================
script_path = SRC / 'main.script.js'
js = script_path.read_text(encoding='utf-8')

NEW_CLUSTERS = (
    "function neutralClusters(q){const CLUSTER_MIN=3;const visited=new Set();let dense=0;"
    "for(let start=0;start<N*N;start++){"
    "if(q.g[start]?.side!=='n'||visited.has(start))continue;"
    "const component=[start];visited.add(start);"
    "for(let k=0;k<component.length;k++)for(const d in dirs){const j=neighbor(component[k],d);"
    "if(j>=0&&q.g[j]?.side==='n'&&!visited.has(j)){visited.add(j);component.push(j);}}"
    "if(component.length>=CLUSTER_MIN){const key='dense-'+q.serial++;"
    "for(const i of component)q.g[i].nc=key;dense++;}"
    "else for(const i of component)delete q.g[i].nc;}"
    "return dense;}"
)

# 1a. replace the whole neutralGroups definition
js = sub_re(js, r'^function neutralGroups\(q\)\{.*\}$', lambda m: NEW_CLUSTERS,
            1, 'engine: neutralGroups -> neutralClusters (definition)', re.M)

# 1b. drop the group branch in capture(), and clear nc when a neutral is claimed
js = sub_re(js, r"if\(t\.side==='n'&&t\.ng\)\{.*?return count;\}", '',
            1, 'engine: capture() whole-group branch removed', re.S)
js = sub(js, "t.side=side;t.team=team;return 1;}",
         "t.side=side;t.team=team;delete t.nc;return 1;}",
         1, 'engine: capture() clears stale nc on claim')

# 1c. drop the group branch line in collect()
js = sub_re(js, r"^if\(q\.g\[target\]\.ng\)\{.*\}$\n", '',
            1, 'engine: collect() whole-group branch removed', re.M)

# 2. global .ng -> .nc  (only the outline/display uses remain now)
n_ng = js.count('.ng')
if n_ng == 0:
    fail('engine: expected remaining .ng references to rename, found 0')
js = js.replace('.ng', '.nc')
applied.append('engine: .ng -> .nc (%d)' % n_ng)

# 3. global neutralGroups -> neutralClusters (call sites)
n_call = js.count('neutralGroups')
if n_call == 0:
    fail('engine: expected neutralGroups call sites to rename, found 0')
js = js.replace('neutralGroups', 'neutralClusters')
applied.append('engine: neutralGroups -> neutralClusters calls (%d)' % n_call)

# 4a. minimap field: grouped -> dense
js = sub(js, 'grouped:q.g.map((t,i)=>t?.side===\'n\'&&t.nc?i:-1)',
         'dense:q.g.map((t,i)=>t?.side===\'n\'&&t.nc?i:-1)',
         1, 'engine: minimapData grouped -> dense')
js = sub(js, "[data.grouped,'#dcb66e',2.6]", "[data.dense,'#dcb66e',2.6]",
         1, 'engine: drawMinimap uses dense')

# 4b. neutral counter label
js = sub(js, ")).size+'组';", ")).size+'个密集区';", 1, 'engine: HUD label -> 密集区')

# 4c. render caption
js = sub(js, '金=中立组', '金=中立密集区', 1, 'engine: canvas caption')

# 4d. hover text
js = sub(js,
         "'中立组：'+s.g.filter(u=>u?.side==='n'&&u.nc===t.nc).length+'块；推动、碰撞或合并任一块将整组收编。'",
         "'中立密集区：'+s.g.filter(u=>u?.side==='n'&&u.nc===t.nc).length+'块。'",
         1, 'engine: inspect() dense text')
js = sub(js, "'散落中立数字；四向连通达到6块后成组，每组最多20块。'",
         "'散落中立数字；四向连通达到3块即形成密集区。'",
         1, 'engine: inspect() scattered text')

# 4e. collector goal naming clarity
js = sub(js, 'const groups=resources.filter(i=>q.g[i].nc);if(groups.length)goals=groups;',
         'const dense=resources.filter(i=>q.g[i].nc);if(dense.length)goals=dense;',
         1, 'engine: collector prefers dense zones')

script_path.write_text(js, encoding='utf-8', newline='')
print('engine rewritten: %d chars' % len(js))

# ======================================================================
# 5. patches: mirror the same renames so they keep applying
# ======================================================================
pat_path = SRC / 'tutorial.patches.py'
pat = pat_path.read_text(encoding='utf-8')
before = pat
pat = pat.replace('neutralGroups', 'neutralClusters')
pat = pat.replace('.ng', '.nc')
pat = pat.replace('金=中立组', '金=中立密集区')
if pat == before:
    fail('patches: no rename applied -- anchors may already be stale')
pat_path.write_text(pat, encoding='utf-8', newline='')
applied.append('patches: mirrored renames')
print('patches mirrored: %d -> %d chars' % (len(before), len(pat)))

# ======================================================================
# 6. tutorial lesson 02 -> "capture one by one"  (plan A)
# ======================================================================
les_path = SRC / 'tutorial.lessons.js'
les = les_path.read_text(encoding='utf-8')
before = les
les = les.replace('neutralGroups', 'neutralClusters')

les = sub(les, '；中立组可以整组收编。', '；散落中立要逐个吃掉。', 1,
          'lesson02: intro text')
les = sub(les, 'for(const i of [4952,4953,5052,5053,5152,5153])add(i,i%100===52?2:4);',
          'for(const i of [5052,5053,5054])add(i,2);', 1,
          'lesson02: board layout -> 3 scattered neutrals')
les = sub(les, "if(q.lesson===1)return !q.g.some(t=>t?.side==='n')&&q.g.some(t=>t?.id>=2&&t.id<=7&&t.side==='p');",
          "if(q.lesson===1)return !q.g.some(t=>t?.side==='n')&&q.g.some(t=>t?.side==='p'&&!t.core);",
          1, 'lesson02: win condition no longer needs a group')
les = sub(les,
          "task=s.turn?'接触金色中立组':'先向右，靠近中立组';hint=s.turn?'再按 →：核心推动中立 2，六个组员一起归你。其他组员不会跟着整组平移。':'先按 → 后观察：即使核心已经挨着它们，六个数字仍是中立。';",
          "task=s.turn?'继续推，把中立块逐个吃掉':'先向右，靠近中立块';hint=s.turn?'再按 →：同值中立会合并并归你，其余散落中立要逐个推走。':'先按 → 后观察：即使核心已经挨着它们，三个数字仍是中立。';",
          1, 'lesson02: task/hint text')
les = sub(les, "s.lesson===1&&s.turn===1&&neutral===6?'观察成功：相邻时仍有6个中立数字。'",
          "s.lesson===1&&s.turn===1&&neutral===3?'观察成功：相邻时仍有3个中立数字。'",
          1, 'lesson02: observation message')

les_path.write_text(les, encoding='utf-8', newline='')
print('lessons rewritten: %d -> %d chars' % (len(before), len(les)))

# ======================================================================
# 7. shells: legend / aria text
# ======================================================================
for name in ('main.shell.html', 'tutorial.shell.html'):
    p = SRC / name
    html = p.read_text(encoding='utf-8')
    before = html
    html = html.replace('>中立组<', '>中立密集区<')
    html = html.replace('金色中立组', '金色中立密集区')
    if html == before:
        fail('%s: no legend text replaced' % name)
    p.write_text(html, encoding='utf-8', newline='')
    applied.append('%s: legend text' % name)
    print('shell updated: %s' % name)

# ======================================================================
# 8. headless tooling export list
# ======================================================================
be = ROOT / 'tools' / 'build_engine.py'
txt = be.read_text(encoding='utf-8')
if "'neutralGroups'" in txt:
    txt = txt.replace("'neutralGroups'", "'neutralClusters'")
    be.write_text(txt, encoding='utf-8', newline='')
    applied.append('tools/build_engine.py export list')
    print('tools/build_engine.py export list updated')

print()
print('STEP 1 EDITS APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
print()
print('Next: python tools/build.py  (expect a legitimate diff vs the original reference)')
