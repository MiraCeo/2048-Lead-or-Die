"""收窄断言：只检查 h2 规则里不再有 1px 字距。

原来那条 `!HTML.includes('letter-spacing:1px')` 太宽 —— 页脚上本来就有一处 1px 字距，
与面板标题无关，结果误报。
"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_shell.js'
t = p.read_text(encoding='utf-8')

OLD = "  check(!HTML.includes('letter-spacing:1px'), '不再有 1px 字距（那会让标题多出约 18px）');"
NEW = ("  check(!/h2\\{[^}]*letter-spacing:1px/.test(HTML),\n"
       "        'h2 规则里不再有 1px 字距（那会让标题多出约 18px）');\n"
       "  check(/h2\\{[^}]*letter-spacing:0/.test(HTML), 'h2 字距明确为 0');")

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('test_shell.js 断言已收窄')
