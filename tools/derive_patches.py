"""Derive the patch rules that turn src/main.script.js into the tutorial's script.

The tutorial carries its own forked copy of the engine. Rather than maintaining
two copies, we express the fork as an explicit ordered list of literal block
replacements and GENERATE the tutorial script at build time.

This tool:
  1. normalises the reference tutorial script (its embedded guide blob -> placeholder)
  2. diffs it against src/main.script.js line by line
  3. emits src/tutorial.patches.py (+ src/tutorial.lessons.js for the big block)
  4. immediately applies those patches and asserts the result equals the reference

Block boundaries are taken as CHARACTER OFFSETS of whole lines (trailing newline
included), because joining lines with '\\n' cannot express a pure insertion or a
pure deletion exactly. Pure insertions/deletions borrow one following line as
context so the anchor is never empty.

The largest hunk is the tutorial's lesson scaffolding (lessons table, tutorialInitial,
tutorialDone, tutorialUI, tutorialHighlights, ...). It is written out to
src/tutorial.lessons.js and referenced via "new_file", so that lesson work happens
in a .js file instead of inside a Python string literal.

If step 4 fails, the derived patch set is incomplete -- fix and rerun.
"""
import difflib
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
MAIN = ROOT / 'src' / 'main.script.js'
REF = ROOT / 'build' / 'reference' / 'tutorial.script.js'
OUT = ROOT / 'src' / 'tutorial.patches.py'
LESSONS = ROOT / 'src' / 'tutorial.lessons.js'

BLOB_RE = re.compile(r"atob\('([A-Za-z0-9+/=]+)'\)")
FUNC_RE = re.compile(r'function\s+([A-Za-z_$][\w$]*)\s*\(')


def offsets(text: str):
    """offsets[k] = char index where line k starts; has len(lines)+1 entries."""
    offs = [0]
    for i, ch in enumerate(text):
        if ch == '\n':
            offs.append(i + 1)
    if offs[-1] != len(text):
        offs.append(len(text))
    return offs


def hint(block: str) -> str:
    names = FUNC_RE.findall(block)
    if names:
        return names[0]
    s = re.sub(r'\s+', ' ', block.strip())[:40]
    return s or '(empty)'


def main():
    main_src = MAIN.read_text(encoding='utf-8')
    ref_raw = REF.read_text(encoding='utf-8')
    ref_norm = BLOB_RE.sub("atob('__GUIDE_B64__')", ref_raw)
    print('tutorial reference: %d embedded blob(s) -> __GUIDE_B64__'
          % len(BLOB_RE.findall(ref_raw)))

    a = main_src.split('\n')
    b = ref_norm.split('\n')
    oa, ob = offsets(main_src), offsets(ref_norm)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)

    patches = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        ai1, ai2, bj1, bj2 = i1, i2, j1, j2
        pure_insert = (ai1 == ai2)
        pure_delete = (bj1 == bj2)
        if (pure_insert or pure_delete) and ai2 < len(a) - 1:
            ai2 += 1
            bj2 += 1
        elif (pure_insert or pure_delete) and ai1 > 0:
            ai1 -= 1
            bj1 -= 1
        old = main_src[oa[ai1]:oa[ai2]]
        new = ref_norm[ob[bj1]:ob[bj2]]
        patches.append({
            'name': '%s@main[%d:%d]' % (hint(new or old), i1 + 1, i2),
            'old': old,
            'new': new,
        })
        if not old:
            print('  [warn] empty anchor for hunk %s' % tag)

    # ---- verify BEFORE extracting the lessons block ----------------------
    text = main_src
    for p in patches:
        n = text.count(p['old'])
        if n != 1:
            print('  [FAIL] %s matched %d times' % (p['name'], n))
            sys.exit(1)
        text = text.replace(p['old'], p['new'], 1)
    if text != ref_norm:
        print('VERIFY: MISMATCH -- patch set incomplete')
        for i, (x, y) in enumerate(zip(text.split('\n'), ref_norm.split('\n'))):
            if x != y:
                print('  first differing line %d:' % (i + 1))
                print('    got     : %s' % x[:150])
                print('    expected: %s' % y[:150])
                break
        sys.exit(1)
    print('VERIFY: patch set reproduces the tutorial script exactly')

    # ---- extract the lesson scaffolding into its own source file ---------
    lessons_patches = [p for p in patches if 'const lessons=[' in p['new']]
    for p in lessons_patches:
        LESSONS.write_text(p['new'], encoding='utf-8', newline='')
        p['new_file'] = LESSONS.name
        p['_content'] = p.pop('new')

    # ---- emit -------------------------------------------------------------
    chunks = []
    for p in patches:
        if 'new_file' in p:
            chunks.append('    {\n        "name": %r,\n        "old": %r,\n'
                          '        "new_file": %r,\n    },\n'
                          % (p['name'], p['old'], p['new_file']))
        else:
            chunks.append('    {\n        "name": %r,\n        "old": %r,\n'
                          '        "new": %r,\n    },\n' % (p['name'], p['old'], p['new']))

    OUT.write_text(
        '"""GENERATED by tools/derive_patches.py -- do not edit by hand.\n\n'
        'Ordered literal block replacements applied to src/main.script.js to produce\n'
        "the tutorial's embedded script. Each anchor must match exactly once; the build\n"
        'fails loudly otherwise, so engine edits cannot silently drift the tutorial.\n\n'
        'Block boundaries are whole lines INCLUDING the trailing newline.\n'
        'A patch carrying "new_file" takes its replacement from that file under src/,\n'
        'so lesson scaffolding is edited as .js rather than as a Python literal.\n\n'
        'Regenerate with:  python tools/derive_patches.py\n'
        '"""\n\n'
        'PATCHES = [\n' + ''.join(chunks) + ']\n',
        encoding='utf-8', newline='')

    print('patches derived : %d  ->  %s' % (len(patches), OUT))
    if lessons_patches:
        print('lessons block   : %d chars  ->  %s' % (len(lessons_patches[0]['_content']), LESSONS))
    print()
    for p in patches:
        if 'new_file' in p:
            print('  %-30s old %6d ch -> new_file %s' % (p['name'], len(p['old']), p['new_file']))
        else:
            print('  %-30s old %6d ch -> new %6d ch' % (p['name'], len(p['old']), len(p['new'])))


if __name__ == '__main__':
    main()
