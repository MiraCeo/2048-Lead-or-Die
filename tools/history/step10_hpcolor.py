"""取消数字描边；改为按血量比例给我方方块上色（绿 / 黄 / 红）。

理解与实现位置：
  方块的颜色就是那条"按血量高度"的填充，所以按比例变色就是让这段填充变色。
  - 满血的我方方块：保持原来的阵营色（不变）
  - 掉血的我方方块：填充转为 绿(>2/3) / 黄(>1/3) / 红(<=1/3)
  这是标准的血条配色，和"血量=背景高度"叠加，低血方块会变成"大面积暗底 + 一小段红"。

颜色与阈值都是具名常量，方便你试玩后调。

注意：填充色一变，"友方碉堡"原本的蓝色身份会被血量色覆盖，图例里那一条会不再成立。
我先按字面（所有我方方块）实现，并在文档里标出来；要排除建筑的话是一行的事。
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


# ---------------------------------------------- 1. 取消描边（text 恢复原样）
sub("function text(t,x,y,size,color,outline){"
    "ctx.font=`600 ${size}px system-ui`;ctx.textAlign='center';ctx.textBaseline='middle';"
    "if(outline){ctx.lineWidth=Math.max(1.5,Math.min(3,size*0.18));"
    "ctx.strokeStyle=outline;ctx.strokeText(t,x,y);}"
    "ctx.fillStyle=color;ctx.fillText(t,x,y);}",
    "function text(t,x,y,size,color){ctx.fillStyle=color;"
    "ctx.font=`600 ${size}px system-ui`;ctx.textAlign='center';ctx.textBaseline='middle';"
    "ctx.fillText(t,x,y);}",
    1, 'text() 恢复原样（取消描边参数）')

sub("text(fmt(t.n),p.x,p.y+(t.core?-1:-3),"
    "fmt(t.n).length>4?8:fmt(t.n).length>3?10:fmt(t.n).length>2?13:17,"
    "digitColor(t.n),'#f2f7e8');",
    "text(fmt(t.n),p.x,p.y+(t.core?-1:-3),"
    "fmt(t.n).length>4?8:fmt(t.n).length>3?10:fmt(t.n).length>2?13:17,"
    "digitColor(t.n));",
    1, '方块数字不再传描边')

# ---------------------------------------------- 2. 血量配色的常量
sub("function tileBody(p,half,size,rad,fill,stroke,t){",
    "const HP_HURT=0.66,HP_CRIT=0.33,"
    "HP_COL_OK='#8fd98a',HP_COL_HURT='#e8cf72',HP_COL_CRIT='#e07a6a';\n"
    "function tileBody(p,half,size,rad,fill,stroke,t){",
    1, '血量配色的颜色与阈值改为具名常量')

# ---------------------------------------------- 3. 掉血的我方方块按比例变色
sub("const fill=t.support?(t.structure?'#96c5e5':'#b5d4e6'):"
    "t.side==='e'?(t.core?'#e8a28c':'#edb8a5'):"
    "t.side==='n'?(t.nc?'#e4d4a8':'#bdc7ad'):"
    "t.core?'#f0d18e':member?'#c5e29c':'#abd5dd';",
    "let fill=t.support?(t.structure?'#96c5e5':'#b5d4e6'):"
    "t.side==='e'?(t.core?'#e8a28c':'#edb8a5'):"
    "t.side==='n'?(t.nc?'#e4d4a8':'#bdc7ad'):"
    "t.core?'#f0d18e':member?'#c5e29c':'#abd5dd';"
    "if(t.side==='p'&&t.hp<t.cap){const hr=t.hp/t.cap;"
    "fill=hr>HP_HURT?HP_COL_OK:hr>HP_CRIT?HP_COL_HURT:HP_COL_CRIT;}",
    1, '掉血的我方方块按血量比例改为绿/黄/红')

p.write_text(js, encoding='utf-8', newline='')
print()
print('引擎已改写：%d 字符' % len(js))
print('本次应用 %d 项' % len(applied))
