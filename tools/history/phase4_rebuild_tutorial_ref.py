"""阶段 4：重建教程脚本参考 + 重新导出 13 条补丁。

## 背景：为什么格式化会让 13 条补丁全失效

补丁是**精确子串匹配**，锚点（old）就是引擎里那些压缩长行。格式化后锚点文本变了，
13 条全部 matches=0。

## 重建思路（机械构造，不靠人工重写）

教程脚本 = 引擎脚本 + 补丁（教程独有的那部分：独立存档、lesson 脚手架、
11×11 棋盘、高亮绘制、对话框接线）。

**补丁的 `new` 侧就是"教程独有内容"，它语义正确、只是格式旧。**
所以：

    新教程脚本 = 把旧补丁的 new 侧应用到【格式化后的引擎】上

这一步能机械完成，因为：
  · old 侧在格式化引擎里仍能找到 —— prettier 只改空白，**token 序列不变**；
  · 用 token 序列匹配（忽略空白）定位每个 old 在格式化引擎里的行区间；
  · 把该区间换成对应补丁的 new 侧。

然后再跑 `derive_patches.py`：它从「引擎」与「教程脚本参考」的差异重新导出补丁，
并**自校验**（应用后必须逐字符复现参考）。产出即 13 条新锚点。

## 为什么不让 prettier 直接格式化整个教程脚本

那样教程侧（lesson 脚手架、独立 UI）的排版会与引擎侧不一致，且
`tutorial.lessons.js` 需要跟着改 —— 多一处漂移源。本方案让教程侧
**保持原有格式**（与之前完全一致），只有引擎侧被格式化，改动面最小。

用法：
    python tools/rebuild_tutorial_reference.py --check     # 预检：能否定位全部 13 条
    python tools/rebuild_tutorial_reference.py --apply     # 生成教程脚本参考
"""
import importlib.util
import io
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)

ENGINE = ROOT / 'src' / 'main.script.js'
PATCHES = ROOT / 'src' / 'tutorial.patches.py'
REF = ROOT / 'build' / 'reference' / 'tutorial.script.js'
TMP = ROOT / '.fmt'

PRETTIER = 'prettier@3.9.9'
PRINT_WIDTH = '120'

APPLY = '--apply' in sys.argv


def run_prettier(path, extra=()):
    cmd = ['npx', '--yes', PRETTIER, '--parser', 'babel',
           '--print-width', PRINT_WIDTH, '--single-quote']
    cmd += list(extra)
    cmd.append(str(path))
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', shell=True)

BLOB_RE = re.compile(r"atob\('([A-Za-z0-9+/=]+)'\)")
SCRIPT_RE = re.compile(r'<script[^>]*>(.*?)</script>', re.S)


def load_patches():
    spec = importlib.util.spec_from_file_location('tp', PATCHES)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PATCHES


# ---- token 化：忽略空白与注释，只留有语义的片段 -----------------------------
TOKEN_RE = re.compile(r"""
      '(?:\\.|[^'\\])*'          # 单引号串
    | "(?:\\.|[^"\\])*"          # 双引号串
    | `(?:\\.|[^`\\])*`          # 模板串（不处理 ${} 嵌套，够用）
    | [A-Za-z_$][\w$]*           # 标识符
    | \d+\.?\d*(?:[eE][+-]?\d+)? # 数字
    | [^\s]                      # 其他单字符（运算符、括号等）
""", re.X)


def tokenize(text):
    """返回 [(token, 结束偏移)]，**丢弃空白与注释**。

    ⚠️ 必须丢弃空白：这个匹配的全部意义就是"忽略格式化差异"。
    第一版把空白也当作 token 保留（记成 <SKIP:...>），结果引擎与 old 的空白
    必然不同（prettier 加了换行与缩进），13 条里 9 条直接分叉在第一个空格上。
    """
    toks = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if text.startswith('//', i):
            j = text.find('\n', i)
            i = n if j < 0 else j + 1
            continue
        if text.startswith('/*', i):
            j = text.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        m = TOKEN_RE.match(text, i)
        if m:
            toks.append((m.group(0), m.end()))
            i = m.end()
        else:
            i += 1
    return toks


def align_span(eng_vals, pat_toks, min_ratio=0.55, min_density=0.80):
    """在引擎 token 流里找 pat_toks 的最佳对应区间，容忍插入/替换。

    为什么不能用"精确子序列匹配"：prettier 会做真 token 变化 ——
        `c=>`      -> `(c)=>`         （给箭头函数参数补括号）
        `return x` -> `return (x)`    （给返回表达式补括号）
    所以 old 的 token 序列不可能与格式化引擎逐一致。实测 13 条里 9 条因此失败。

    判据（不要用"首尾块长度"——实测那会误杀正确的对齐）：
      · 匹配率 = 匹配 token 数 / old token 数  >= min_ratio
      · 匹配密度 = 匹配 token 数 / 推断出的跨距 >= min_density
        密度低说明跨距里塞了大量不相关 token，是误命中。

    返回 (start_token_idx, end_token_idx) 或 None。
    """
    import difflib
    sm = difflib.SequenceMatcher(None, eng_vals, pat_toks, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
    if not blocks:
        return None
    matched = sum(b.size for b in blocks)
    if matched / len(pat_toks) < min_ratio:
        return None
    start = blocks[0].a
    end = blocks[-1].a + blocks[-1].size
    span = end - start
    if span <= 0:
        return None
    if matched / span < min_density:
        return None
    return start, end, matched


def main():
    engine_text = io.open(ENGINE, encoding='utf-8', newline='').read()
    patches = load_patches()

    eng_toks = tokenize(engine_text)
    eng_vals = [t for t, _ in eng_toks]
    print('引擎: %d 字符, %d 个 token' % (len(engine_text), len(eng_toks)))

    # ---- 为每条补丁在格式化引擎里定位（token 序列匹配） -------------------
    plan = []
    failed = []
    for p in patches:
        if 'new' not in p:
            # new_file 型：同样要定位，替换成 lessons 文件内容
            new_text = io.open(ROOT / 'src' / p['new_file'], encoding='utf-8',
                               newline='').read()
        else:
            new_text = p['new']

        pat_toks = [t for t, _ in tokenize(p['old'])]
        if not pat_toks:
            failed.append((p['name'], 'old 里没有 token'))
            continue

        span = align_span(eng_vals, pat_toks)
        if not span:
            failed.append((p['name'], '无法在格式化引擎里对齐（匹配率或密度不足）'))
            continue
        s, e, matched = span
        span_len = e - s

        start_off = eng_toks[s - 1][1] if s > 0 else 0
        end_off = eng_toks[e - 1][1]
        plan.append((p, start_off, end_off, new_text))
        print('  %-42s old %5d tok -> 引擎 %5d tok 匹配 %5d (密度 %.0f%%)'
              % (p['name'][:42], len(pat_toks), span_len, matched,
                 100.0 * matched / span_len))

    print()
    if failed:
        print('❌ 有 %d 条无法定位：' % len(failed))
        for name, why in failed:
            print('   %s: %s' % (name[:50], why))
        return 1
    print('✅ 13 条锚点全部按 token 序列唯一定位')

    # ---- 倒序替换（避免偏移失效） ------------------------------------------
    out = engine_text
    for p, a, b, new_text in sorted(plan, key=lambda x: -x[1]):
        out = out[:a] + new_text + out[b:]

    print()
    print('生成的教程脚本: %d -> %d 字符' % (len(engine_text), len(out)))
    if '__TUTORIAL_B64__' in out:
        print('❌ 生成的脚本仍含 __TUTORIAL_B64__，异常')
        return 1
    if out.count('__GUIDE_B64__') != 1:
        print('❌ __GUIDE_B64__ 出现 %d 次，应为 1' % out.count('__GUIDE_B64__'))
        return 1
    print('✅ 占位符检查通过（无 __TUTORIAL_B64__，__GUIDE_B64__ 恰好 1 次）')

    # ---- 用 prettier 把教程脚本也格式化（与引擎同一套规则） ---------------
    # 为什么必须格式化：prettier 会做 `c=>` -> `(c)=>`、`a||b` -> `a ?? b`
    # 这类**真 token 变化**。若教程侧保持旧格式，derive_patches 导出的补丁
    # 两侧风格不一致，下一步重导出时会立刻再次失配。
    # 统一格式化后，derive_patches 的 diff 只包含**语义差异**（教程独有的那部分），
    # 这正是补丁该有的样子。
    print()
    print('=== prettier 格式化教程脚本（--debug-check 校验 AST 等价） ===')
    TMP.mkdir(parents=True, exist_ok=True)
    raw = TMP / 'tutorial.raw.js'
    io.open(raw, 'w', encoding='utf-8', newline='\n').write(out)
    r = run_prettier(raw, extra=['--debug-check'])
    if r.returncode != 0:
        print(((r.stdout or '') + (r.stderr or ''))[:1500])
        print('❌ 教程脚本 --debug-check 失败')
        return 1
    print('  ✅ AST 等价')
    r = run_prettier(raw)
    if r.returncode != 0 or not (r.stdout or '').strip():
        print(((r.stdout or '') + (r.stderr or ''))[:1500])
        print('❌ 教程脚本格式化失败')
        return 1
    out = r.stdout
    print('  %d 字符' % len(out))

    if not APPLY:
        print()
        print('（预检模式，未写入；加 --apply 执行）')
        return 0

    # 备份旧的参考（一次性）
    if REF.exists():
        bak = REF.with_suffix('.js.pre-format')
        if not bak.exists():
            shutil.copyfile(REF, bak)
            print('旧参考已备份: %s' % bak.name)
    io.open(REF, 'w', encoding='utf-8', newline='').write(out)
    print('已写入 %s' % REF)
    print()
    print('下一步: python tools/derive_patches.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
