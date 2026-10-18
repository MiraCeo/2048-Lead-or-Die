"""把一次性变更脚本迁入 tools/history/。

保留在 tools/ 的是「还能再跑」的东西：构建/补丁工具链、测试、诊断报告、实验台。
迁走的是「已经执行完、不会再用」的一次性脚本 —— 它们的价值是变更历史。

迁移前先检查：保留的文件里若引用了要迁走的文件名，就先报错不迁（否则会断链）。
"""
import re
import shutil
import sys
from pathlib import Path

TOOLS = Path(r'D:\2048\tools')
HIST = TOOLS / 'history'

KEEP = {
    # 工具链
    'extract_sources.py', 'derive_patches.py', 'build.py', 'check_patches.py',
    'repair_patches.py', 'reanchor.py', 'build_engine.py',
    # 测试（8 个文件 / 9 组用例）
    'test_step1.js', 'test_step2.js', 'test_step2_tutorial.js', 'test_step4.js',
    'test_rules.js', 'test_display.js', 'test_shell.js', 'test_fx.js',
    # 诊断与报告
    'report_tech_cost.js', 'report_regen_math.js', 'report_radius_throughput.js',
    'diff_engine.py', 'diff_tutorial.py', 'dump_lines.py', 'probe_step2.py',
    'report_tutorial.py',
    # 实验台（平衡性实验时再用）
    'harness.js', 'trace.js', 'first_divergence.py', 'trace_series.py',
    'build_variant.py',
}

files = [p for p in TOOLS.iterdir() if p.is_file()]
keep_now = [p for p in files if p.name in KEEP]
move = [p for p in files if p.name not in KEEP]

print('保留 %d 个，迁移 %d 个' % (len(keep_now), len(move)))

# ---- 检查引用 ----
moving_names = {p.name for p in move}
bad = []
for p in keep_now:
    text = p.read_text(encoding='utf-8', errors='replace')
    for name in moving_names:
        if name in text:
            bad.append((p.name, name))
if bad:
    print('\n发现引用，已中止（未移动任何文件）：')
    for a, b in bad:
        print('  %s 引用了 %s' % (a, b))
    sys.exit(1)
print('引用检查通过：保留的文件没有引用要迁走的脚本')

# ---- 迁移 ----
HIST.mkdir(exist_ok=True)
moved = 0
for p in sorted(move):
    dst = HIST / p.name
    if dst.exists():
        sys.exit('目标已存在，中止：%s' % dst)
    shutil.move(str(p), str(dst))
    moved += 1
print('已迁入 %s：%d 个文件' % (HIST, moved))

# ---- 落地一份说明 ----
note = HIST / 'README.md'
note.write_text(
    '# tools/history —— 一次性变更脚本（已执行完）\n\n'
    '这些脚本是**变更历史**，不是流水线的一部分。请不要在构建或测试里引用它们。\n\n'
    '它们的价值在于：每个脚本记录了那一次改动的**精确替换文本、锚点与理由**，\n'
    '是“为什么这么改”的一手证据。改动溯源时按文件名里的序号（step1…step16）顺序读即可。\n\n'
    '| 前缀 | 内容 |\n'
    '| --- | --- |\n'
    '| `step1…step16` | 功能与界面改动（含配套的测试同步脚本 `*b_tests` / `*c`） |\n'
    '| `doc_sync*` / `doc_chinese` / `doc_finish` | 项目文档的历次更新 |\n'
    '| `handover_doc*` | 交接文档的状态对照与执行前必读 |\n\n'
    '当前工具链、测试与诊断脚本在上一级 `tools/` 目录。完整说明见 项目文档.md §14.3 / §14.4。\n',
    encoding='utf-8', newline='')
print('已写入说明：%s' % note)
