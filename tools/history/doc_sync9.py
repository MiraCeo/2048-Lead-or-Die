"""项目文档同步：刻度取消、数字改浅色描边。"""
import re
import sys
from pathlib import Path

DOC = Path(r'D:\2048') / '项目文档.md'
t = DOC.read_text(encoding='utf-8')
log = []


def sub_re(pattern, new, label, flags=0):
    global t
    n = len(re.findall(pattern, t, flags))
    if n != 1:
        sys.exit('%s：预期 1 次，实际 %d 次' % (label, n))
    t = re.sub(pattern, new, t, count=1, flags=flags)
    log.append(label)


sub_re(r'^\| 进度刻度 \| 按 `1/n` 画\*\*档位刻度\*\*（n ≤ 8 时），让 0/1/2/3/4 这种小整数进度可数 \|$',
       '| 数字描边 | 方块数字加**浅色描边**：低血方块的上半露出暗底，深色数字必须有浅色衬托才看得清 |',
       '§12.6 表格：进度刻度 -> 数字描边', re.M)

sub_re(r'^\| 进度值是小整数（阈值 4 之下是 0/1/2/3/4），细线表达不了 \| 按 `1/n` 画\*\*档位刻度\*\*（n ≤ 8 时），让进度可数 \|$',
       '| 数字在低血方块上会压到暗底（数字本身是深色，底色是浅色） | 改成**浅色描边**；'
       '曾试过加档位刻度，你判断不需要，**已取消** |',
       '§13.4 表格：刻度 -> 描边', re.M)

DOC.write_text(t, encoding='utf-8', newline='')
print('项目文档已同步：')
for a in log:
    print('  - %s' % a)
