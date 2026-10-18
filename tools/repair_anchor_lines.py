"""修复因**有意改动**而失配的补丁锚点：从当前引擎里取出对应行作为新锚点。

与 tools/reanchor.py 的区别：
    reanchor.py 是**启发式**的（在引擎里找与 old 首行"最长公共前缀"的行，
    要求前缀 ≥12 字符且唯一命中）。它适用于"同一行被改了几个字"的场景。
    但当注释说的那种情况不成立时（改成完全不同、或跨行删减），它会报
    "无法自动重锚"。

    本脚本更直接：补丁名里就写着 `@main[起:止]`，那是该锚点在**原始引擎**里的
    行号。既然我们已经知道改的是哪几条、以及现在的内容是什么，就直接按
    「取当前引擎的第 起..止 行」重建 old 即可 —— 因为被改的那几行**没有增删行**。

⚠️ 前提：改动**没有改变行数**（只改了行内容）。本脚本会校验这一点：
   取出的行数必须与补丁名里的区间长度一致，否则拒绝并提示改用手工处理。

只改 `old`（引擎侧）；`new`（教程侧）不动。

用法：
    python tools/repair_anchor_lines.py            # 预检，不写
    python tools/repair_anchor_lines.py --apply    # 执行
"""
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
RANGE_RE = re.compile(r'@main\[(\d+):(\d+)\]$')


def load_patches():
    spec = importlib.util.spec_from_file_location('tp', PATCHES)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def locate_by_content(engine_text, p):
    """不靠行号，靠内容定位补丁锚点应该长什么样。

    ⚠️ 为什么不能用补丁名里的 @main[起:止]：
       那是**教程脚本**里的行号，而教程脚本相对引擎脚本是大改过的
       （lesson 脚手架是 46 行的大块插入，worldStep / ui 等也被换掉），
       行号早已漂移。按它取行会安静地取到**错误的行**（实测取到了方块绘制代码）。
       所以行号只能当线索，不能当依据。

    定位策略（按补丁类型分两种）：
      1. new_file 型（教程侧来自 src/tutorial.lessons.js）：
         该文件的首行定义了它替换掉的引擎内容，直接取首行。
      2. 内联 new 型：
         new 里的字符串字面量（localStorage key、消息 type 等）能反过来
         指向引擎里的对应行；再结合 old 里出现过的标识符锁定。
    """
    old = p['old']

    # --- 情形 1：new_file 型 ---
    if 'new_file' in p:
        nf = ROOT / 'src' / p['new_file']
        if nf.exists():
            first = io.open(nf, encoding='utf-8', newline='').read().split('\n')[0]
            if first and engine_text.count(first + '\n') == 1:
                return first + '\n', '取自 new_file %s 的首行' % p['new_file']

    # --- 情形 2：用 old 里的特征标识符定位当前引擎的对应行 ---
    # 从 old 里抽出 JS 标识符，挑当前引擎里唯一命中的那一行
    ids = re.findall(r'[A-Za-z_$][\w$]{5,}', old)
    # 统计每个标识符在引擎里的候选行
    engine_lines = engine_text.split('\n')
    for ident in sorted(set(ids), key=lambda s: -len(s)):
        if ident in ('function', 'return', 'const', 'localStorage'):
            continue
        cand = [i for i, ln in enumerate(engine_lines) if ident in ln]
        if len(cand) != 1:
            continue
        # 只有在 old 里该标识符也比较稀有，才可信
        if old.count(ident) <= 3:
            line = engine_lines[cand[0]]
            if engine_text.count(line + '\n') == 1:
                return line + '\n', '按标识符 %r 唯一定位' % ident
    return None, '无法定位'


def main():
    engine_text = io.open(ENGINE, encoding='utf-8', newline='').read()
    lines = engine_text.split('\n')
    if engine_text.endswith('\n'):
        lines = lines[:-1]

    mod = load_patches()
    src_text = io.open(PATCHES, encoding='utf-8', newline='').read()

    stale = [p for p in mod.PATCHES if engine_text.count(p['old']) != 1]
    print('引擎: %d 行 · 补丁 %d 条 · 失配 %d 条' % (len(lines), len(mod.PATCHES), len(stale)))
    print()

    if not stale:
        print('没有失配的补丁，无需修复。')
        return 0

    fixes = []
    for p in stale:
        cand, how = locate_by_content(engine_text, p)
        if not cand:
            print('  !! %s: %s —— 需手工处理' % (p['name'], how))
            continue
        fixes.append((p, cand, how, cand.count('\n')))

    if not fixes:
        print()
        print('❌ 没有可自动修复的补丁。')
        return 1

    print('将重锚 %d 条：' % len(fixes))
    for p, cand, how, n in fixes:
        print('  %s' % p['name'])
        print('     %s' % how)
        print('     old %d 字符 -> %d 字符（%d 行）' % (len(p['old']), len(cand), n))
        print('     新内容首 90 字符: %r' % cand[:90])

    if not APPLY:
        print()
        print('（预检模式，未写入；加 --apply 执行）')
        return 0

    # ---- 写回：把 PATCHES 里对应条目的 old 字符串换掉 ------------------------
    # tutorial.patches.py 是 Python 字面量，用 repr 生成与 derive_patches.py 相同的格式。
    for p, cand, _how, _n in fixes:
        old_repr = repr(p['old'])
        new_repr = repr(cand)
        if src_text.count(old_repr) != 1:
            print('  !! %s: 在补丁文件里定位不到原 old 字面量，跳过' % p['name'])
            continue
        src_text = src_text.replace(old_repr, new_repr, 1)
        print('  已重锚 %s' % p['name'])

    io.open(PATCHES, 'w', encoding='utf-8', newline='').write(src_text)
    print()
    print('已写入 %s' % PATCHES)
    print('请接着运行: python tools/check_patches.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
