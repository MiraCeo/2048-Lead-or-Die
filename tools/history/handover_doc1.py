"""交接文档更新（一）：项目文档.md

三件事：
  1. 进度表同步到当前真实状态
  2. §13.9「后续两轮」已过时（第二轮已完成）→ 改写
  3. 追加 §14 交接要点 —— 给接手者的一份自足说明
     （黄金规则 / 命令 / tools 目录怎么读 / 参数速查 / 待办 / 已知坑）
"""
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


# ─────────────────────────────────────────── 1. 进度表
OLD_TABLE = """| — | 界面优化 第三轮（科技树按需面板 ✅ · 舰队收缩 · 战报折叠）| 部分完成（见 §13.12）|
| — | 界面优化 第四轮（首屏是否真能一屏放下 · 颜色编码表 · 响应式合并）| 待办（**需要人眼**） |
| — | 动效（吸收 / 被攻击 / 摧毁 / 升级 / 恢复） | ✅ 功能验收通过（见 §9.1）|
| — | 难度调整（初始科技 / 科技树成本 / 敌方 曲线 / 敌方 能力） | 待办（见 §10；科技树成本已部分上调） |
| — | 科技树第二条线换轴 / 探索改真决策 | 待办（见 §11） |"""

NEW_TABLE = """| — | 界面优化 第三轮·甲（科技树按需面板）| ✅ 功能验收通过（见 §13.12）|
| — | 界面优化 第三轮·乙（舰队列表收缩 · 战报折叠）| 待办（见 §14.6） |
| — | 画布（删顶部标签 · 去下方留白 · 860×860）| ✅ 功能验收通过（见 §13.11）|
| — | 面板标题折行修复（字距归零）| ✅ 看图确认后修复（见 §14.7）|
| — | 动效（吸收 / 被攻击 / 摧毁 / 升级 / 恢复） | ✅ 功能验收通过（见 §9.1）|
| — | 视觉桥打通（可读用户截图） | ✅ 已可用（见 §14.8）|
| — | 界面优化 第四轮（首屏实测 · 颜色编码表 · 响应式合并）| 待办 |
| — | 难度调整（初始科技 / 科技树成本 / 敌方曲线 / 敌方能力） | 待办（见 §10；科技树成本已部分上调） |
| — | 探索改真决策 | 待办（见 §11.2；11.1 已解决） |"""

sub_re(re.escape(OLD_TABLE), NEW_TABLE, '进度表同步到当前状态')

# ─────────────────────────────────────────── 2. §13.9 改写
OLD_139 = """### 13.9 界面优化后续两轮

**第二轮（结构性收缩，我做）**：科技树改为按需面板（主界面只留余额 + 入口）、
舰队列表按数量收缩、战报默认少量 + 可展开、扫描面板改紧凑。

**第三轮（必须人眼）**：首屏尺寸迭代、响应式 CSS 合并、颜色编码表与图例。
理由见 §13.5 —— 现有 CSS 为"首屏放得下"已叠了四轮覆盖规则，那是历史证据，而我看不到画面。"""

NEW_139 = """### 13.9 界面优化后续安排（已按实际进度改写）

**第三轮·甲（已完成 ✅）**：科技树改为按需面板 —— 见 §13.12。
**第三轮·乙（待办）**：舰队列表按数量收缩、战报默认少量 + 可展开。
**第四轮（待办）**：首屏实测、颜色编码表与图例、响应式 CSS 合并（含清理遗留的 `886` 死规则）。

**⚠️ 关于"是否需要人眼"**：原先我把第四轮整体标为"必须人眼"，因为当时看不到画面。
**现在视觉桥已打通（§14.8），我可以读用户发的截图**，所以第四轮不必整包交给别人 ——
但**无法自测截图**（沙箱内 headless Chrome 起不来，见 §14.7），仍需"用户截图 → 我读"这个回路。"""

sub_re(re.escape(OLD_139), NEW_139, '§13.9 按实际进度改写')

# ─────────────────────────────────────────── 3. 追加 §14
SEC14 = """

---

## 14. 交接要点（给接手的人或 AI）

### 14.1 一句话现状

《核心群岛》（2048 远征）已完成：构建管线、六项计划改动（步骤 1–4）、一轮规则修订、
展示层、界面优化前两轮 + 第三轮甲、动效。
**9 组无头测试全过、13 条教程补丁 0 失配。** 剩余的是界面收尾、难度调整、探索机制与教程重做。

| 项 | 值 |
| --- | --- |
| 交付物 | `2048小游戏-教程七关.html` · 225703 字节 · sha256 `AB65A7059AF5E59D15D98EA1185AD724505E89F283B79FF1101C33C209901FCA` |
| 真源 | `src/` 六个文件：`main.shell.html` / `main.script.js` / `guide.html` / `tutorial.shell.html` / `tutorial.lessons.js` / `tutorial.patches.py` |
| 补丁 | 13 条（教程内嵌副本由主脚本 + 补丁生成） |
| 测试 | 8 个文件、9 组用例 |

### 14.2 三条黄金规则（违反会直接坏掉）

**① 绝不手改交付文件。** 它是 `src/` 的构建产物。直接改它会：下次构建整个覆盖它、
`src/` 与交付物脱节、**并且教程的 13 条补丁锚点失配，导致构建直接失败**。
正确做法：改 `src/` → `python tools/build.py`。

**② 改动落在"危险区"时，必须走补丁重锚流程。** 危险区＝被教程补丁覆盖的那些行
（棋盘绘制行、`ui()`、`draw()`、`actUnsafe`、`worldStep`、`performSwap`、`inputBlocked`、
`keydown`、boot 块等，见 §13.2）。流程：

```
改完 → python tools/check_patches.py   # 看是否失配
     → python tools/reanchor.py        # 失配就重锚（按"公共前缀最长的行"匹配，支持跨行补丁）
     → python tools/check_patches.py   # 确认 0 / 13
```

**③ 改完 `src/` 一定要重建引擎，否则测试会读到旧引擎、误报失败。**（我踩过一次。）

```
python tools/build_engine.py --out build/engine.js
```

### 14.3 常用命令

```powershell
cd 'D:\\2048'

# 构建
python tools\\build.py              # 组装交付文件并与基线比对
python tools\\build.py --accept     # 把当前构建记为新基线

# 补丁健康
python tools\\check_patches.py      # 13 条锚点是否仍唯一命中
python tools\\reanchor.py           # 引擎改动后重锚受影响补丁
python tools\\repair_patches.py     # 定点修复（带命中数断言）

# 无头引擎与测试
python tools\\build_engine.py --out build\\engine.js
node tools\\test_step1.js engine     # 引擎冒烟 + 「ng 字段已移除」回归
node tools\\test_step1.js tutorial   # 教程加载 / 7 关可实例化
node tools\\test_step2.js            # 自动收集（吸收 · 记账 · 上限 · 半径）
node tools\\test_step2_tutorial.js   # 教程结构 + 吸收作用域隔离
node tools\\test_step4.js            # 科技点（三条来源 · 成本门控 · 两条线生效）
node tools\\test_rules.js            # 阈值规则 · 受伤可升级 · 回血 · 敌方天花板
node tools\\test_display.js          # 棋盘编码 + 战报行为
node tools\\test_shell.js            # 外壳结构：元素 id 对账 + 顺序 + 命名去重
node tools\\test_fx.js               # 动效事件通道 + 六类特效触发条件

# 复核类（无断言，只输出数字）
node tools\\report_tech_cost.js          # 科技树各级成本与效果
node tools\\report_regen_math.js         # 回血与伤害的参考数值表
node tools\\report_radius_throughput.js  # 半径与站点吞吐是否互相打架
```

### 14.4 `tools/` 目录怎么读（共 80+ 文件，分三类）

| 类别 | 文件 | 说明 |
| --- | --- | --- |
| **工具链（长期有效）** | `extract_sources.py` · `derive_patches.py` · `build.py` · `check_patches.py` · `repair_patches.py` · `reanchor.py` · `build_engine.py` | 构建与补丁维护，必须留着 |
| **测试** | `test_*.js`（8 个） | 见 14.3 |
| **诊断/报告** | `report_*.js`（3 个） · `diff_engine.py` · `diff_tutorial.py` · `dump_lines.py` · `probe_step2.py` · `report_tutorial.py` | 随时可重跑，用于复核与排查 |
| **实验台** | `harness.js` · `trace.js` · `first_divergence.py` · `trace_series.py` · `build_variant.py` | §6/§7 那次诊断用的 A/B 与逐回合追踪；做平衡性实验时再用 |
| **一次性变更脚本（已执行完）** | `step*.py` · `step*b_*.py` · `doc_sync*.py` 等约 60 个 | **不是流水线的一部分**，请勿在构建里引用。它们的价值是**变更历史**：每个脚本记录了那次改动的精确替换文本、锚点与理由，是"为什么这么改"的一手证据 |

> **建议**：接手后把最后一类移入 `tools/history/`，让工具链一眼可辨。
> 这件事**我没有执行**（属于文件整理，等你决定）。

### 14.5 当前可调参数速查（按引擎实算）

| 常量 | 现值 | 作用 |
| --- | --- | --- |
| `ABSORB_CAP` | **4** | 自动合成阈值的基础值；每升一级翻倍（4 / 8 / 16 / 32） |
| `ABSORB_TP` | 2 | 每块每回合吸收次数（吞吐线每级 +1） |
| `ABSORB_RADIUS` | 1 | 站点收集半径基础值（半径线每级 +1） |
| `SITE_TP` | 4 | 站点每回合吞吐上限（**随半径线 +4/级**） |
| `REGEN_RATE` | **0.05** | 回血＝血量上限的 5%/回合 |
| `REGEN_DELAY` | **10** | 脱离战斗满 10 回合才回血 |
| `AI_REGEN_RATE` | **0** | 敌方回血（存在但关闭） |
| `AI_ABSORB_CEILING` | **4** | 敌方采集机天花板（与玩家同形态、值独立可调） |
| `SCORE_PER_TECH` | 100 | 每 100 合成分兑换 1 科技点（**会扣分**） |
| `TECH_TP_MAX` / `TECH_RADIUS_MAX` / `TECH_THRESHOLD_MAX` | 2 / 2 / **3** | 三条线的等级上限 |
| `techCost(line,level)` | `8 + 8×level` | 全线合计 **96 点** |
| `HP_HURT` / `HP_CRIT` | 0.66 / 0.33 | 血量配色的两档阈值 |
| `HP_COL_OK/HURT/CRIT` | `#8fd98a` / `#e8cf72` / `#e07a6a` | 绿 / 黄 / 红 |
| `DUR` | `{shot:450,absorb:420,pulse:480,hit:600,kill:520,regen:640}` | 六类动效时长（ms） |
| `--board-chrome` | 230px | 棋盘可用高度的固定开销（CSS 变量，**唯一需要按屏幕调的尺寸**） |

### 14.6 待办（含"卡在哪"）

| 优先级 | 事项 | 卡在哪 |
| --- | --- | --- |
| 1 | 舰队列表收缩（只有一支时收成一行） | 无，可直接做 |
| 1 | 战报默认少量 + 可展开 | 无，可直接做 |
| 2 | 首屏实测与 `--board-chrome` 调值 | **需要看画面** |
| 2 | 颜色编码表与图例（金色/浅绿的双重含义） | **需要看画面** |
| 2 | 响应式 CSS 合并（含清掉遗留的 `886` 死规则） | 需要看画面 |
| 3 | 难度调整四项（§10） | 需用户定方向与量级；建议 1→2→4→3 小步调 |
| 3 | 探索改成真决策（§11.2） | 等"是否加战争迷雾"定案 |
| 4 | 教程重做（§12.7） | 等机制冻结（现处于停测状态） |
| — | 动效的幅度与时序微调 | 需要看画面 |
| — | 血量配色是否排除支援碉堡（核心已排除） | 需用户定 |

### 14.7 已知的坑（都踩过）

1. **沙箱内 headless Chrome 起不来**：`mojo platform_channel` 需要命名管道，沙箱不允许开，
   报 `Check failed: 拒绝访问 (0x5)`。**加参数绕不过去，不要重试**。所以无法自测截图。
2. **`886` 有四处**（画布高度参与坐标映射）：shell 的 canvas 高度属性、`draw()` 的
   `clearRect/fillRect`、`indexFromEvent` 的换算、`pointermove` 的拖拽换算。只改一处会让
   点击位置与方块错位。（画布已改成 860，四处已同步；旧 CSS 里还残留一处不生效的 `calc(...860/886...)`。）
3. **无头 DOM 是 Proxy stub**：`$('xxx')` 永远返回假元素，所以**元素 id 掉了测试也不报错**，
   只有真人开浏览器才发现界面空了 —— 这就是 `tools/test_shell.js` 存在的原因。
4. **`mkState` 类测试辅助函数容易撞 id**：若测试板再放一个 `id:1` 的核心，会与默认核心重号，
   受控核心跑到别处。写新测试时留意。
5. **测试板要围绕默认核心摆**：同上。
6. **`clearPreview()` 曾把整段 WASD 说明写回 `#previewHint`**：只删 markup 删不干净，
   已改为清空。同类"写在别处的文案"要一并查。
7. **动效的 `fx` 必须显式传参，不能用全局缓冲**：`ai()` 与 `showPreview()` 会用副本模拟
   `moveMain`（敌方每回合 6 核 × 4 方向），全局缓冲会被灌满幽灵特效。新特效一律走**可选 fx 参数**。
8. **渲染循环的准入判断**：`shot` 与 `absorb` 是"两点型"（`from`/`to`），其余是"单点型"（`at`）
   —— 曾因为把 absorb 放在 `at` 准入之后，导致吸收轨迹永远画不出来。新特效注意分类。
9. **Hindsight 记忆工具返回 401**，本次全程未使用，结论全部来自实测与源码。

### 14.8 环境与工具（非代码）

- **视觉桥（可读截图）已打通**：`C:\\Users\\12782\\.modlens\\config.json` = `{"reuse":{"codex":true}}`。
  读图用 `modlens_read_image`。注意它曾有两次失败原因（`codex` 的 `models_cache.json` 里
  非法的 `effort: max/ultra`；`codex` 的 `config.toml` 里 `service_tier = "default"` 已不再是合法值，
  当前只接受 `fast`/`flex`）—— **若哪天又读不了图，先查这两处**。
- **工作区**：`D:\\2048`（沙箱只允许写这里）。原始项目目录 `D:\\Hypergryph\\模拟初筛` 只读未动，
  其 `.analyze` 已迁入 `D:\\2048\\.analyze`（保留作为参照，与工作区版本可能不同步）。
- **Python / Node**：Python 3.11、Node v24。构建与测试都不依赖任何第三方包。
- **`AGENT.md`** 是用户给 AI 的工作规则（讨论≠授权、不得擅自扩范围等），改动代码前应遵守。
"""

if '## 14. 交接要点' not in t:
    t = t.rstrip('\n') + SEC14
    log.append('追加 §14 交接要点')

DOC.write_text(t, encoding='utf-8', newline='')
print('项目文档已更新：')
for a in log:
    print('  - %s' % a)
