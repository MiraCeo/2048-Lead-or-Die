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
    python tools/bundle_engine.py                 # 重建并与参照副本比对，不写回
    python tools/bundle_engine.py --write         # 校验通过后写回 main.script.js
    python tools/bundle_engine.py --diff          # 不一致时显示首个差异位置
    python tools/bundle_engine.py --write --allow-diverge
                                                  # 有意改动引擎时用（见下）

## 关于「字节不变」这个保证

阶段 2 是**纯搬移**，所以当时要求重建结果与拆分前逐字节相同 —— 那是阶段 2 的验收标准。
但阶段 3 起会**有意**修改引擎（改存档 KEY、品牌名），差异是预期的，不是错误。

所以本脚本分两种情况：
    默认      与参照副本 build/reference/main.script.original.js 比对；
              不一致就拒绝写入，并提示加 --allow-diverge。
    --allow-diverge
              跳过参照比对（或只做提示），允许写入。

**参照副本是拆分前的一次性快照，永远代表"阶段 2 那个点"。**
日常判断"我这次改动是否符合预期"，用 git 更直接：

    git diff --stat -- src/main.script.js

若只想确认"没有意外改动"，比对 git 里上一个提交的版本即可，不必依赖本副本。
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
ALLOW_DIVERGE = '--allow-diverge' in sys.argv


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
    print('模块: %d 个' % len(man['modules']))
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
        out_lines.extend(body)
        # 溯源区间是**阶段 2 压缩文本**的行号，只作归因展示，不参与校验
        # （清单里刻意不记行数，见 extract_engine.py 的说明）。
        a, b = m.get('origStart'), m.get('origEnd')
        tag = ('溯源 %d\u2013%d' % (a, b)) if a is not None else '（无溯源信息）'
        print('  %-14s %4d 行  (%s)' % (name, len(body), tag))

    if problems:
        print('\n❌ 模块与清单不符：')
        for p in problems:
            print('   ' + p)
        return 1

    built = '\n'.join(out_lines) + ('\n' if trailing_nl else '')

    # ---- 与参照副本比对 -----------------------------------------------------
    if REFERENCE.exists():
        ref = io.open(REFERENCE, encoding='utf-8', newline='').read()
        same = (built == ref)
        print()
        print('参照: %s' % REFERENCE)
        print('  原 sha256: %s' % hashlib.sha256(ref.encode('utf-8')).hexdigest())
        print('  新 sha256: %s' % hashlib.sha256(built.encode('utf-8')).hexdigest())
        print('  字节数   : %d  vs  %d' % (len(built.encode('utf-8')), len(ref.encode('utf-8'))))
        if same:
            print('  与参照相同: ✅ 是')
        else:
            print('  与参照相同: ❌ 否（%+d 字节）'
                  % (len(built.encode('utf-8')) - len(ref.encode('utf-8'))))
            if not ALLOW_DIVERGE:
                print()
                print('重建结果与参照副本不同。')
                print('  · 若是**有意**改引擎（改 KEY / 品牌 / 逻辑），加 --allow-diverge 写入；')
                print('  · 若是无意改动，用 --diff 定位首个差异。')
                return 1
            print('  （已给 --allow-diverge，视为有意改动）')
        if not same and SHOW_DIFF:
            a, b = ref, built
            for i in range(min(len(a), len(b))):
                if a[i] != b[i]:
                    print()
                    print('  首个差异在字符偏移 %d:' % i)
                    print('    原: %r' % a[max(0, i - 60):i + 60])
                    print('    新: %r' % b[max(0, i - 60):i + 60])
                    print('    （原文件第 %d 行）' % (a[:i].count('\n') + 1))
                    break
            else:
                print('  仅长度不同：原 %d 字符，新 %d 字符' % (len(a), len(b)))
    else:
        print()
        print('⚠️  找不到参照 %s（跳过比对，不影响写入）' % REFERENCE)

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
