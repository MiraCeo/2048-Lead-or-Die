"""界面优化第二轮：按你 5 点反馈改。

你的反馈：
  1 面板标题放大后还可以 -> 保留
  2 状态条删掉（冗余没用）
  3 WASD 操作方式不要放棋盘上方（占地方、不方便看）
  4 100% 缩放下棋盘仍无法一屏放下
  5 规则能搬进游戏介绍就搬进去，不要一直挂在游戏界面

处理：
  2 状态条不是"直接删元素"——那样 say() 会全线失效，
    无效操作的提示（"行动点不足""该方向没有有效主移动"）就都没了。
    任务书自己写着"不要仅仅通过删除信息来降低密度，优先考虑分层、折叠、悬浮提示"，
    所以改成**不占任何布局空间的临时悬浮提示**（出现后约 2.6 秒淡出），
    并去掉每回合那行例行汇报（那才是"冗余没用"的部分）。
  3 棋盘上方只保留 #previewHint 这个元素用于显示「移动预览结果」，
    默认空着、不再占位（静态的 WASD 说明搬进游戏介绍）。
  4 不再用魔法数字算棋盘尺寸：改成让浏览器按可用高度算
    （canvas 用 max-width/max-height 等比缩放，固定开销抽成一个可调变量），
    再加上 2、3 两处释放出来的垂直空间。
  5 把画布底部的两条规则文字、科技点来源、小地图提示等搬进游戏介绍。
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


# ==================================================== 外壳
shell_path = SRC / 'main.shell.html'
sh = shell_path.read_text(encoding='utf-8')

NEW_CSS = (
    "/* 本轮：棋盘尺寸交给浏览器算；状态条改为不占位的临时浮层；棋盘上方不再常驻操作提示 */\n"
    ".play-area{position:relative}\n"
    ".feedback{position:absolute;left:50%;transform:translateX(-50%);top:6px;z-index:3;"
    "pointer-events:none;max-width:92%;background:#0d1a14f2;border:1px solid #3a503e;"
    "border-radius:8px;padding:6px 12px;font-size:11px;line-height:1.6;color:#dbe8cd;"
    "opacity:0;transition:opacity .22s}\n"
    ".feedback.show{opacity:1}\n"
    "#previewHint{min-height:0;padding-top:0}\n"
    ".board{width:100%;min-width:0;max-width:none;display:flex;justify-content:center;align-items:flex-start}\n"
    ".board canvas{width:auto;height:auto;max-width:100%;"
    "max-height:calc(100dvh - var(--board-chrome,230px))}\n"
)
sh = sub(sh, '</style></head><body>', NEW_CSS + '</style></head><body>',
         1, '追加本轮 CSS：临时浮层 + 棋盘尺寸交给浏览器')

sh = sub(sh,
         '<div id="previewHint" class="mini-detail map-keyhint">WASD / 方向键移动 · 点击己方数字单独调整 · '
         '拖动两块互换 · Esc 返回主体 · Shift + 方向预览</div>'
         '<div id="status" class="status" role="status">正在初始化游戏…若此提示持续显示，请反馈当前页面截图。</div>',
         '<div id="feedback" class="feedback" role="status" aria-live="polite"></div>'
         '<div id="previewHint" class="mini-detail map-keyhint"></div>',
         1, '删掉状态条；棋盘上方只留预览结果位（默认空）')

sh = sub(sh, '<span class="mini-detail">科技点<br>击破核心/碉堡 · 探索新区块 · 兑换积分</span>',
         '<span class="mini-detail" style="cursor:help" '
         'title="击破敌方核心或碉堡、探索新区块、用合成分兑换">科技点</span>',
         1, '科技点来源改为悬浮提示（规则搬进介绍）')

sh = sub(sh, '<div id="inspect" class="inspect">悬停数字查看归属、血量和编队规模。</div>',
         '<div id="inspect" class="inspect">悬停数字查看单位详情。</div>',
         1, '扫描面板占位文案精简')

sh = sub(sh, '<div class="mini-detail" style="margin-top:9px">点击绿色核心标记切换视野</div>',
         '',
         1, '小地图提示搬进游戏介绍')

shell_path.write_text(sh, encoding='utf-8', newline='')
print('外壳已改写：%d 字符' % len(sh))

# ==================================================== 引擎
js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')

js = sub(js, "function say(t){$('status').textContent=t;}",
         "let fbTimer=null;function say(t){const el=$('feedback');if(!el)return;"
         "el.textContent=t;el.classList.add('show');"
         "if(fbTimer)clearTimeout(fbTimer);"
         "fbTimer=setTimeout(()=>el.classList.remove('show'),2600);}",
         1, 'say() 改为临时悬浮提示（不占布局空间）')

js = sub(js,
         "say(`回合 ${s.turn} · 对碰 ${r.contacts||0} 次 · 合并 ${r.merges} 次 · "
         "收编 ${r.recruited} 块 · 己方射击 ${r.playerShots} 次"
         "${s.turn%2===0?' · 敌方已行动':' · 常规敌方下回合行动，碉堡可开火'}`);",
         "",
         1, '去掉每回合的例行汇报（那才是冗余的部分）')

js = sub(js,
         "paintDrag(q,cam);text('实心底色区分阵营 · 整体轮廓：绿=主体 / 蓝=其他己方 / 红=敌军 / "
         "金=中立密集区',430,862,10,'#8fa883');"
         "text('视野跟随核心 · 射程8格 · 补给内每2回合1 / 外每回合3 · 碉堡每回合射击',430,880,9,'#647e60');}",
         "paintDrag(q,cam);}",
         1, '画布底部的规则文字搬进游戏介绍')

js_path.write_text(js, encoding='utf-8', newline='')
print('引擎已改写：%d 字符' % len(js))

# ==================================================== 游戏介绍：接收搬过来的规则
g_path = SRC / 'guide.html'
g = g_path.read_text(encoding='utf-8')

g = sub(g, '<nav><a href="#start">快速开始</a>',
        '<nav><a href="#start">快速开始</a><a href="#ui">画面与科技</a>',
        1, '游戏介绍导航加入新章节')

NEW_SEC = (
    '<section id="ui"><h2>08 / 画面读法、小地图与科技点</h2>'
    '<h3>棋盘读法</h3><p>方块的<strong>实心底色</strong>区分阵营，'
    '<strong>整体轮廓</strong>：绿＝主体，蓝＝其他己方，红＝敌军，金＝中立密集区。'
    '方块<strong>背景颜色的高度</strong>表示剩余血量（剩一半血就只有下半有色），'
    '方块下方的细条是<strong>升级进度</strong>，画成满格灰表示该方块已超过阈值、不再吸收。'
    '掉血的我方方块会按血量比例转为绿／黄／红；核心保持原色不变。</p>'
    '<h3>操作方式</h3><p><span class="key">W A S D</span>／方向键让主体移动；'
    '点击己方非核心数字后按方向键可单块调整；把己方非核心数字拖到另一个上可互换位置；'
    '<span class="key">Esc</span> 返回主体；<span class="key">Z</span> 撤销；'
    '按住 <span class="key">Shift</span> 再按方向键可预览移动结果'
    '（只预览移动、对碰与归属，不含随后的射击、敌方行动与补给）。</p>'
    '<h3>小地图</h3><p>点击小地图上的己方核心标记即可切换视野，切换不消耗时间。</p>'
    '<h3>科技点</h3><p>三个来源：<strong>击破敌方核心或碉堡</strong>、'
    '<strong>探索</strong>（首次进入新的 10×10 区块，每块 1 点）、'
    '以及<strong>用合成分兑换</strong>（每 100 分换 1 点，<strong>会消耗积分</strong>）。'
    '科技树目前三条线：<strong>自动合成阈值</strong>（基础 4，每级翻倍）、'
    '<strong>吸收吞吐</strong>、<strong>收集半径</strong>。</p>'
    '</section>'
)
g = sub(g, '<footer>CORE ARCHIPELAGO · 独立说明页 · 无网络依赖</footer>',
        NEW_SEC + '<footer>CORE ARCHIPELAGO · 独立说明页 · 无网络依赖</footer>',
        1, '游戏介绍新增「画面读法、小地图与科技点」章节')

g_path.write_text(g, encoding='utf-8', newline='')
print('游戏介绍已更新：%d 字符' % len(g))

print()
print('本次应用 %d 项' % len(applied))
