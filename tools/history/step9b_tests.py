"""同步展示层测试：刻度已取消、数字改为带浅色描边。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_display.js'
t = p.read_text(encoding='utf-8')

OLD = "  check(ENGINE.includes('if(t.n<=8)for(let k=1;k<t.n;k++)'), '按 1/n 画档位刻度（n≤8 时）');"
NEW = ("  check(!ENGINE.includes('if(t.n<=8)for(let k=1;k<t.n;k++)'), '档位刻度已取消');\n"
       "  check(ENGINE.includes('ctx.strokeText(t,x,y)'), 'text() 支持描边');\n"
       "  check(ENGINE.includes(\"digitColor(t.n),'#f2f7e8'\"), '方块数字带了浅色描边');\n"
       "  check(ENGINE.includes(\"ctx.textBaseline='middle';if(outline)\"),\n"
       "        '描边在设置字体之后执行（否则会沿用上一次的字体）');")

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('test_display.js 已同步')
