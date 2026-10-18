"""检查首屏布局改动的落实情况（需看画面的那一组，能机器验的部分）。

背景：左侧栏曾有一个 `SCAN / 悬停扫描` 面板，CSS 给它 `min-height:70px`，
但内容常态只有一行（"39行 45列 · 空地"）。粗算左侧栏 ≈773px，超过常见视口，
于是页面出现纵向滚动条、最下面的提示被切掉。

改法：把悬停详情挪进**顶栏单行**（超长省略 + title 看全文），删掉整个面板，
并把 `--board-chrome` 从依赖 fallback 的 230px 显式定义为 200px（按实际开销算）。

这个脚本校验那些**能机器验证**的部分；真正的"是否同屏"仍需人眼看截图。
"""
import io
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _root import PATHS

html = io.open(PATHS.DELIVERABLE, encoding='utf-8').read()
eng = io.open(PATHS.SRC / 'main.script.js', encoding='utf-8').read()
# 归一化：去掉**所有空白**（含换行）。只去空格的话，prettier 把语句折成两行就匹配不到
# —— 这个检查器第一版就这么误报了自己。
eng_flat = re.sub(r'\s+', '', eng)
# CSS 也要归一化（整段 css 抽出来，去掉空白再比对规则文本）
css_flat = re.sub(r'\s+', '', html[html.find('<style>'):html.find('</style>')])
# 只保留**规则体**（去掉注释），否则注释里提到旧变量名会误判
css_rules = re.sub(r'/\*.*?\*/', '', html[html.find('<style>'):html.find('</style>')], flags=re.S)
rules_flat = re.sub(r'\s+', '', css_rules)

fails = []


def check(ok, label, detail=''):
    if not ok:
        fails.append(label)
    print('  %s  %s%s' % ('通过' if ok else '失败', label, ('  -- ' + detail) if detail else ''))


print('=== SCAN 面板已并入顶栏（不再独占一个固定高度的卡片） ===')
check('SCAN / 悬停扫描' not in html, 'SCAN 面板标题已移除')
check('id="inspect"' in html, '悬停详情元素仍在（id 未变，引擎仍能写入）')
check('class="scan-line"' in html, '它现在是顶栏里的单行元素')
check('.scan-line{' in html, 'scan-line 样式在场（省略号 + title 兜底）')
check('class="inspect"' not in html, '旧的固定高度面板容器已不再使用')

print()
print('=== 单行截断必须有 title 兜底（否则长详情看不全） ===')
check('el.title=text' in eng_flat, 'inspect() 会同时写 textContent 与 title')

print()
print('=== 棋盘尺寸：弹性布局接管，不再有魔法数字 ===')
# 只查**规则体**：变量名在注释里被提到是正常的（那是演进记录）
check('--board-chrome:' not in rules_flat and 'var(--board-chrome' not in rules_flat,
      '--board-chrome 的**定义与引用**都已移除（注释中保留演进记录没问题）')
check('.boardcanvas{width:auto;height:auto;max-width:100%;max-height:100%}' in rules_flat,
      '棋盘用 max-height:100% 吃 .board 的剩余高度')

print()
print('=== 战报：折叠状态与"有没有被折叠"一致 ===')
check('<details class="log-wrap">' in html, '折叠容器仍在')
check('wrap.tagName===' in eng_flat, '按元素类型判定（不假设一定是 DETAILS）')
# 关键：条数不多时必须自动展开，否则摘要说"已全部显示"却正文为空
check('all.length<=LOG_PREVIEW)wrap.open=true' in eng_flat,
      '条数 ≤ 预览数时自动展开')
check('wrap.open=false' not in eng_flat,
      '绝不自动关闭（否则每次 ui() 都会覆盖玩家的展开意图）')
check("'toggle'" in eng, '展开/收起会即时重渲染')

print()
print('=== 首屏自适应：整页锁定视口，而不是让内容撑高页面 ===')
for pat, label in [
    ('.shell{height:100dvh', '外壳锁定为视口高度'),
    ('box-sizing:border-box', '高度含内边距（否则必然溢出）'),
    ('.layout{flex:1', '.layout 吃掉剩余高度'),
    ('min-height:0', '允许 flex 子项收缩（不加就还是会顶出去）'),
    ('footer{flex:00auto}', '页脚常驻底部 → 最下面的提示永远同屏'),
    ('.layout>aside{min-height:0;overflow-y:auto', '左右栏内部滚动，不顶整页'),
    # 空预览位不占高度：v0.1.5 起预览位移到页脚，用**绝对定位浮层**实现
    # （`.status-overlay{position:absolute}` 完全不占布局高度，比原来靠 :empty 收回 28px 更彻底）。
    # 原来断言 `.map-keyhint:empty{min-height:0}` —— 那条类已随结构删除，断言同步改为新机制。
    ('footer.status-overlay{position:absolute', '预览/反馈是绝对定位浮层（零布局高度）'),
    ('footer#previewHint:not(:empty){opacity:1}', '空预览位不可见、有内容才显示'),
]:
    check(pat in rules_flat, label)

print()
print('=== 状态槽：悬停详情与操作反馈共用一格，不得叠字 ===')
check('class="status-slot"' in html, '两者被同一个状态槽包住')
check('.status-slot>.feedback{' in html, '反馈在槽内绝对定位（按内容收缩）')
check('background:#0f1b15' in html, '反馈背景**全不透明**（原 95% 会透出底下的悬停详情）')
check('.status-slot:has(>.feedback.show)>.scan-line{visibility:hidden}' in html.replace(' ', ''),
      '反馈显示时直接藏起悬停详情（不靠不透明度硬盖）')

# ---- 真浏览器实测：页面不得滚动、页脚必须在视口内 ----
# 这是本次最重要的能力变化：此前"沙箱内 headless Chrome 起不来"，布局只能靠用户截图；
# 放宽文件策略后它可以跑了。于是"首屏是否同屏"从**只能人眼**变成**可以机器断言**。
print()
print('=== 真实浏览器实测（headless Chrome）：不滚动 + 页脚可见 ===')
import subprocess
SIZES = ['1920x1080', '1600x900', '1366x768', '1280x720']
for sz in SIZES:
    r = subprocess.run([sys.executable, str(HERE / 'shot.py'), '--metrics', '--size', sz],
                       cwd=PATHS.ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    out = r.stdout
    def grab(pat):
        mm = re.search(pat, out)
        return int(mm.group(1)) if mm else -1
    vh = grab(r'viewport:\s*x=\d+\s*y=\d+\s*w=\d+\s*h=(\d+)')
    sh = grab(r'doc\.scrollHeight.*?h=(\d+)')
    fy = grab(r'footer:\s*x=\d+\s*y=(\d+)\s*w=\d+\s*h=(\d+)') if False else None
    mm = re.search(r'footer:\s*x=\d+\s*y=(\d+)\s*w=\d+\s*h=(\d+)', out)
    fbot = (int(mm.group(1)) + int(mm.group(2))) if mm else -1
    bw = grab(r'canvas#canvas:\s*x=\d+\s*y=\d+\s*w=(\d+)')
    ok = (vh > 0 and sh == vh and 0 < fbot <= vh)
    check(ok, '%-10s 视口高 %4d · 文档高 %4d · 页脚底 %4d · 棋盘 %3dpx'
              % (sz, vh, sh, fbot, bw))
    # 棋盘**框**应当贴着画布；被拉成整列宽时两侧会有大片空白
    # （实测曾出现 1048px 框 / 535px 画布，各空 256px，看起来像布局坏了）
    bd = grab(r'\.board:\s*x=\d+\s*y=\d+\s*w=(\d+)')
    check(bd > 0 and bw > 0 and (bd - bw) <= 24,
          '%-10s 棋盘框 %3dpx 贴合画布 %3dpx（差值 %d，应为内边距+边框 18）'
          % (sz, bd, bw, bd - bw))
    # 中间列必须**跟着棋盘走**：列远宽于棋盘时，收缩后的棋盘框会变成
    # "小方块浮在大片空白里"（v0.1.3 的观感问题）。
    pa = grab(r'\.play-area:\s*x=\d+\s*y=\d+\s*w=(\d+)')
    check(pa > 0 and bd > 0 and (pa - bd) <= 60,
          '%-10s 中间列 %3dpx 贴合棋盘框 %3dpx（差值 %d，应 ≤60）'
          % (sz, pa, bd, pa - bd))
    # 顶栏已取消（v0.1.5），状态改放页脚 —— 页脚状态区应横跨大部分宽度
    ss = grab(r'\.status-slot:\s*x=\d+\s*y=\d+\s*w=(\d+)')
    sh = grab(r'\.shell:\s*x=\d+\s*y=\d+\s*w=(\d+)')
    check(ss > 0 and sh > 0 and ss >= sh * 0.6,
          '%-10s 页脚状态区 %4dpx 横跨（外壳 %4dpx 的 %.0f%%）'
          % (sz, ss, sh, 100.0 * ss / sh if sh else 0))
    # ★ 两栏**不得内部溢出**。v0.1.5 之前左栏溢出 91px、右栏 166px，
    #   "全部同屏"是假的（内容藏在栏内滚动条后面）。
    #   但两栏内容高度是固定的，视口矮到一定程度必然溢出 ——
    #   所以只对"视口高 ≥ 700"的尺寸严格断言，更矮的只报告（见项目文档 §21.5）。
    lv = grab(r'\.layout\s*(?:&gt;|>)\s*aside:ov=(-?\d+)')
    rv = grab(r'\.layout\s*(?:&gt;|>)\s*\.right:ov=(-?\d+)')
    if vh >= 700:
        check(lv <= 0 and rv <= 0,
              '%-10s 侧栏无内部溢出（左 %+d / 右 %+d，应为 ≤0）' % (sz, lv, rv))
    else:
        print('  报告  %-10s 视口仅 %dpx：侧栏溢出 左 %+d / 右 %+d'
              '（内容高度固定，矮屏必然栏内滚动；页面本身仍不滚动）'
              % (sz, vh, lv, rv))

print()
print('=== 死 CSS：markup 已删除的元素不该还留着样式 ===')
# 只取 <style>…</style> 之间的内容：否则 `<style>` 标签本身（以 > 结尾+换行）
# 会被"悬空选择器"正则误匹配。
_ss = html.find('<style>') + len('<style>')
_se = html.find('</style>')
css_raw = html[_ss:_se]
# 再剥掉注释 —— 注释里提到旧类名是"演进记录"，不是残留
# （第一版没剥，把注释里的 `.map-keyhint ` 误报成"仍在使用"）。
css_only = re.sub(r'/\*.*?\*/', '', css_raw, flags=re.S)
markup_part = html[html.find('<body>'):]
for cls in ('brand', 'en', 'badge', 'header-actions', 'play-heading',
            'map-actions', 'map-keyhint', 'topbar'):
    styles = re.search(r'\.' + re.escape(cls) + r'[{, :]', css_only)
    used = ('class="' + cls) in markup_part
    check(styles is None or used,
          '%-16s %s' % (cls, '已移除' if styles is None else '仍在使用'))
check('<header' not in html, 'header 元素已删除')
# 选择器不得悬空：删除规则时若只匹配了复合选择器的后半截，会留下 `.shell>` 这种碎片，
# 而它仍能解析成合法 CSS（只是永远不匹配），静默失效。
dangling = [m.group(0) for m in re.finditer(r'[^{}\n]*[>,]\n', css_only)]
check(not dangling, '无悬空选择器片段（删除规则时未切断复合选择器）',
      str(dangling[:2]) if dangling else '')

# ---- 两处"写了没生效/遮住内容"的定点校验（v0.1.6）----
print()
print('=== 浮层不遮列号 + navbtns 真正贴底 ===')
r = subprocess.run([sys.executable, str(HERE / 'shot.py'), '--metrics', '--size', '1600x900'],
                   cwd=PATHS.ROOT, capture_output=True, text=True,
                   encoding='utf-8', errors='replace')
o = r.stdout


def g1(pat):
    m = re.search(pat, o)
    return int(m.group(1)) if m else -1


cv_y, cv_h = g1(r'canvas#canvas:\s*x=\d+\s*y=(\d+)\s*w=\d+\s*h=(\d+)'), g1(r'canvas#canvas:\s*x=\d+\s*y=\d+\s*w=\d+\s*h=(\d+)')
act_bottom = g1(r'\.board-actions:\s*x=\d+\s*y=\d+\s*w=\d+\s*h=(\d+)')
act_y = g1(r'\.board-actions:\s*x=\d+\s*y=(\d+)')
aside_bottom = g1(r'aside\.left:\s*x=\d+\s*y=\d+\s*w=\d+\s*h=(\d+)')
aside_y = g1(r'aside\.left:\s*x=\d+\s*y=(\d+)')
nav_y = g1(r'\.navbtns:\s*x=\d+\s*y=(\d+)')
nav_h = g1(r'\.navbtns:\s*x=\d+\s*y=\d+\s*w=\d+\s*h=(\d+)')

if cv_y > 0 and act_y > 0:
    covered = (act_y + act_bottom) - cv_y
    # 列号标签绘制在 43/860 处（canvas 内坐标），换算成像素
    label_px = round(cv_h * 34 / 860)
    check(covered <= label_px,
          '浮层覆盖画布顶部 %dpx，列号标签在 %dpx 处 → %s'
          % (covered, label_px, '列号可见' if covered <= label_px else '**列号被遮**'))

if aside_y > 0 and nav_y > 0:
    gap = (aside_y + aside_bottom) - (nav_y + nav_h)
    check(gap <= 16, 'navbtns 距左栏底部 %dpx（应 ≤16，否则 margin-top:auto 没生效）' % gap)

print()
print('%d 项失败' % len(fails))
sys.exit(1 if fails else 0)
