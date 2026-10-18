"""界面优化第一轮：信息重复与命名 + 操作反馈上移。

范围（任务书里我核实成立的条目）：
  §五.1 世界／视野尺寸重复 —— 顶部徽标删掉（棋盘左上右下已各表一次，视野范围另有 #targetCount）
  §五.2 当前核心 vs 共享 core —— 改成"当前控制核心""全队共享 core"
  §五.3 目标进度 —— 改成"最高合成值"（它读的是历史最高值）
  §五.4 行动点固定规则重复 —— 副标题精简，规则移入悬浮提示
  §五.6 固定补给／增援规则重复 —— 战场面板底部那两行删掉（游戏介绍里已完整讲）
  §五.8 中英文标题过小 —— 面板标题 10px/字距2px -> 11px/字距1px，并提亮
  附：装饰性英文副标题与页脚改为中文
  §二.3 操作反馈 —— 把预览提示与状态条移到棋盘上方（P0 的一部分）

另含：核心从血量配色中排除（你的要求）。

安全区（纯 CSS／markup）全部落在 src/main.shell.html；
唯一的引擎改动是核心排除，它在被补丁覆盖的那一行里，改完要重新锚定。
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


# ==================================================== 引擎：核心排除血量配色
js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')
js = sub(js, "if(t.side==='p'&&t.hp<t.cap){const hr=t.hp/t.cap;",
         "if(t.side==='p'&&!t.core&&t.hp<t.cap){const hr=t.hp/t.cap;",
         1, '核心保持原色（从血量配色中排除）')
js_path.write_text(js, encoding='utf-8', newline='')
print('引擎已改写：%d 字符' % len(js))

# ==================================================== 外壳
shell_path = SRC / 'main.shell.html'
sh = shell_path.read_text(encoding='utf-8')

# --- 面板标题可读性（CSS）
sh = sub(sh, 'h2{margin:0 0 16px;font-size:10px;letter-spacing:2px;color:var(--muted);font-weight:500}',
         'h2{margin:0 0 14px;font-size:11px;letter-spacing:1px;color:#9db18f;font-weight:600}',
         1, '面板标题：10px/字距2px -> 11px/字距1px 并提亮')

# --- 顶部：删掉与世界/视野重复的徽标
sh = sub(sh, '<div class="header-actions"><span class="badge">100 × 100 世界 · 25 × 25 视野</span>',
         '<div class="header-actions">',
         1, '顶部删掉重复的世界／视野徽标')

# --- 装饰英文 -> 中文副标题
sh = sub(sh, '<div class="en">CORE ARCHIPELAGO / EXPEDITION 10 / CONTACT & SUPPORT</div>',
         '<div class="en">2048 远征 · 合成 · 收编 · 扩张</div>',
         1, '副标题改为中文玩法说明')

# --- 命名
sh = sub(sh, '<h2>COMMAND / 当前核心</h2>', '<h2>COMMAND / 当前控制核心</h2>',
         1, '「当前核心」->「当前控制核心」')
sh = sub(sh, '<span>共享 core</span>', '<span>全队共享 core</span>',
         1, '「共享 core」->「全队共享 core」')
sh = sub(sh, '<span>目标</span>', '<span>最高合成值</span>',
         1, '「目标」->「最高合成值」')

# --- 行动点：固定规则移入悬浮提示
sh = sub(sh, '<span class="mini-detail">额外行动点<br>每2回合 +1</span>',
         '<span class="mini-detail" style="cursor:help" title="每 2 次有效主移动获得 1 点">额外行动点</span>',
         1, '行动点固定规则移入悬浮提示')

# --- 战场面板：删掉与游戏介绍重复的固定规则
sh = sub(sh, '<div class="divider"></div><div class="mini-detail">'
             '补给：视野内每2回合 +1，视野外每回合 +3<br>敌方全图均匀增援 · 每20回合友方碉堡支援</div>',
         '',
         1, '战场面板删掉重复的补给／增援固定规则')

# --- 操作反馈上移到棋盘上方（P0 的一部分）
sh = sub(sh, '</canvas></div>'
             '<div id="previewHint" class="mini-detail map-keyhint">WASD / 方向键移动 · 点击己方数字单独调整 · '
             '拖动两块互换 · Esc 返回主体 · Shift + 方向预览</div>'
             '<div id="status" class="status" role="status">正在初始化游戏…若此提示持续显示，请反馈当前页面截图。</div>'
             '</section>',
         '</canvas></div></section>',
         1, '从棋盘下方移走预览提示与状态条')

sh = sub(sh, '</div></div><div class="board">',
         '</div></div>'
         '<div id="previewHint" class="mini-detail map-keyhint">WASD / 方向键移动 · 点击己方数字单独调整 · '
         '拖动两块互换 · Esc 返回主体 · Shift + 方向预览</div>'
         '<div id="status" class="status" role="status">正在初始化游戏…若此提示持续显示，请反馈当前页面截图。</div>'
         '<div class="board">',
         1, '把预览提示与状态条放到棋盘上方')

# --- 页脚英文 -> 中文
sh = sub(sh, '<footer><span>EXPLORATION · FORMATION · 2048</span>',
         '<footer><span>探索 · 编队 · 合成 2048</span>',
         1, '页脚装饰英文改为中文')

shell_path.write_text(sh, encoding='utf-8', newline='')
print('外壳已改写：%d 字符' % len(sh))
print()
print('本次应用 %d 项' % len(applied))
