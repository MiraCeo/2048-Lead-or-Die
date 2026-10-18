"""一键验证：按**正确顺序**跑完整条链子。

为什么必须有它：本项目踩过一次"假通过"——

    v0.1.5 改了 `src/engine/80-ui.js`（舰队面板改为整块隐藏），
    但没有重建 `build/engine.js` 就跑了测试。
    测试读的是**旧引擎**，于是那条断言在旧文案上通过，报"0 失败"。
    两个月后（v0.2.0）重建引擎才暴露：`test_shell.js` 有一条断言早已失效。

这正是项目文档 §14.2③ 记过的坑，但那条规则靠人记 —— 现在改成一条命令。

顺序不能反：
    1. bundle_engine   src/engine/*.js  -> src/main.script.js
    2. build           组装交付 HTML（并与基线比对）
    3. build_engine    交付 HTML       -> build/engine.js   ← 漏了这步，测试就读旧引擎
    4. 测试 / 检查

用法：
    python tools/verify_all.py             # 全套（不含平衡测量与 difftest）
    python tools/verify_all.py --fast      # 跳过布局实测（较慢，要开浏览器）
    python tools/verify_all.py --balance   # 追加平衡复测（若已有基线）
"""
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _root import PATHS

FAST = '--fast' in sys.argv
WITH_BALANCE = '--balance' in sys.argv

PY = sys.executable
failures = []


def run(label, cmd, allow_fail=False):
    r = subprocess.run(cmd, cwd=PATHS.ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    ok = r.returncode == 0
    print('  %s  %-34s exit=%d' % ('通过' if ok else '失败', label, r.returncode))
    if not ok:
        failures.append(label)
        for line in out.splitlines():
            if any(k in line for k in ('失败', 'FAIL', 'FAILED', 'Error', 'error', 'stale')):
                print('        ' + line.strip()[:150])
    return ok


def main():
    print('=== 1. 重建引擎源码（engine/ → main.script.js） ===')
    run('bundle_engine', [PY, 'tools/bundle_engine.py', '--write', '--allow-diverge'])

    print()
    print('=== 2. 组装交付物 ===')
    run('build', [PY, 'tools/build.py'])

    print()
    print('=== 3. 从交付物重建无头引擎（★ 漏了这步测试会读旧引擎） ===')
    run('build_engine', [PY, 'tools/build_engine.py', '--out', 'build/engine.js'])

    print()
    print('=== 4. 补丁与品牌 ===')
    run('check_patches', [PY, 'tools/check_patches.py'])
    run('check_branding', [PY, 'tools/check_branding.py'])
    run('check_doc_links', [PY, 'tools/check_doc_links.py'])

    print()
    print('=== 5. 功能测试（10 组） ===')
    tests = [
        ('test_step1 engine', ['tools/test_step1.js', 'engine']),
        ('test_step1 tutorial', ['tools/test_step1.js', 'tutorial']),
        ('test_step2', ['tools/test_step2.js']),
        ('test_step2_tutorial', ['tools/test_step2_tutorial.js']),
        ('test_step4', ['tools/test_step4.js']),
        ('test_rules', ['tools/test_rules.js']),
        ('test_display', ['tools/test_display.js']),
        ('test_shell', ['tools/test_shell.js']),
        ('test_fx', ['tools/test_fx.js']),
        ('test_loose_matcher', ['tools/test_loose_matcher.js']),
    ]
    for label, args in tests:
        run(label, ['node'] + args)

    if not FAST:
        print()
        print('=== 6. 布局实测（4 分辨率，需开浏览器） ===')
        run('check_layout', [PY, 'tools/check_layout.py'])

    if WITH_BALANCE:
        print()
        print('=== 7. 平衡复测（与基线对比） ===')
        base = PATHS.BUILD / 'balance' / 'base.json'
        if base.exists():
            run('balance', ['node', 'tools/balance.js', '--engine', 'build/engine.js',
                            '--seeds', '10', '--turns', '400',
                            '--out', 'build/balance/after',
                            '--compare', 'build/balance/base'])
        else:
            print('  跳过（没有 build/balance/base.json）')

    print()
    if failures:
        print('❌ %d 项失败：%s' % (len(failures), ', '.join(failures)))
        return 1
    print('✅ 全部通过')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
