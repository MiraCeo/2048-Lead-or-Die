"""文档同步：一次性变更脚本已迁入 tools/history/。"""
import re
import sys
from pathlib import Path

ROOT = Path(r'D:\2048')
log = []


def sub_re(path, pattern, new, label, flags=0):
    p = Path(path)
    t = p.read_text(encoding='utf-8')
    n = len(re.findall(pattern, t, flags))
    if n != 1:
        sys.exit('%s：预期 1 次，实际 %d 次' % (label, n))
    p.write_text(re.sub(pattern, new, t, count=1, flags=flags), encoding='utf-8', newline='')
    log.append(label)


# ─────────────────────────────── 项目文档 §14.4
OLD = r"""### 14\.4 `tools/` 目录怎么读（共 80\+ 文件，分三类）

\| 类别 \| 文件 \| 说明 \|
\| --- \| --- \| --- \|
\| \*\*工具链（长期有效）\*\* \| `extract_sources\.py` · `derive_patches\.py` · `build\.py` · `check_patches\.py` · `repair_patches\.py` · `reanchor\.py` · `build_engine\.py` \| 构建与补丁维护，必须留着 \|
\| \*\*测试\*\* \| `test_\*\.js`（8 个） \| 见 14\.3 \|
\| \*\*诊断/报告\*\* \| `report_\*\.js`（3 个） · `diff_engine\.py` · `diff_tutorial\.py` · `dump_lines\.py` · `probe_step2\.py` · `report_tutorial\.py` \| 随时可重跑，用于复核与排查 \|
\| \*\*实验台\*\* \| `harness\.js` · `trace\.js` · `first_divergence\.py` · `trace_series\.py` · `build_variant\.py` \| §6/§7 那次诊断用的 A/B 与逐回合追踪；做平衡性实验时再用 \|
\| \*\*一次性变更脚本（已执行完）\*\* \| `step\*\.py` · `step\*b_\*\.py` · `doc_sync\*\.py` 等约 60 个 \| \*\*不是流水线的一部分\*\*，请勿在构建里引用。它们的价值是\*\*变更历史\*\*：每个脚本记录了那次改动的精确替换文本、锚点与理由，是"为什么这么改"的一手证据 \|

> \*\*建议\*\*：接手后把最后一类移入 `tools/history/`，让工具链一眼可辨。
> 这件事\*\*我没有执行\*\*（属于文件整理，等你决定）。"""

NEW = """### 14.4 `tools/` 目录怎么读

**`tools/` 只放"还能再跑"的东西（28 个文件）：**

| 类别 | 文件 | 说明 |
| --- | --- | --- |
| **工具链（长期有效）** | `extract_sources.py` · `derive_patches.py` · `build.py` · `check_patches.py` · `repair_patches.py` · `reanchor.py` · `build_engine.py` | 构建与补丁维护，必须留着 |
| **测试** | `test_*.js`（8 个文件 / 9 组用例） | 见 §14.3 |
| **诊断/报告** | `report_*.js`（3 个） · `diff_engine.py` · `diff_tutorial.py` · `dump_lines.py` · `probe_step2.py` · `report_tutorial.py` | 随时可重跑，用于复核与排查 |
| **实验台** | `harness.js` · `trace.js` · `first_divergence.py` · `trace_series.py` · `build_variant.py` | §6/§7 那次诊断用的 A/B 与逐回合追踪；做平衡性实验时再用 |

**`tools/history/` 放"已经执行完、不会再跑"的一次性变更脚本（58 个文件）：**

- `step1…step16` —— 功能与界面改动（含配套的测试同步脚本 `*b_tests` / `*c`）
- `doc_sync*` / `doc_chinese` / `doc_finish` —— 项目文档的历次更新
- `handover_doc*` —— 交接文档的状态对照与执行前必读

它们的价值是**变更历史**：每个脚本记录了那一次改动的**精确替换文本、锚点与理由**，
是"为什么这么改"的一手证据。**不是流水线的一部分，请勿在构建或测试里引用。**
改动溯源时按序号顺序读即可；同一说明也在 `tools/history/README.md` 里。

> **迁移后已复核**：`check_patches` 0 / 13 · `build.py` 比对基线 `UNCHANGED` · 9 组测试全过。"""

sub_re(ROOT / '项目文档.md', OLD, NEW, '§14.4 更新为迁移后的目录说明')

# ─────────────────────────────── 交接文档 overlay 补一行
p = ROOT / '交接文档.md'
t = p.read_text(encoding='utf-8')
ANCHOR = "> | （细节）「导出 40 个函数」 | 实际是 **37 个**（现役引擎已扩展到 64 个） |\n"
ADD = ANCHOR + "> | §8 提到的对照脚本 | 一次性变更脚本已归入 `tools/history/`，现役工具链与测试在 `tools/` —— 见 项目文档 §14.4 |\n"
if ADD not in t and ANCHOR in t:
    p.write_text(t.replace(ANCHOR, ADD, 1), encoding='utf-8', newline='')
    log.append('交接文档对照表补上工具目录一行')
elif ADD in t:
    log.append('交接文档已有该行，跳过')
else:
    sys.exit('交接文档里找不到对照表锚点')

print('文档已同步：')
for a in log:
    print('  - %s' % a)
