"""项目文档：记录界面优化第一轮与新增的外壳测试。"""
import re
import sys
from pathlib import Path

DOC = Path(r'D:\2048') / '项目文档.md'
t = DOC.read_text(encoding='utf-8')
log = []


def sub_re(pattern, new, label, flags=0):
    global t
    n = len(re.findall(pattern, t, flags))
    if n != 1:
        sys.exit('%s：预期 1 次，实际 %d 次' % (label, n))
    t = re.sub(pattern, new, t, count=1, flags=flags)
    log.append(label)


# 工具表加外壳测试
sub_re(r'\| \[tools/test_step1\.js\]\(tools/test_step1\.js\)',
       '| [tools/test_shell.js](tools/test_shell.js) | **外壳结构对账**：把引擎引用的元素 id 与交付文件里真实存在的 id 对起来 |\n'
       '| [tools/test_step1.js](tools/test_step1.js)',
       '工具表加入 test_shell.js', re.M)

# 命令清单加一行
sub_re(r'^node tools\\test_display\.js.*$',
       'node tools\\test_display.js          # 展示层：绘制路径 + 战报行为\n'
       'node tools\\test_shell.js            # 外壳结构：元素 id 对账 + 顺序 + 命名去重',
       '命令清单加入外壳测试', re.M)

# 进度表
sub_re(r'^\| — \| 界面优化（视觉侧：布局 · 命名 · 图例 · 响应式）\| 待办（交给有视觉的一方） \|$',
       '| — | 界面优化 第一轮（信息重复 · 命名 · 操作反馈上移）| ✅ 功能验收通过（见 §13.8）|\n'
       '| — | 界面优化 第二轮（科技树按需面板 · 舰队收缩 · 战报折叠）| 待办 |\n'
       '| — | 界面优化 第三轮（首屏尺寸 · 响应式 CSS 合并）| 待办（**需要人眼**）|',
       '进度表拆成三轮', re.M)

SEC = """

### 13.8 界面优化第一轮：已完成 ✅

**① 信息重复与命名**（任务书 §五 里我核实成立的条目）

| 任务书条目 | 处理 |
| --- | --- |
| §五.1 世界／视野尺寸重复 | 删掉顶部徽标（棋盘左上、右上已各表一次，视野范围另有 `#targetCount`） |
| §五.2 当前核心 vs 共享 core | 改成「**当前控制核心**」「**全队共享 core**」 |
| §五.3 目标进度 | 改成「**最高合成值**」（它读的是历史最高值） |
| §五.4 行动点固定规则重复 | 副标题精简，规则移入悬浮提示（`title`） |
| §五.6 固定补给／增援重复 | 战场面板底部那两行删掉（游戏介绍里已完整讲） |
| §五.8 中英文标题过小 | 面板标题 `10px/字距2px` → **`11px/字距1px` 并提亮** |
| — | 附：副标题与页脚装饰英文改为中文 |

**② 操作反馈上移**（任务书 §二.3 / P0 的一部分）
预览提示与状态条从棋盘**下方**移到**上方**，让"刚发生了什么"与棋盘同屏可见。

**③ 核心保持原色**（你的要求）
核心从血量配色中排除（`!t.core`），受损核心不再变绿/黄/红，保留金色身份。

**④ 新增 [tools/test_shell.js](tools/test_shell.js) —— 补上一个之前一直缺的验证**

重构 markup 最容易**悄悄弄坏**的是元素 id。而无头环境的 `document` 是 Proxy stub，
`$('xxx')` 永远返回一个假元素——**id 掉了测试也不会报错，只有真人开浏览器才会发现界面空了**。

这个测试直接把「引擎引用的 id」与「交付文件里真实存在的 id」对起来：
**49 个 id 全部存在**，并检查关键 id 唯一、操作反馈确实排在棋盘之前。
以后不管是视觉侧还是我改 markup，跑它就能立刻知道有没有把界面改空。

### 13.9 界面优化后续两轮

**第二轮（结构性收缩，我做）**：科技树改为按需面板（主界面只留余额 + 入口）、
舰队列表按数量收缩、战报默认少量 + 可展开、扫描面板改紧凑。

**第三轮（必须人眼，视觉侧做）**：首屏尺寸迭代、响应式 CSS 合并、颜色编码表与图例。
理由见 §13.5——现有 CSS 为"首屏放得下"已叠了四轮覆盖规则，那是历史证据，
而我看不到画面。
"""

if '13.8 界面优化第一轮' not in t:
    t = t.rstrip('\n') + SEC
    log.append('追加 §13.8 / §13.9')

DOC.write_text(t, encoding='utf-8', newline='')
print('项目文档已更新：')
for a in log:
    print('  - %s' % a)
