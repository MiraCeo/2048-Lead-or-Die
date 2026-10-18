"""把敌方采集机的天花板改成与玩家同一形态。

玩家规则（你确认过的底层规则）：数字 <= 阈值可吸收，升级后超过阈值则进度清零，
所以自动可达上限是阈值的两倍。

我上一步给采集机写的是旧式判据 `n*2 <= 天花板`，那等于上限恰好等于天花板本身——
只有玩家的一半，不符合你要的"形式对称"。

这里改成同一形态：只要进度够就升级，升级后超过天花板则进度清零并停止。
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SRC = Path(r'D:\2048') / 'src'
p = SRC / 'main.script.js'
js = p.read_text(encoding='utf-8')

OLD = ('while(t.payload>=t.n&&t.n*2<=aiAbsorbCeiling(q)){t.payload-=t.n;'
       'const oldCap=t.cap||1,oldHp=t.hp??oldCap;t.n*=2;'
       't.cap=3**lvl(t.n)*lvl(t.n);'
       't.hp=Math.max(1,Math.min(t.cap,Math.round(oldHp*t.cap/oldCap)));'
       'log(q,`采集机升级 · core=${t.n}`);}')

NEW = ('while(t.payload>=t.n){t.payload-=t.n;'
       'const oldCap=t.cap||1,oldHp=t.hp??oldCap;t.n*=2;'
       't.cap=3**lvl(t.n)*lvl(t.n);'
       't.hp=Math.max(1,Math.min(t.cap,Math.round(oldHp*t.cap/oldCap)));'
       'log(q,`采集机升级 · core=${t.n}`);'
       'if(t.n>aiAbsorbCeiling(q)){t.payload=0;break;}}')

c = js.count(OLD)
if c != 1:
    sys.exit('对称性修复失败：锚点命中 %d 次（预期 1）' % c)

p.write_text(js.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('敌方采集机天花板已改为与玩家同形态（可达两倍天花板）')
