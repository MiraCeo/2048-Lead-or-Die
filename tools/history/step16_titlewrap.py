"""修面板标题折行：去掉 h2 的字距。

看图发现：「COMMAND / 当前控制核心」折行，末尾的「心」被单独挤到第二行。
算下来 11px 粗体下约 157px，而面板可用宽度只有 152px（180 − padding 28）。

字距 1px × 18 个字符 ≈ 18px —— 去掉它就能同时解决两处：
  · 「当前控制核心」溢出（157 → 139px，装得下）
  · 「切换与回到核心」只差 2px 的险情（150 → 132px，有富余）
且不增加任何垂直空间（改成两行标题会多吃掉约 70px，可能破坏"一屏放得下"）。

字号与颜色保留（用户上一轮确认"还可以"）。
"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'src' / 'main.shell.html'
sh = p.read_text(encoding='utf-8')

OLD = 'h2{margin:0 0 14px;font-size:11px;letter-spacing:1px;color:#9db18f;font-weight:600}'
NEW = 'h2{margin:0 0 14px;font-size:11px;letter-spacing:0;color:#9db18f;font-weight:600}'

c = sh.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(sh.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('已改：面板标题去掉字距（字号与颜色保留）')
