"""取消进度条档位刻度；给方块数字加描边。

关于描边的颜色：`digitColor` 返回的是**深色**（2 是 #233d2a、4 是 #185227），
即数字本来是"深字配浅底"。但血量改成背景高度之后，低血方块的上班露出暗底，
深色数字压在暗底上会看不清。所以描边必须用**浅色**：
  - 浅底上：深字 + 浅描边，描边融进底色，看起来就是普通深字；
  - 暗底上：浅描边把深字的轮廓"衬"出来，仍可辨认。

描边宽度按字号自适应（字号小的时候 3px 会把笔画吃掉）。

另外：数字是被补丁覆盖那一行里的内容，所以改完要重新锚定补丁；
text() 本身不在补丁范围内。
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
applied = []


def sub(old, new, n, label):
    global js
    c = js.count(old)
    if c != n:
        print('\n中止：%s：预期 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:200]))
        print('内存中已应用：%s' % (', '.join(applied) or '无'))
        print('注意：尚未写入文件。')
        sys.exit(1)
    js = js.replace(old, new)
    applied.append(label)
    print('已改：%s' % label)


# ---------------------------------------------- 1. 去掉档位刻度
sub("if(t.n<=8)for(let k=1;k<t.n;k++)rect(bx+Math.round(bw*k/t.n),by,1,bh,0,'#16321f',null);",
    "",
    1, '取消进度条的档位刻度')

# ---------------------------------------------- 2. text() 支持描边（向后兼容）
sub("function text(t,x,y,size,color){ctx.fillStyle=color;"
    "ctx.font=`600 ${size}px system-ui`;ctx.textAlign='center';ctx.textBaseline='middle';"
    "ctx.fillText(t,x,y);}",
    "function text(t,x,y,size,color,outline){"
    "ctx.font=`600 ${size}px system-ui`;ctx.textAlign='center';ctx.textBaseline='middle';"
    "if(outline){ctx.lineWidth=Math.max(1.5,Math.min(3,size*0.18));"
    "ctx.strokeStyle=outline;ctx.strokeText(t,x,y);}"
    "ctx.fillStyle=color;ctx.fillText(t,x,y);}",
    1, 'text() 增加可选描边参数（不传则行为不变）')

# ---------------------------------------------- 3. 方块数字加浅色描边
sub("text(fmt(t.n),p.x,p.y+(t.core?-1:-3),"
    "fmt(t.n).length>4?8:fmt(t.n).length>3?10:fmt(t.n).length>2?13:17,digitColor(t.n));",
    "text(fmt(t.n),p.x,p.y+(t.core?-1:-3),"
    "fmt(t.n).length>4?8:fmt(t.n).length>3?10:fmt(t.n).length>2?13:17,"
    "digitColor(t.n),'#f2f7e8');",
    1, '方块数字加浅色描边（浅底暗底都可读）')

p.write_text(js, encoding='utf-8', newline='')
print()
print('引擎已改写：%d 字符' % len(js))
print('本次应用 %d 项' % len(applied))
