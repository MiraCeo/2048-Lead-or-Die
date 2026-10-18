"""阶段 3：交付文件改名 + 品牌改名（含存档 key 换新）。

用户决定：
    · 交付文件名 = 「尔领死吧」+ 版本号，从 0.1.0 起  ->  尔领死吧-v0.1.0.html
    · 存档 key 一并改，**接受清档**                     ->  lead-or-die-v1
    · 品牌显示名 = 尔领死吧（英文 Lead or Die）

改动分四处：
    A. 文件名     tools/_root.py 的 PATHS.DELIVERABLE + tools/_root.js 的 DELIVERABLE
                  + 5 个测试脚本改用共享常量
    B. 品牌名     src/main.shell.html / src/tutorial.shell.html / src/guide.html
    C. 存档 key   已在阶段 3 前半段手工改（引擎 + 2 条补丁锚点）
    D. 版本号     文件名内含；页脚显示版本

每条替换断言精确命中预期次数，命中数不符即报错退出。
（本脚本已经错了不止一次，所以坚持"先预检再写入"。）

用法：
    python tools/rename_project.py --apply
"""
import io
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)

APPLY = '--apply' in sys.argv

OLD_FILE = '2048小游戏-教程七关.html'
NEW_FILE = '尔领死吧-v0.1.0.html'
OLD_BRAND = '核心群岛'
NEW_BRAND = '尔领死吧'
VERSION = '0.1.0'

# ---- A. 交付文件名 ---------------------------------------------------------
# (相对路径, 查找, 替换, 期望命中次数)
EDITS = [
    # Python 侧单一来源
    ('tools/_root.py',
     "DELIVERABLE = ROOT / '" + OLD_FILE + "'",
     "DELIVERABLE = ROOT / '" + NEW_FILE + "'", 1),

    # 5 个测试脚本：把字面量换成共享常量
    ('tools/test_step1.js',
     "return fs.readFileSync(path.join(ROOT, '" + OLD_FILE + "'), 'utf8');",
     "return fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');", 1),
    ('tools/test_step2_tutorial.js',
     "const html = fs.readFileSync(path.join(ROOT, '" + OLD_FILE + "'), 'utf8');",
     "const html = fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');", 1),
    ('tools/test_display.js',
     "const HTML = fs.readFileSync(path.join(ROOT, '" + OLD_FILE + "'), 'utf8');",
     "const HTML = fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');", 1),
    ('tools/test_shell.js',
     "const HTML = fs.readFileSync(path.join(ROOT, '" + OLD_FILE + "'), 'utf8');",
     "const HTML = fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');", 1),
    ('tools/test_step4.js',
     "  const html = fs.readFileSync(path.join(ROOT, '" + OLD_FILE + "'), 'utf8');",
     "  const html = fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');", 1),

    # build.py 文档字符串里的产物名
    ('tools/build.py',
     '-->  ' + OLD_FILE,
     '-->  ' + NEW_FILE, 1),

    # ---- B. 品牌名 ----
    ('src/main.shell.html', '<title>' + OLD_BRAND + ' · 含七关互动教程</title>',
     '<title>' + NEW_BRAND + ' · 含七关互动教程</title>', 1),
    ('src/main.shell.html', '<h1>' + OLD_BRAND + '</h1>',
     '<h1>' + NEW_BRAND + '</h1>', 1),
    ('src/main.shell.html', 'title="' + OLD_BRAND + '七关互动教程"',
     'title="' + NEW_BRAND + '七关互动教程"', 1),
    ('src/main.shell.html', 'title="' + OLD_BRAND + '游戏介绍"',
     'title="' + NEW_BRAND + '游戏介绍"', 1),

    ('src/tutorial.shell.html', '<title>' + OLD_BRAND + ' · 互动教程</title>',
     '<title>' + NEW_BRAND + ' · 互动教程</title>', 1),
    ('src/tutorial.shell.html', '<h1>' + OLD_BRAND + '</h1>',
     '<h1>' + NEW_BRAND + '</h1>', 1),
    ('src/tutorial.shell.html', 'title="' + OLD_BRAND + '游戏介绍"',
     'title="' + NEW_BRAND + '游戏介绍"', 1),

    ('src/guide.html', '<title>' + OLD_BRAND + ' · 游戏介绍</title>',
     '<title>' + NEW_BRAND + ' · 游戏介绍</title>', 1),
    ('src/guide.html', '<h1>' + OLD_BRAND + ' · 游戏介绍</h1>',
     '<h1>' + NEW_BRAND + ' · 游戏介绍</h1>', 1),
    # 介绍页的装饰英文眉标：改成与仓库名一致的英文名
    ('src/guide.html', 'CORE ARCHIPELAGO / FIELD MANUAL / V10',
     'LEAD OR DIE / FIELD MANUAL / V' + VERSION, 1),
]

# 需要补 require 的测试脚本
NEED_REQUIRE = [
    'tools/test_step1.js', 'tools/test_step2_tutorial.js',
    'tools/test_display.js', 'tools/test_shell.js', 'tools/test_step4.js',
]
REQUIRE_LINE = "const { DELIVERABLE } = require('./_root.js');"


def main():
    problems = []
    plan = []

    for rel, old, new, expect in EDITS:
        p = ROOT / rel
        if not p.exists():
            problems.append('%s: 文件不存在' % rel)
            continue
        t = io.open(p, encoding='utf-8', newline='').read()
        n = t.count(old)
        if n != expect:
            problems.append('%s: 锚点命中 %d 次（期望 %d）\n      %r'
                            % (rel, n, expect, old[:90]))
            continue
        plan.append((rel, old, new, n))

    # 测试脚本需要 require 共享常量
    for rel in NEED_REQUIRE:
        p = ROOT / rel
        if not p.exists():
            continue
        t = io.open(p, encoding='utf-8', newline='').read()
        if REQUIRE_LINE in t:
            continue                      # 已有，幂等
        if "require('./_root.js')" in t:
            continue
        plan.append((rel, "const ROOT = path.resolve(__dirname, '..');",
                     "const ROOT = path.resolve(__dirname, '..');\n" + REQUIRE_LINE, 1))

    print('=== 预检 ===')
    for rel, old, new, n in plan:
        print('  %-32s %d 处' % (rel, n))
    print()

    if problems:
        print('❌ 有锚点未命中：')
        for x in problems:
            print('   ' + x)
        return 1
    if not plan:
        print('无需改动。')
        return 0

    if not APPLY:
        print('（预检模式，未写入；加 --apply 执行）')
        return 0

    # 按文件聚合，逐条替换
    by_file = {}
    for rel, old, new, _ in plan:
        by_file.setdefault(rel, []).append((old, new))

    print('=== 写入 ===')
    for rel, subs in by_file.items():
        p = ROOT / rel
        t = io.open(p, encoding='utf-8', newline='').read()
        for old, new in subs:
            t = t.replace(old, new, 1)
        io.open(p, 'w', encoding='utf-8', newline='').write(t)
        print('  %-32s %d 处' % (rel, len(subs)))

    print()
    print('✅ 改名完成。后续步骤：')
    print('   1. python tools/build.py            # 产物会写到新文件名')
    print('   2. 删除旧交付文件 ' + OLD_FILE)
    print('   3. python tools/build.py --accept   # 更新基线')
    print('   4. 跑 9 组测试与 difftest')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
