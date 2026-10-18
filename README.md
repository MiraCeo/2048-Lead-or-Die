# 尔领死吧

> **Lead or Die** —— 2048 的中文谐音。
> 一款把 2048 的合成机制放进 100×100 战场的单文件网页游戏。

🔗 仓库：<https://github.com/MiraCeo/2048-Lead-or-Die>

---

## 快速开始

**下载 [`尔领死吧-v0.1.0.html`](尔领死吧-v0.1.0.html)，双击打开。**

单个自包含 HTML，无网络依赖、无安装、无构建步骤 —— 所有样式、脚本与说明页都内嵌在这一个文件里。
进度自动保存在浏览器本地。

### 操作

| 操作 | 输入 |
| --- | --- |
| 主体移动（推进世界） | `W` `A` `S` `D` 或 方向键 |
| 单块调整（冻结世界） | 点击己方非核心数字，再用方向键；`Esc` 返回主体 |
| 方块置换 | 把己方非核心数字拖到另一个己方非核心数字上 |
| 移动预览 | 按住 `Shift` 再按方向键（不消耗回合） |
| 撤销 | `Z`（最多 50 步） |
| 切换受控核心 | 点击己方核心、左侧列表，或小地图上的核心标记 |

完整的机制说明、数值与画面读法都在**游戏内的「游戏介绍」**里 —— 它随 `src/` 一起构建，
是机制的权威说明。本 README 不复制那些内容，以免与实现脱节。

---

## 这是什么游戏

在 100×100 的数字战场上经营一支由方块组成的远征军：

- **合成** —— 同值方块相撞翻倍，一路推向 2048
- **收编** —— 推动或碰撞把中立数字并入己方，扩大编队
- **分化** —— 离体小队达到 4 块会自动产生新的分核心，可分别操控
- **吸收** —— 低于阈值的方块每回合自动吞噬相邻中立；核心与收集站还提供**收集半径**
- **对抗** —— 敌方编队每两回合行动一次，还有敌机、碉堡与采集机；血量对碰与射程 8 格的攻击
- **成长** —— 用科技点升级自动合成阈值、吸收吞吐与收集半径

时间由**你的动作**推进：主移动推进世界，而单块调整与置换冻结世界。
因此不存在「打开界面是否暂停」的问题。

---

## 工程说明

### 为什么只有一个 HTML

交付物是**单个自包含 HTML**，故意如此：离线可玩、双击即开、便于分发。
代价是它必须由 `src/` **构建**出来 —— 所以：

> ⚠️ **不要直接编辑 `尔领死吧-v0.1.0.html`。** 它是构建产物。
> 下次构建会整个覆盖它，`src/` 会与交付物脱节，而且教程的 13 条补丁锚点会失配、构建直接失败。

### 仓库结构

```
尔领死吧-v0.1.0.html      ← 交付物（构建产物，勿手改）
src/                      ← 唯一真源
  main.shell.html           HTML/CSS 外壳
  engine/                   引擎，11 个域模块（可读代码）
  main.script.js            由 engine/ 拼接而成（构建产物）
  guide.html                游戏内介绍页
  tutorial.shell.html       教程外壳
  tutorial.lessons.js       教程七关脚手架
  tutorial.patches.py       13 条补丁规则（引擎 → 教程副本）
tools/                    ← 构建、测试与诊断脚本
build/                    ← 构建中间产物、基线、诊断记录
项目文档.md                ← 唯一的工作记录与决策中心（含全部设计决策与踩过的坑）
```

**教程自带一份引擎副本**，它由 `src/main.script.js` + 13 条补丁**生成**，不手工维护。
每条补丁锚点断言唯一命中，失配即构建失败 —— 这样引擎的改动不可能悄悄与教程脱节。

### 构建

需要 **Python 3.11+** 与 **Node 18+**。构建与测试**不依赖任何第三方包**。

```powershell
git clone https://github.com/MiraCeo/2048-Lead-or-Die.git
cd 2048-Lead-or-Die              # git clone 生成的是仓库名，与交付文件名不同

python tools/build.py              # 组装交付物，并与基线比对
python tools/check_patches.py      # 13 条教程补丁锚点健康检查
```

### 开发循环

改引擎请改 `src/engine/*.js`（可读代码），然后：

```powershell
python tools/bundle_engine.py --write    # 拼回 src/main.script.js
python tools/build.py                    # 组装交付 HTML
python tools/check_patches.py            # 补丁锚点
python tools/build_engine.py --out build/engine.js
```

### 测试

```powershell
# 功能验收（10 组，均不依赖第三方包）
node tools/test_step1.js engine      # 引擎冒烟
node tools/test_step1.js tutorial    # 教程加载 / 七关可实例化
node tools/test_step2.js             # 自动收集机制
node tools/test_step2_tutorial.js    # 教程结构 + 吸收作用域隔离
node tools/test_step4.js             # 科技点系统
node tools/test_rules.js             # 阈值 / 受伤可升级 / 回血 / 敌方天花板
node tools/test_display.js           # 棋盘编码 + 战报行为
node tools/test_shell.js             # 外壳结构：元素 id 对账（防「改动把界面改空」）
node tools/test_fx.js                # 动效事件通道
node tools/test_loose_matcher.js     # 测试助手自测

# 行为等价（重构安全网）
node tools/difftest.js --engine build/engine.js --seeds 6 --turns 400 `
     --out build/difftest/check --assert-same build/difftest/base
```

`difftest` 用固定种子跑完整对局并逐回合比对**全部方块字段与计数器**，
用来证明「重构没有改变行为」。它自己也做过反向验证：注入已知变异能被检出。

### 诊断与复核（无断言，只输出数字）

```powershell
node tools/report_tech_cost.js          # 科技树各级成本与效果
node tools/report_regen_math.js         # 回血与伤害参考数值
node tools/report_radius_throughput.js  # 半径与站点吞吐是否互相打架
python tools/engine_structure.py        # 打印引擎的顶层结构
python tools/check_branding.py          # 解码内嵌的介绍页/教程，检查品牌名一致
```

> 这两份内嵌文档是 **base64** 存的，在交付物 HTML 里明文搜不到 ——
> 要检查它们的内容必须**解码后**再检索。

---

## 状态

**v0.1.0 · 原型**，仍在迭代。当前重点是**编队、收编与战术操作**；
敌方规模与成长等数值仍是可调参数，后续会做难度调整。

已知待办与「卡在哪」记录在 [项目文档.md](项目文档.md) 的 **§14.6**（唯一权威清单）。

## 授权

**未授权（All rights reserved）。** 本仓库目前未附 License，因此默认保留所有权利。
欢迎阅读与试玩；如需使用、修改或分发代码，请先联系作者。

## 说明

本项目在开发过程中大量使用 AI 辅助（含代码、文档与重构），
所有改动都经过构建校验与自动化测试。设计与决策记录见 [项目文档.md](项目文档.md)。
