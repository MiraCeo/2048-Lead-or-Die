"""Step 1 (continued): remaining guide mention of whole-group capture.

The enemy-unit table still describes the collector as capturing whole neutral groups.
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

GUIDE = Path(r'D:\2048') / 'src' / 'guide.html'
html = GUIDE.read_text(encoding='utf-8')

OLD = '<td>⚒ 采集机</td><td>优先寻找中立组并整组纳入编队；采集相邻零散数字积累升级。</td>'
NEW = '<td>⚒ 采集机</td><td>优先前往中立密集区，采集相邻零散数字积累升级。</td>'

c = html.count(OLD)
if c != 1:
    sys.exit('GUIDE EDIT FAILED: collector row matched %d times (expected 1)' % c)
html = html.replace(OLD, NEW, 1)
GUIDE.write_text(html, encoding='utf-8', newline='')

left = [p for p in ('中立组', '整组', '成组', '20块') if p in html]
print('guide: %d chars' % len(html))
print('collector row updated')
print('remaining mentions of removed concepts: %s' % (left or 'none'))
