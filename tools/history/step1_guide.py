"""Step 1 (continued): the game guide document.

Handover doc section 3 lists these guide edits:
  - section 03 "中立组：六块起，整组收编"
  - the trailing section "中立组上限：20块"
plus the minimap legend row that describes grouped neutrals.

First reports every remaining mention of the group mechanic, so nothing is missed.
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
GUIDE = ROOT / 'src' / 'guide.html'

html = GUIDE.read_text(encoding='utf-8')

print('=== mentions of the group mechanic in the guide ===')
for pat in ('中立组', '整组', '成组', '20块', '6块'):
    for m in re.finditer(re.escape(pat), html):
        s = max(0, m.start() - 60)
        print('  %-6s ...%s...' % (pat, html[s:m.end() + 60].replace('\n', ' ')))
print()

applied = []


def sub(old, new, n, label):
    global html
    c = html.count(old)
    if c != n:
        sys.exit('GUIDE EDIT FAILED: %s -- expected %d, found %d\n  anchor: %r'
                 % (label, n, c, old[:180]))
    html = html.replace(old, new)
    applied.append(label)


# 1. section 03 heading
sub('<h2>03 / 归属、分核心与中立组</h2>',
    '<h2>03 / 归属、分核心与中立密集区</h2>',
    1, 'section 03 heading')

# 2. the whole-group sub-mechanism -> dense-zone read-out
sub('<h3>中立组：六块起，整组收编</h3><p>四向连通的中立数字达到6块时自动成组，每组最多20块；'
    '超过时拆成多个独立连通组，新接触的中立数字参与重新分组。推动、碰撞或合并任一成员，就将整组归属转给收编方；'
    '仅操作涉及的方块移动，其他成员位置不变。采集机优先寻找并收编中立组，而不是吞掉整个组。</p>',
    '<h3>中立密集区：三块起，只作标记</h3><p>四向连通的中立数字达到3块即形成密集区，'
    '棋盘上以金色轮廓标出，小地图上也以金色显示大致位置。密集区只回答“哪一片中立值得去”，'
    '不再提供整组收编——每个中立数字都要单独推动、碰撞或合并来收编。采集机优先前往密集区。</p>',
    1, 'section 03 group sub-mechanism')

# 3. outline colour legend sentence
sub('金色是中立组。', '金色是中立密集区。', 1, 'outline legend sentence')

# 4. minimap legend row
sub('<tr><td>金色区域</td><td>成组中立块的大致形状和位置</td></tr>',
    '<tr><td>金色区域</td><td>中立密集区的大致形状和位置</td></tr>',
    1, 'minimap legend row')

# 5. drop the trailing "中立组上限：20块" section entirely
before = len(html)
html, n = re.subn(r'<section><h2>中立组上限：20块</h2>.*?</section>', '', html, flags=re.S)
if n != 1:
    sys.exit('GUIDE EDIT FAILED: trailing 上限 section matched %d times (expected 1)' % n)
applied.append('trailing 中立组上限 section removed (%d chars)' % (before - len(html)))

GUIDE.write_text(html, encoding='utf-8', newline='')

print('GUIDE EDITS APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
print()
print('guide: %d chars' % len(html))
left = [p for p in ('中立组', '整组', '成组', '20块') if p in html]
print('remaining mentions of removed concepts: %s' % (left or 'none'))
