"""同步展示层测试：核心已从血量配色排除，断言要跟上。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_display.js'
t = p.read_text(encoding='utf-8')

OLD = "  check(ENGINE.includes(\"if(t.side==='p'&&t.hp<t.cap)\"), '掉血的我方方块按比例变色');"
NEW = ("  check(ENGINE.includes(\"if(t.side==='p'&&!t.core&&t.hp<t.cap)\"),\n"
       "        '掉血的我方方块按比例变色，且核心已排除（核心保持原色）');")

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('test_display.js 已同步')
