"""同步外壳测试：面板标题的字距已从 1px 改为 0。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_shell.js'
t = p.read_text(encoding='utf-8')

OLD = "  check(HTML.includes('font-size:11px;letter-spacing:1px'), '面板标题字号与字距已放大');"
NEW = ("  check(HTML.includes('font-size:11px;letter-spacing:0'),\n"
       "        '面板标题字号已放大、字距已归零（否则长标题会折行）');\n"
       "  check(!HTML.includes('letter-spacing:1px'), '不再有 1px 字距（那会让标题多出约 18px）');")

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('test_shell.js 已同步')
