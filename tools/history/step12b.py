"""修掉一处漏网：clearPreview() 会把整段 WASD 说明写回 #previewHint。

你在反馈里说"WASD 的操作方式不要放到棋盘上方"，我删掉了 markup 里的静态文字，
但 clearPreview() 在每次结束预览时又把它写回去了 —— 于是任何一次 Shift 预览之后，
那段说明就会永久留在棋盘上方。这里改成清空，只保留「预览结果」这一用途。
"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'src' / 'main.script.js'
js = p.read_text(encoding='utf-8')

OLD = ("$('previewHint').textContent='WASD / 方向键移动 · 点击己方数字单独调整 · "
       "拖动两块互换 · Esc 返回主体 · Shift + 方向预览';")
NEW = "$('previewHint').textContent='';"

c = js.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(js.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('已改：clearPreview() 改为清空预览位，不再写回操作说明')
