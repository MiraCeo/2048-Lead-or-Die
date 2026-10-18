"""画布：删掉顶部的世界/视野标签，去掉下方留空，让画布尽量充满且完整。

你的要求：
  1 画布上方的 100×100 与 25×25 删掉
  2 坐标先留着（棋盘四周的行列号）
  3 画布下方不要留空
  4 尽量让画布充满屏幕但保持完整

做法：
  - 顶部两个标签整体删掉。其中右边那个原本兼作"模式指示"，
    但顶栏的 #modeLabel 已经在显示模式，预览状态另有 #previewHint，
    所以它是重复的，可以整体删。
  - 画布本来 860×886：网格下方到 y=843，再往下 43px 是刚才删掉的那两行规则文字
    留下的余量。把画布高度改成 860（下方只剩 17px），这块空就没了。
  - X / Y / C 三个坐标常量**不动**（网格几何不变），只改画布高度与随它走的三处映射。

886 一共有四处：shell 的 canvas 属性、draw 的 clearRect/fillRect、
indexFromEvent 的换算、pointermove 里的换算。四处必须一起改。

draw 那一行被教程补丁覆盖，改完要重新锚定。
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
SRC = ROOT / 'src'
applied = []


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        print('\n中止：%s：预期 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:200]))
        print('内存中已应用：%s' % (', '.join(applied) or '无'))
        print('注意：尚未写入任何文件。')
        sys.exit(1)
    applied.append(label)
    print('已改：%s' % label)
    return text.replace(old, new)


# ==================================================== 引擎
js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')

js = sub(js,
         "ctx.clearRect(0,0,860,886);ctx.fillStyle='#111d18';ctx.fillRect(0,0,860,886);"
         "text('EXPEDITION SECTOR / 100 × 100',205,17,10,'#819979');"
         "text(preview?'MOVEMENT PREVIEW / 战斗未结算':mode!=='main'?"
         "'EXTRA ACTION / TIME FROZEN':'CORE-CENTERED VIEW / 25 × 25',640,17,10,'#bad6a1');",
         "ctx.clearRect(0,0,860,860);ctx.fillStyle='#111d18';ctx.fillRect(0,0,860,860);",
         1, '删掉画布顶部两个标签 + 画布高度 886 -> 860')

js = sub(js, "(e.clientY-box.top)*886/box.height,c=Math.floor((x-X)/C)",
         "(e.clientY-box.top)*860/box.height,c=Math.floor((x-X)/C)",
         1, 'indexFromEvent 的高度换算跟进')

js = sub(js, "drag.y=(e.clientY-box.top)*886/box.height;",
         "drag.y=(e.clientY-box.top)*860/box.height;",
         1, '拖拽坐标换算跟进')

js_path.write_text(js, encoding='utf-8', newline='')
print('引擎已改写：%d 字符' % len(js))

# ==================================================== 外壳
shell_path = SRC / 'main.shell.html'
sh = shell_path.read_text(encoding='utf-8')
sh = sub(sh, '<canvas id="canvas" width="860" height="886"',
         '<canvas id="canvas" width="860" height="860"',
         1, '画布元素高度属性跟进')
shell_path.write_text(sh, encoding='utf-8', newline='')
print('外壳已改写：%d 字符' % len(sh))

print()
print('本次应用 %d 项' % len(applied))
