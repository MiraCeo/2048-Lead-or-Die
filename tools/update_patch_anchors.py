"""阶段 4：把 13 条补丁的 `old`（引擎侧锚点）更新为**格式化后**的对应文本。

## 为什么不用 derive_patches.py 重新导出

试过，不适合：derive_patches 从**行级 diff** 重新切 hunk。格式化把原来的长行拆开后，
13 个 hunk 裂成 24 个碎片，重组时出现组合错误（实测 VERIFY MISMATCH）。
而且它有一步"纯插入/删除就借一行邻居当上下文"，在相邻 hunk 变多后会**吞掉紧邻的下一个 hunk**。

## 本方案

**保留原有 13 条补丁的结构与 `new` 侧**，只把 `old` 换成格式化引擎里对应的那段。
这样：
  · 教程侧（`new`）内容完全不变 —— 教程行为、`tutorial.lessons.js` 都不动；
  · 13 条补丁的语义边界不变，只是锚点文本变成了格式化后的样子；
  · 补丁应用后就能正确重建教程脚本。

## 怎么定位每条补丁在格式化引擎里的位置

补丁的 `old` 是**旧格式**文本，在格式化引擎里不可能精确匹配。改用 token 对齐：

  token 化时丢弃空白/注释，于是 prettier 的排版差异被抹平；剩下的真 token 变化
  （`c=>` -> `(c)=>`、`return x` -> `return (x)`）用 difflib 容忍。
  判据是"匹配率"与"匹配密度"，**不要**用首尾块长度（实测会误杀正确的对齐）。

定位后取该 token 区间对应的源文本作为新锚点。

用法：
    python tools/update_patch_anchors.py --check    # 预检：13 条能否全部对齐
    python tools/update_patch_anchors.py --apply    # 写回 tutorial.patches.py
"""
import difflib
import importlib.util
import io
import re
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

APPLY = '--apply' in sys.argv

TOKEN_RE = re.compile(r"""
      '(?:\\.|[^'\\])*'
    | "(?:\\.|[^"\\])*"
    | `(?:\\.|[^`\\])*`
    | [A-Za-z_$][\w$]*
    | \d+\.?\d*(?:[eE][+-]?\d+)?
    | [^\s]
""", re.X)


def tokenize(text):
    """返回 [(token, 结束偏移)]，**丢弃空白与注释**（这是容忍格式化差异的关键）。"""
    toks, i, n = [], 0, len(text)
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


def align(eng_vals, pat_toks, min_ratio=0.55, min_density=0.80):
    """在引擎 token 流里定位 pat_toks 的对应区间。返回 (start, end) 或 None。"""
    sm = difflib.SequenceMatcher(None, eng_vals, pat_toks, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
    if not blocks:
        return None
    matched = sum(b.size for b in blocks)
    if matched / len(pat_toks) < min_ratio:
        return None
    start = blocks[0].a
    end = blocks[-1].a + blocks[-1].size
    if end - start <= 0 or matched / (end - start) < min_density:
        return None
    return start, end


def load_patches():
    spec = importlib.util.spec_from_file_location('tp', PATCHES)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PATCHES


def emit(patches, path):
    """按 derive_patches.py 的格式写出（保持既有风格）。"""
    chunks = []
    for p in patches:
        if 'new_file' in p:
            chunks.append('    {\n        "name": %r,\n        "old": %r,\n'
                          '        "new_file": %r,\n    },\n'
                          % (p['name'], p['old'], p['new_file']))
        else:
            chunks.append('    {\n        "name": %r,\n        "old": %r,\n'
                          '        "new": %r,\n    },\n'
                          % (p['name'], p['old'], p['new']))
    io.open(path, 'w', encoding='utf-8', newline='').write(
        '"""GENERATED -- 由 tools/update_patch_anchors.py 重新锚定（阶段 4 格式化）。\n\n'
        'Ordered literal block replacements applied to src/main.script.js to produce\n'
        "the tutorial's embedded script. Each anchor must match exactly once; the build\n"
        'fails loudly otherwise, so engine edits cannot silently drift the tutorial.\n\n'
        '阶段 4 说明：引擎已由 prettier 格式化为可读代码，所以这里的 old 也是格式化\n'
        '文本。new 侧（教程侧）保持原有格式不变 —— 只有引擎侧被格式化。\n'
        '"""\n\n'
        'PATCHES = [\n' + ''.join(chunks) + ']\n')


def main():
    engine_text = io.open(ENGINE, encoding='utf-8', newline='').read()
    eng_toks = tokenize(engine_text)
    eng_vals = [t for t, _ in eng_toks]
    patches = load_patches()

    print('引擎: %d 字符, %d token' % (len(engine_text), len(eng_toks)))
    print('补丁: %d 条' % len(patches))
    print()

    updated = []
    failed = []
    for p in patches:
        pat_toks = [t for t, _ in tokenize(p['old'])]
        span = align(eng_vals, pat_toks)
        if not span:
            failed.append((p['name'], '无法对齐'))
            continue
        s, e = span
        a = eng_toks[s - 1][1] if s > 0 else 0
        b = eng_toks[e - 1][1]
        new_old = engine_text[a:b]
        # 锚点以换行结尾更稳（整行边界）
        if b < len(engine_text) and engine_text[b] == '\n':
            new_old += '\n'
        if engine_text.count(new_old) != 1:
            failed.append((p['name'], '新锚点在引擎里命中 %d 次'
                           % engine_text.count(new_old)))
            continue
        old_len, new_len = len(p['old']), len(new_old)
        updated.append({
            'name': p['name'],
            'old': new_old,
            **({'new_file': p['new_file']} if 'new_file' in p else {'new': p['new']}),
        })
        print('  %-42s %6d -> %6d 字符  (token %d -> %d)'
              % (p['name'][:42], old_len, new_len, len(pat_toks), e - s))

    print()
    if failed:
        print('❌ %d 条失败：' % len(failed))
        for n, why in failed:
            print('   %s: %s' % (n[:52], why))
        return 1
    print('✅ 13 条锚点全部更新为格式化文本，且各自在引擎里唯一')

    if not APPLY:
        print()
        print('（预检模式，未写入；加 --apply 执行）')
        return 0

    emit(updated, PATCHES)
    print()
    print('已写入 %s' % PATCHES)
    print('下一步: python tools/check_patches.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
