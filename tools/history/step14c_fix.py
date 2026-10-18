"""修 test_shell.js 里的一个语法错误：跨行字符串漏了 + 号。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_shell.js'
t = p.read_text(encoding='utf-8')

OLD = ("  check(HTML.includes('<strong id=\"tech\"></strong><span class=\"mini-detail\">科技点</span></div>'\n"
       "                      '<button id=\"openTech\">打开科技树</button>'),")
NEW = ("  check(HTML.includes('<strong id=\"tech\"></strong><span class=\"mini-detail\">科技点</span></div>'\n"
       "                      + '<button id=\"openTech\">打开科技树</button>'),")

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('已修：补上 + 号')
