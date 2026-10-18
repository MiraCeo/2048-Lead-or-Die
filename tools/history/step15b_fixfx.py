"""修一个真 bug：吸收特效永远不会被画出来。

原因：渲染循环的准入判断是 `if(!visible(f.at,cam))continue;`，
而"吸收"事件的字段是 from / to（没有 at）——`visible(undefined,cam)` 返回 false，
于是吸收特效每一帧都被 continue 掉。

修法：把 shot 与 absorb 这两类"两点型"特效都放在 at 准入之前处理，
剩下的 pulse / regen / hit / kill 才是"单点型"（用 at）。

同时加一条结构断言把这个坑钉死：
"absorb 分支必须出现在 at 准入之前"。
"""
import sys
from pathlib import Path

ROOT = Path(r'D:\2048')
SRC = ROOT / 'src'

OLD = ("if(!visible(f.at,cam))continue;const p=screenPoint(f.at,cam);"
       "if(k==='absorb'){const o=screenPoint(f.from,cam);"
       "ctx.globalAlpha=fade*.8;ctx.strokeStyle='#c8f195';ctx.lineWidth=2;"
       "ctx.beginPath();ctx.moveTo(o.x,o.y);ctx.lineTo(p.x,p.y);ctx.stroke();"
       "ctx.globalAlpha=fade;ctx.fillStyle='#e6ff9c';ctx.beginPath();"
       "ctx.arc(o.x+(p.x-o.x)*age,o.y+(p.y-o.y)*age,2.5,0,6.2832);ctx.fill();}"
       "else if(k==='pulse')")

NEW = ("if(k==='absorb'){if(!visible(f.from,cam)&&!visible(f.to,cam))continue;"
       "const o=screenPoint(f.from,cam),e=screenPoint(f.to,cam);"
       "ctx.globalAlpha=fade*.8;ctx.strokeStyle='#c8f195';ctx.lineWidth=2;"
       "ctx.beginPath();ctx.moveTo(o.x,o.y);ctx.lineTo(e.x,e.y);ctx.stroke();"
       "ctx.globalAlpha=fade;ctx.fillStyle='#e6ff9c';ctx.beginPath();"
       "ctx.arc(o.x+(e.x-o.x)*age,o.y+(e.y-o.y)*age,2.5,0,6.2832);ctx.fill();continue;}"
       "if(!visible(f.at,cam))continue;const p=screenPoint(f.at,cam);"
       "if(k==='pulse')")

p = SRC / 'main.script.js'
js = p.read_text(encoding='utf-8')
c = js.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
js = js.replace(OLD, NEW, 1)
p.write_text(js, encoding='utf-8', newline='')

# 自检：absorb 分支必须排在 at 准入之前
i_absorb = js.find("if(k==='absorb'){")
i_gate = js.find("if(!visible(f.at,cam))continue;const p=screenPoint(f.at,cam);")
if i_absorb < 0 or i_gate < 0 or i_absorb > i_gate:
    sys.exit('自检失败：absorb 分支没有排在 at 准入之前（absorb=%d gate=%d）' % (i_absorb, i_gate))
print('已修：吸收特效改为在 at 准入之前处理（两点型特效）')
print('自检通过：absorb 分支位于 at 准入之前')
