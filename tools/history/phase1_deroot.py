"""阶段 1：把写死的 `D:\\2048` 换成从仓库结构推导。

设计原则（上一版连续三轮栽在转义层级上，这次改掉做法）：
  1. **不手写反斜杠字面量**，一律用 chr(92) 拼接，让形态在源码里可见。
  2. **先预检、后写入**：默认只报告命中情况，--apply 才真正改。
  3. Python 与 JS 形态不同：Python raw 串里是 1 个反斜杠，JS 普通串里是 2 个。
     两者各用各的常量，且用 repr 打印出来供人工核对。

    python tools/deroot.py            # 预检（不改文件）
    python tools/deroot.py --apply    # 执行

一次性脚本，执行完归档到 tools/history/。
"""
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

_HERE = Path(__file__).resolve().parent
# 本脚本执行时临时放在 .migration/ 下，现已归档到 tools/history/。
# 两种位置都要能定位仓库根：向上找到"含 tools/ 的那一级"。
ROOT = next((p for p in [_HERE, *_HERE.parents] if (p / 'tools').is_dir()), _HERE)
TOOLS = ROOT / 'tools'
APPLY = '--apply' in sys.argv

BS = chr(92)                       # 一个反斜杠
P_PY = 'D:' + BS + '2048'          # Python raw 串形态（1 个反斜杠）
P_JS = 'D:' + BS + BS + '2048'     # JS 普通串形态（2 个反斜杠）
DELIV = '2048小游戏-教程七关.html'

PY_ROOT_LINE = "ROOT = Path(r'" + P_PY + "')"
JS_ROOT_CONST = "const ROOT = '" + P_JS + "';"

print('=== 匹配形态自查（repr，人工核对） ===')
print('  P_PY（Python 用）: %r' % P_PY)
print('  P_JS（JS 用）    : %r' % P_JS)
print()

PY_HEAD = ("sys.path.insert(0, str(Path(__file__).resolve().parent))\n"
           "from _root import PATHS\n")

# ---- Python：整块锚点替换（必须覆盖旧的 SRC/OUT_FILE/REFERENCE 行，否则它们会覆盖新值）
PY_BLOCK_BUILD = (
    "ROOT = Path(r'" + P_PY + "')\n"
    "SRC = ROOT / 'src'\n"
    "OUT_FILE = ROOT / '" + DELIV + "'\n"
    "REFERENCE = ROOT / 'build' / 'reference' / '2048.original.html'"
)
PY_BLOCK_EXTRACT = (
    "ROOT = Path(r'" + P_PY + "')\n"
    "SHIPPED = ROOT / '" + DELIV + "'\n"
    "SRC = ROOT / 'src'\n"
    "REF = ROOT / 'build' / 'reference'"
)
PY_BLOCK_CHECK = (
    "ROOT = Path(r'" + P_PY + "')\n"
    "SRC = ROOT / 'src'"
)

PY_LINE_REPL = {
    # build.py 中 ROOT 即仓库根，其余用 ROOT 派生的行照旧即可（能正常工作）
    'build.py': (PY_BLOCK_BUILD,
                 PY_HEAD + "\nROOT = PATHS.ROOT\nSRC = PATHS.SRC\n"
                           "OUT_FILE = PATHS.DELIVERABLE\nREFERENCE = PATHS.ORIGINAL"),
    'extract_sources.py': (PY_BLOCK_EXTRACT,
                           PY_HEAD + "\nROOT = PATHS.ROOT\nSHIPPED = PATHS.DELIVERABLE\n"
                                     "SRC = PATHS.SRC\nREF = PATHS.REFERENCE"),
    'check_patches.py':  (PY_BLOCK_CHECK, PY_HEAD + "\nROOT = PATHS.ROOT\nSRC = PATHS.SRC"),
    # 其余脚本的 ROOT 行后面没有紧跟的 ROOT/ 派生行，单行锚点即可
    'derive_patches.py': (PY_ROOT_LINE, PY_HEAD + "\nROOT = PATHS.ROOT"),
    'dump_lines.py':     (PY_ROOT_LINE, PY_HEAD + "\nROOT = PATHS.ROOT"),
    'probe_step2.py':    (PY_ROOT_LINE, PY_HEAD + "\nROOT = PATHS.ROOT"),
    'reanchor.py':       (PY_ROOT_LINE, PY_HEAD + "\nROOT = PATHS.ROOT"),
    'repair_patches.py': (PY_ROOT_LINE, PY_HEAD + "\nROOT = PATHS.ROOT"),
    'build_engine.py':   ("DEFAULT_HTML = r'" + P_PY + BS + DELIV + "'",
                          PY_HEAD + "\nDEFAULT_HTML = str(PATHS.DELIVERABLE)"),
    'diff_tutorial.py':  ("HTML = Path(r'" + P_PY + BS + DELIV + "')",
                          PY_HEAD + "\nHTML = PATHS.DELIVERABLE"),
    'report_tutorial.py':("HTML = Path(r'" + P_PY + BS + DELIV + "')\n"
                          "OUT = Path(r'" + P_PY + BS + "build" + BS + "reports" + BS + "tutorial_hooks.txt')",
                          PY_HEAD + "\nHTML = PATHS.DELIVERABLE\nOUT = PATHS.REPORTS / 'tutorial_hooks.txt'"),
    'diff_engine.py':    ("import re\nimport difflib\n\n"
                          "HTML = r'" + P_PY + BS + DELIV + "'\n"
                          "ENG = r'" + P_PY + BS + ".analyze" + BS + "core-fleet.engine.js'",
                          "import re\nimport difflib\nimport sys\nfrom pathlib import Path\n\n"
                          + PY_HEAD + "\nHTML = str(PATHS.DELIVERABLE)\nENG = str(PATHS.ANALYZE_ENGINE)"),
}

# ---- JS：手写解析器，彻底避开转义层级 --------------------------------
# 这里已经错了四轮，根因都是"在源码里拼反斜杠"。改法：逐字符扫描，
# 把连续反斜杠当分隔符，不做任何转义拼接。
DELIV_JS_EXPR = "path.join(ROOT, '" + DELIV + "')"


def rewrite_js_paths(text: str):
    """把 'D:(若干反斜杠)<路径>' 换成 path.join(ROOT, ...) / ROOT。

    要点：
      - **连引号一起吃掉**：只换内容会留下原引号，导致 'path.join(...)' 这种
        引号嵌套错乱（前几轮就栽在这）。
      - **丢弃仓库目录名那一段**：D:\\2048\\build\\engine.js 的 '2048' 是仓库根
        自身的名字，路径由 ROOT 表达，不能再列一遍。
        若整条路径就只有仓库名（'D:\\2048'），换成裸的 ROOT 标识符。
    返回 (新文本, 替换次数)。
    """
    out = []
    i = 0
    n = len(text)
    replaced = 0
    while i < n:
        ch = text[i]
        if ch in "'\"" and i + 2 < n and text[i + 1] == 'D' and text[i + 2] == ':':
            quote = ch
            j = i + 3
            k = j
            while k < n and text[k] == BS:
                k += 1
            if k > j:                      # D: 之后确有反斜杠
                m = k
                while m < n and (text[m].isalnum() or text[m] in '.-_' or text[m] == BS
                                 or ord(text[m]) > 0x2E00):
                    m += 1
                # 必须正好以同种引号收尾
                if m < n and text[m] == quote:
                    segs = [s for s in text[k:m].split(BS) if s]
                    if segs:
                        if len(segs) == 1:
                            expr = 'ROOT'          # 就是仓库根本身
                        else:
                            expr = ("path.join(ROOT, " +
                                    ', '.join("'" + s + "'" for s in segs[1:]) + ")")
                        out.append(expr)
                        replaced += 1
                        i = m + 1
                        continue
        out.append(ch)
        i += 1
    return ''.join(out), replaced

JS_FILES = ['report_radius_throughput.js', 'report_regen_math.js', 'report_tech_cost.js',
            'test_display.js', 'test_fx.js', 'test_rules.js', 'test_shell.js',
            'test_step1.js', 'test_step2.js', 'test_step2_tutorial.js', 'test_step4.js']

JS_ROOT_LINE = ("const path = require('path');\n"
                "// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符\n"
                "const ROOT = path.resolve(__dirname, '..');")


def preview_py():
    print('=== Python 侧预检 ===')
    rows = []
    for name, (anchor, _) in PY_LINE_REPL.items():
        text = (TOOLS / name).read_text(encoding='utf-8')
        n = text.count(anchor)
        rows.append((name, n))
        print('  %-22s 命中 %d' % (name, n))
    return all(n == 1 for _, n in rows)


def preview_js():
    print('\n=== JS 侧预检（手写解析器） ===')
    ok = True
    for name in JS_FILES:
        text = (TOOLS / name).read_text(encoding='utf-8')
        _, n = rewrite_js_paths(text)
        has_root = (JS_ROOT_CONST in text)
        print('  %-30s 路径 %d 处  ROOT常量=%s' % (name, n, '有' if has_root else '无'))
        if n == 0 and not has_root:
            ok = False
            k = text.find('D:')
            if k >= 0:
                print('       文件内原文: %r' % text[k:k + 46])
    return ok


def apply_py():
    print('\n=== Python 侧写入 ===')
    for name, (anchor, repl) in PY_LINE_REPL.items():
        p = TOOLS / name
        text = p.read_text(encoding='utf-8')
        p.write_text(text.replace(anchor, repl, 1), encoding='utf-8', newline='')
        print('  %-22s 已改写' % name)


def apply_js():
    print('\n=== JS 侧写入 ===')
    for name in JS_FILES:
        p = TOOLS / name
        text = p.read_text(encoding='utf-8')
        text, n = rewrite_js_paths(text)
        if JS_ROOT_CONST in text:
            text = text.replace(JS_ROOT_CONST, JS_ROOT_LINE, 1)
        if "require('path')" not in text:
            lines = text.split('\n')
            for i, ln in enumerate(lines):
                if ln.startswith('const ') and 'require(' in ln:
                    lines.insert(i + 1, JS_ROOT_LINE)
                    break
            text = '\n'.join(lines)
        elif 'const ROOT = path.resolve' not in text:
            lines = text.split('\n')
            for i, ln in enumerate(lines):
                if "require('path')" in ln:
                    lines.insert(i + 1,
                                 "// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符\n"
                                 "const ROOT = path.resolve(__dirname, '..');")
                    break
            text = '\n'.join(lines)
        p.write_text(text, encoding='utf-8', newline='')
        print('  %-30s 已改写（路径 %d 处）' % (name, n))


def verify():
    me = Path(__file__).name
    print('\n=== 残留检查 ===')
    bad = []
    for p in sorted(list(TOOLS.glob('*.py')) + list(TOOLS.glob('*.js'))):
        if p.name == me:
            continue
        t = p.read_text(encoding='utf-8')
        if P_PY in t:
            bad.append(p.name)
            for i, ln in enumerate(t.split('\n'), 1):
                if P_PY in ln:
                    print('  !! %s:%d  %s' % (p.name, i, ln.strip()[:110]))
    if not bad:
        print('  ✅ 无残留')

    print('\n=== 语法校验 ===')
    fails = []
    for p in sorted(TOOLS.glob('*.py')):
        if p.name == me:
            continue
        r = subprocess.run([sys.executable, '-m', 'py_compile', str(p)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fails.append(p.name)
            print('  FAIL %s: %s' % (p.name, (r.stderr or '').strip()[:200]))
    for p in sorted(TOOLS.glob('*.js')):
        r = subprocess.run(['node', '--check', str(p)],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        if r.returncode != 0:
            fails.append(p.name)
            print('  FAIL %s: %s' % (p.name, (r.stderr or '').strip()[:200]))
    print('  语法错误 %d 个' % len(fails))
    return (not bad) and (not fails)


def main():
    if not APPLY:
        ok = preview_py() and preview_js()
        print('\n预检: %s' % ('全部命中 ✅' if ok else '有未命中 ❌'))
        print('（未改动任何文件；确认无误后加 --apply 执行）')
        return 0 if ok else 1

    if not (preview_py() and preview_js()):
        print('\n❌ 预检未通过，已中止（未写入任何文件）')
        return 1
    apply_py()
    apply_js()
    ok = verify()
    print()
    print('✅ 完成' if ok else '❌ 有问题，见上')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
