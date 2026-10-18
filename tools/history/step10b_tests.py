"""同步展示层测试：描边取消、改为血量比例配色。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_display.js'
t = p.read_text(encoding='utf-8')

OLD = ("  check(ENGINE.includes('ctx.strokeText(t,x,y)'), 'text() 支持描边');\n"
       "  check(ENGINE.includes(\"digitColor(t.n),'#f2f7e8'\"), '方块数字带了浅色描边');\n"
       "  check(ENGINE.includes(\"ctx.textBaseline='middle';if(outline)\"),\n"
       "        '描边在设置字体之后执行（否则会沿用上一次的字体）');")

NEW = ("  check(!ENGINE.includes('strokeText'), '描边已取消');\n"
       "  check(!ENGINE.includes(\"'#f2f7e8'\"), '数字不再带描边色');\n"
       "  check(ENGINE.includes(\"if(t.side==='p'&&t.hp<t.cap)\"), '掉血的我方方块按比例变色');\n"
       "  check(ENGINE.includes('hr>HP_HURT?HP_COL_OK:hr>HP_CRIT?HP_COL_HURT:HP_COL_CRIT'),\n"
       "        '三档阈值：绿(>2/3) / 黄(>1/3) / 红(其余)');\n"
       "  check(ENGINE.includes(\"'#8fd98a'\") && ENGINE.includes(\"'#e8cf72'\") && ENGINE.includes(\"'#e07a6a'\"),\n"
       "        '绿/黄/红三色都在场');\n"
       "  check(ENGINE.includes('let fill='), 'fill 改为可覆盖（否则无法按血量改色）');")

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('test_display.js 已同步')
