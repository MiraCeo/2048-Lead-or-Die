"""Assemble the single-file deliverable from src/.

Pipeline:
    src/main.script.js  --[13 patch rules]-->  tutorial script
    src/tutorial.shell.html + tutorial script  -->  tutorial document
    src/main.shell.html + main script + base64(guide) + base64(tutorial)
        -->  尔领死吧-v0.1.0.html

The tutorial script is GENERATED, never hand-edited. Each patch anchor must match
exactly once; otherwise the build aborts with a pointer to tools/derive_patches.py,
so an engine edit can never silently drift the tutorial.

Verification: the assembled file must be byte-identical to
build/reference/2048.original.html. Run this after every source edit.
"""
import base64
import hashlib
import importlib.util
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _root import PATHS

ROOT = PATHS.ROOT
SRC = PATHS.SRC
OUT_FILE = PATHS.DELIVERABLE
REFERENCE = PATHS.ORIGINAL
VERSION = PATHS.VERSION

GUIDE_PH = '__GUIDE_B64__'
TUT_PH = '__TUTORIAL_B64__'
SCRIPT_PH = '__MAIN_SCRIPT__'
TUT_SCRIPT_PH = '__TUTORIAL_SCRIPT__'
# 版本号占位符 —— 由 tools/_root.py 的 VERSION 注入（发版只改那一处）
VERSION_PH = '__VERSION__'


def load_patches():
    spec = importlib.util.spec_from_file_location('tutorial_patches', SRC / 'tutorial.patches.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PATCHES


def b64(text: str) -> str:
    return base64.b64encode(text.encode('utf-8')).decode('ascii')


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--accept', action='store_true',
                    help='record this build as the new accepted baseline')
    ap.add_argument('--release', action='store_true',
                    help='also archive a copy at releases/尔领死吧-v<版本>.html')
    args = ap.parse_args()

    main_shell = (SRC / 'main.shell.html').read_text(encoding='utf-8')
    main_script = (SRC / 'main.script.js').read_text(encoding='utf-8')
    guide = (SRC / 'guide.html').read_text(encoding='utf-8')
    tut_shell = (SRC / 'tutorial.shell.html').read_text(encoding='utf-8')
    patches = load_patches()

    # ---- 版本号注入 -------------------------------------------------------
    # 版本号的**唯一来源**是 tools/_root.py 的 VERSION。三个源文件里写的是
    # 占位符 __VERSION__，在这里统一替换。
    #
    # ⚠️ 必须在**base64 编码之前**替换：guide 会被编码进教程脚本、教程脚本又被
    #    编码进主脚本，编码之后再替换就找不到明文了。
    # ⚠️ 替换后若仍残留 __VERSION__，说明有源文件漏改了 —— 响亮失败，不静默产出。
    for label, text in (('guide.html', guide), ('main.shell.html', main_shell),
                        ('tutorial.shell.html', tut_shell)):
        if VERSION_PH in text:
            text = text.replace(VERSION_PH, VERSION)
        if label == 'guide.html':
            guide = text
        elif label == 'main.shell.html':
            main_shell = text
        else:
            tut_shell = text

    guide_b64 = b64(guide)

    # 1. tutorial script = main script + patch rules
    tut_script = main_script
    for p in patches:
        n = tut_script.count(p['old'])
        if n != 1:
            sys.exit('BUILD FAILED: patch %s matched %d times (expected 1).\n'
                     'The engine changed; repair that patch in %s\n'
                     '(or regenerate all of them: python tools/derive_patches.py)'
                     % (p['name'], n, SRC / 'tutorial.patches.py'))
        new = ((SRC / p['new_file']).read_text(encoding='utf-8')
               if 'new_file' in p else p['new'])
        tut_script = tut_script.replace(p['old'], new, 1)

    if TUT_PH in tut_script:
        sys.exit('BUILD FAILED: tutorial script still references %s' % TUT_PH)
    n = tut_script.count(GUIDE_PH)
    if n != 1:
        sys.exit('BUILD FAILED: tutorial script should reference %s once, found %d' % (GUIDE_PH, n))
    tut_script = tut_script.replace(GUIDE_PH, guide_b64, 1)

    # 2. tutorial document
    if tut_shell.count(TUT_SCRIPT_PH) != 1:
        sys.exit('BUILD FAILED: tutorial shell must contain %s once' % TUT_SCRIPT_PH)
    tut_html = tut_shell.replace(TUT_SCRIPT_PH, tut_script, 1)

    # 3. main script with both embedded documents
    for ph in (GUIDE_PH, TUT_PH):
        if main_script.count(ph) != 1:
            sys.exit('BUILD FAILED: main script must contain %s once, found %d'
                     % (ph, main_script.count(ph)))
    html_script = main_script.replace(GUIDE_PH, guide_b64, 1).replace(TUT_PH, b64(tut_html), 1)

    # 4. the deliverable
    if main_shell.count(SCRIPT_PH) != 1:
        sys.exit('BUILD FAILED: main shell must contain %s once' % SCRIPT_PH)
    out = main_shell.replace(SCRIPT_PH, html_script, 1)

    # 版本号占位符必须已被全部替换 —— 否则产物里会留下 __VERSION__ 这种字样，
    # 而它出现在玩家可见的页脚/眉标里，属"悄悄坏掉"。响亮失败。
    if VERSION_PH in out:
        n = out.count(VERSION_PH)
        sys.exit('BUILD FAILED: 产物里仍残留 %d 处 %s。\n'
                 '有源文件漏用了版本占位符（应为 v%s）。'
                 % (n, VERSION_PH, VERSION))

    OUT_FILE.write_text(out, encoding='utf-8', newline='')

    produced = OUT_FILE.read_bytes()
    print('version          : v%s' % VERSION)
    print('patches applied  : %d' % len(patches))
    print('guide b64        : %d chars' % len(guide_b64))
    print('tutorial script  : %d chars' % len(tut_script))
    print('tutorial document: %d chars  -> b64 %d' % (len(tut_html), len(b64(tut_html))))
    print('deliverable      : %s' % OUT_FILE)
    print('                   %d chars, %d bytes' % (len(out), len(produced)))
    print('sha256           : %s' % hashlib.sha256(produced).hexdigest())

    # ---- 发布副本 ---------------------------------------------------------
    # 发布纪律（用户要求）：稳定文件名 `尔领死吧.html` 永远是最新构建，玩家/网页端
    # 只刷新它；同时按版本号留一份副本，用于回溯"这版改了什么"。
    #
    # 只在 --release 时才写副本：日常开发每改一行都建一个副本会把 releases/ 淹掉。
    if args.release:
        rel = PATHS.release_file()
        rel.parent.mkdir(parents=True, exist_ok=True)
        rel.write_bytes(produced)
        print('release          : %s  (%d bytes)' % (rel, len(produced)))
    else:
        print('release          : （未写副本；发版请加 --release）')

    # Build 0 acceptance was "byte-identical to the original shipped file".
    # After deliberate changes the deliverable legitimately differs, so we verify
    # against a moving baseline: --accept records the current build as accepted.
    baseline = PATHS.BASELINE / '2048.html'
    if args.accept:
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_bytes(produced)
        print('baseline         : ACCEPTED (%d bytes) -> %s' % (len(produced), baseline))
        return

    if baseline.exists():
        ref = baseline.read_bytes()
        same = produced == ref
        print('baseline         : %s  (%d bytes)' % (baseline.name, len(ref)))
        print('UNCHANGED        : %s' % ('YES' if same else 'NO'))
        if not same:
            print('                   %+d bytes vs baseline' % (len(produced) - len(ref)))
            print('                   (expected if you edited src/; use --accept to adopt)')
    elif REFERENCE.exists():
        ref = REFERENCE.read_bytes()
        same = produced == ref
        print('reference        : %s  (%d bytes)' % (REFERENCE.name, len(ref)))
        print('BYTE-IDENTICAL   : %s' % ('YES' if same else 'NO'))
        if not same:
            print()
            print('  first difference:')
            n = min(len(produced), len(ref))
            for i in range(n):
                if produced[i] != ref[i]:
                    print('    byte %d' % i)
                    print('    got: %r' % produced[max(0, i - 40):i + 40])
                    print('    ref: %r' % ref[max(0, i - 40):i + 40])
                    break
            else:
                print('    files differ in length only: got %d, ref %d' % (len(produced), len(ref)))
            sys.exit(1)
    else:
        print('baseline         : NOT PRESENT -- no verification target')


if __name__ == '__main__':
    main()
