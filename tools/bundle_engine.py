"""打包器：把 src/engine/ 的域模块拼回 src/main.script.js。

**硬门槛：重建结果必须与拆分前逐字节相同。**

为什么这是硬门槛而不是"最好如此"：
    13 条教程补丁是精确子串匹配，锚点就是 main.script.js 里那些未格式化的压缩长行。
    重建差一个字节（哪怕只是多一个空行）-> `check_patches.py` 报 13 条全失配
    -> `build.py` 直接失败。所以"字节不变"就是本次重构的安全网。

模块文件的格式约定（见 tools/extract_engine.py）：
    前 3 行是以 `// ` 开头的模块注释头，其余是原样内容。
    本脚本按 manifest.json 的顺序拼接正文，并在拼接后**校验**：
      - 每个模块的正文行数等于清单里记的 lines
      - 正文首行去掉空白后，与原文件的对应行**逐字符相同**

用法：
    python tools/bundle_engine.py                 # 重建并校验，不写回
    python tools/bundle_engine.py --write         # 校验通过后写回 main.script.js
    python tools/bundle_engine.py --diff          # 不一致时显示首个差异位置

关于「怎么证明字节不变」：两种手段，用哪个都行 ——
    1. `git diff --stat -- src/main.script.js` 为空 —— 最直接，且不依赖额外文件；
    2. 本脚本的参照副本 build/reference/main.script.original.js（拆分前存的快照）。
参照副本是**可选的**：没有它脚本会跳过比对并给出警告。
它是一次性快照，不必长期保留；`git diff` 才是日常手段。
"""
import hashlib
import io
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)
SRC = ROOT / 'src'
ENGINE_DIR = SRC / 'engine'
MANIFEST = ENGINE_DIR / 'manifest.json'
TARGET = SRC / 'main.script.js'
REFERENCE = ROOT / 'build' / 'reference' / 'main.script.original.js'

WRITE = '--write' in sys.argv
SHOW_DIFF = '--diff' in sys.argv


def read_module(path, header_lines):
    """返回模块正文（去掉注释头）。"""
    text = io.open(path, encoding='utf-8', newline='').read()
    lines = text.split('\n')
    if text.endswith('\n'):
        lines = lines[:-1]
    body = lines[header_lines:]
    return body


def main():
    if not MANIFEST.exists():
        sys.exit('找不到 %s —— 先跑 python tools/extract_engine.py' % MANIFEST)
    man = json.loads(io.open(MANIFEST, encoding='utf-8').read())

    header_lines = man.get('headerLines', 3)
    trailing_nl = man.get('trailingNewline', True)

    print('清单: %s' % MANIFEST)
    print('模块: %d 个，合计 %d 行（原文件 %d 行）'
          % (len(man['modules']), sum(m['lines'] for m in man['modules']), man['sourceLines']))
    print()

    out_lines = []
    problems = []
    for m in man['modules']:
        name = m['name']
        path = ENGINE_DIR / (name + '.js')
        if not path.exists():
            problems.append('模块文件缺失: %s' % path.name)
            continue
        body = read_module(path, header_lines)
        if len(body) != m['lines']:
            problems.append('%s: 正文 %d 行，清单记 %d 行'
                            % (name, len(body), m['lines']))
        out_lines.extend(body)
        print('  %-14s %4d 行  (原 %d\u2013%d)' % (name, len(body), m['start'], m['end']))

    if problems:
        print('\n❌ 模块与清单不符：')
        for p in problems:
            print('   ' + p)
        return 1

    built = '\n'.join(out_lines) + ('\n' if trailing_nl else '')

    # ---- 与原文件比对 -------------------------------------------------------
    if REFERENCE.exists():
        ref = io.open(REFERENCE, encoding='utf-8', newline='').read()
        same = (built == ref)
        print()
        print('参照: %s' % REFERENCE)
        print('  原 sha256: %s' % hashlib.sha256(ref.encode('utf-8')).hexdigest())
        print('  新 sha256: %s' % hashlib.sha256(built.encode('utf-8')).hexdigest())
        print('  字节数   : %d  vs  %d' % (len(built.encode('utf-8')), len(ref.encode('utf-8'))))
        print('  逐字节相同: %s' % ('✅ 是' if same else '❌ 否'))
        if not same and SHOW_DIFF:
            a, b = ref, built
            for i in range(min(len(a), len(b))):
                if a[i] != b[i]:
                    print()
                    print('  首个差异在字符偏移 %d:' % i)
                    print('    原: %r' % a[max(0, i - 60):i + 60])
                    print('    新: %r' % b[max(0, i - 60):i + 60])
                    la = a[:i].count('\n') + 1
                    print('    （原文件第 %d 行）' % la)
                    break
            else:
                print('  仅长度不同：原 %d 字符，新 %d 字符' % (len(a), len(b)))
        if not same:
            print()
            print('❌ 重建结果与原文件不一致 —— 阶段 2 不允许写入。')
            print('   用 --diff 看首个差异位置。')
            return 1
    else:
        print()
        print('⚠️  找不到参照 %s' % REFERENCE)
        print('    （只有拿到拆分前的副本才能证明字节不变；本次跳过比对）')

    # ---- 写回 ---------------------------------------------------------------
    if WRITE:
        before = TARGET.read_text(encoding='utf-8') if TARGET.exists() else None
        if before == built:
            print('\nmain.script.js 内容已是重建结果，无需写入。')
        else:
            TARGET.write_text(built, encoding='utf-8', newline='')
            print('\n已写回 %s' % TARGET)
    else:
        print('\n（未写回；加 --write 才会覆盖 main.script.js）')

    print()
    print('✅ 重建校验通过')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
