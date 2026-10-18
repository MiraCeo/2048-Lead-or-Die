"""Extract the shipped single-file HTML into authoring sources under src/.

Everything is derived from the ONE shipped file, so the extraction is verifiable:
tools/build.py must rebuild that file byte-for-byte from src/.

Produces:
    build/reference/2048.original.html   pristine copy, the build's verification target
    src/main.shell.html                  shell with __MAIN_SCRIPT__ / __GUIDE_B64__ / __TUTORIAL_B64__
    src/main.script.js                   main game script (base64 blobs -> placeholders)
    src/guide.html                       decoded guide document
    src/tutorial.shell.html              tutorial document with __TUTORIAL_SCRIPT__
    build/reference/tutorial.script.js   current tutorial script, kept ONLY to prove that the
                                         patch rules in src/tutorial.patches.py reproduce it

The tutorial script is NOT a source: it is generated from src/main.script.js by the patch rules.
"""
import base64
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _root import PATHS

ROOT = PATHS.ROOT
SHIPPED = PATHS.DELIVERABLE
SRC = PATHS.SRC
REF = PATHS.REFERENCE

GUIDE_PH = '__GUIDE_B64__'
TUT_PH = '__TUTORIAL_B64__'
SCRIPT_PH = '__MAIN_SCRIPT__'
TUT_SCRIPT_PH = '__TUTORIAL_SCRIPT__'

SCRIPT_RE = re.compile(r'(<script[^>]*>)(.*?)(</script>)', re.S)
BLOB_RE = re.compile(r"atob\('([A-Za-z0-9+/=]+)'\)")


def main():
    html = SHIPPED.read_text(encoding='utf-8')
    SRC.mkdir(parents=True, exist_ok=True)
    REF.mkdir(parents=True, exist_ok=True)

    # pristine reference for byte-for-byte build verification
    shutil.copyfile(SHIPPED, REF / '2048.original.html')

    # ---- main script ------------------------------------------------------
    m = SCRIPT_RE.search(html)
    if not m:
        sys.exit('no <script> block in shipped html')
    main_script = m.group(2)

    blobs = BLOB_RE.findall(main_script)
    if len(blobs) != 2:
        sys.exit('expected 2 atob blobs in main script, found %d' % len(blobs))

    guide_html = base64.b64decode(blobs[0]).decode('utf-8')
    tutorial_html = base64.b64decode(blobs[1]).decode('utf-8')

    main_script_src = main_script.replace(blobs[0], GUIDE_PH, 1).replace(blobs[1], TUT_PH, 1)

    # ---- main shell -------------------------------------------------------
    main_shell = html[:m.start(2)] + SCRIPT_PH + html[m.end(2):]
    # the placeholders must land inside the atob() calls, so keep them there
    # (main_shell carries the whole script slot; blob placeholders live in main.script.js)

    # ---- tutorial document ------------------------------------------------
    tm = SCRIPT_RE.search(tutorial_html)
    if not tm:
        sys.exit('no <script> block in tutorial document')
    tutorial_script = tm.group(2)
    tutorial_shell = tutorial_html[:tm.start(2)] + TUT_SCRIPT_PH + tutorial_html[tm.end(2):]

    # ---- write ------------------------------------------------------------
    (SRC / 'main.shell.html').write_text(main_shell, encoding='utf-8', newline='')
    (SRC / 'main.script.js').write_text(main_script_src, encoding='utf-8', newline='')
    (SRC / 'guide.html').write_text(guide_html, encoding='utf-8', newline='')
    (SRC / 'tutorial.shell.html').write_text(tutorial_shell, encoding='utf-8', newline='')
    (REF / 'tutorial.script.js').write_text(tutorial_script, encoding='utf-8', newline='')

    print('shipped html      : %d chars' % len(html))
    print('reference copy    : %s' % (REF / '2048.original.html'))
    print()
    print('src/main.shell.html      %7d chars  (script slot -> %s)' % (len(main_shell), SCRIPT_PH))
    print('src/main.script.js       %7d chars  (blobs -> %s / %s)' % (len(main_script_src), GUIDE_PH, TUT_PH))
    print('src/guide.html           %7d chars' % len(guide_html))
    print('src/tutorial.shell.html  %7d chars  (script slot -> %s)' % (len(tutorial_shell), TUT_SCRIPT_PH))
    print('reference/tutorial.script.js %5d chars  (patch-completeness target)' % len(tutorial_script))
    print()
    print('-- sanity: placeholders present --')
    for name, text, ph in [
        ('main.shell.html', main_shell, SCRIPT_PH),
        ('main.script.js', main_script_src, GUIDE_PH),
        ('main.script.js', main_script_src, TUT_PH),
        ('tutorial.shell.html', tutorial_shell, TUT_SCRIPT_PH),
    ]:
        print('   %-22s contains %-20s %s' % (name, ph, text.count(ph)))
    print()
    print('-- sanity: rebuilt main html should equal original (script slot restored) --')
    rebuilt = main_shell.replace(SCRIPT_PH, main_script)
    print('   byte-identical to shipped: %s' % (rebuilt == html))


if __name__ == '__main__':
    main()
