"""用无头 Chrome 检查渲染后的实际状态（DOM 值 / 布局尺寸）。

为什么需要这个工具：
  1. 此前"沙箱内 headless Chrome 起不来"（mojo platform_channel 需命名管道），
     所以项目一直靠"用户截图 → 读图"来验证画面。放宽文件策略后它**能跑了**，
     这意味着布局问题可以**机器自测**，不必每次都问用户要截图。
  2. PowerShell 的 `>` 重定向会写成 UTF-16 带 BOM，解码即失败 —— 必须用
     subprocess 取原始字节（同一个坑在 extract_release.py 里也记了一次）。

用法：
    python tools/shot.py                     # 截图到 build/shot.png（1600x900）
    python tools/shot.py --size 1280x800
    python tools/shot.py --dom               # 打印状态槽/反馈的实际 DOM
    python tools/shot.py --metrics           # 打印关键元素的布局尺寸
"""
import os
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
sys.path.insert(0, str(HERE))
from _root import PATHS

CHROME_CANDIDATES = [
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
]


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == '--' + name and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def size_arg(default='1600x900'):
    """Chrome 的 --window-size 要求 `宽,高`（**逗号**分隔）。

    第一版直接传了 `1366x768`（x 分隔），Chrome 静默忽略、始终用默认 1600x900，
    于是"多分辨率验证"实际测了三次同一个尺寸 —— 假通过。必须 normalize。
    """
    return arg('size', default).replace('x', ',')


def run(chrome, url, extra, prof):
    base = [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
            '--hide-scrollbars', '--user-data-dir=' + str(prof)]
    r = subprocess.run(base + extra + [url], capture_output=True)
    return r.stdout.decode('utf-8', 'replace')


# 交付物在命令行里用中文名会被 PowerShell/Chrome 拆成多个"目标"，所以复制成 ASCII 名
SRC = PATHS.BUILD / '_shot_src.html'
SRC.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(PATHS.DELIVERABLE, SRC)
URL = 'file:///' + str(SRC).replace('\\', '/')

chrome = find_chrome()
if not chrome:
    sys.exit('找不到 Chrome / Edge')
PROF = PATHS.BUILD / 'chromeprof'

# 默认每次用**干净** profile（跑完也清掉）：
#   ① 复用 profile 会让 localStorage 留着上一局的存档 —— 截图内容随运行历史变化，
#      "全新开局"和"恢复存档"混在一起，不便对比；
#   ② 一个 profile 实测能涨到 11MB（Cache/ShaderCache 等）。
# 需要保留登录态/存档时加 --keep-profile。
KEEP = '--keep-profile' in sys.argv
if not KEEP and PROF.exists():
    shutil.rmtree(PROF, ignore_errors=True)


def cleanup():
    if not KEEP:
        shutil.rmtree(PROF, ignore_errors=True)
        for p in (SRC, PATHS.BUILD / '_probe.html'):
            try:
                p.unlink()
            except OSError:
                pass

if '--dom' in sys.argv:
    dom = run(chrome, URL, ['--dump-dom'], PROF)
    print('DOM 长度: %d 字符' % len(dom))
    for key in ('status-slot', 'id="inspect"', 'id="feedback"'):
        i = dom.find(key)
        print()
        print('=== %s ===' % key)
        print(repr(dom[max(0, i - 60):i + 320]) if i >= 0 else '(未找到)')
elif '--metrics' in sys.argv:
    # 用 --dump-dom 拿不到布局，改用内联脚本把尺寸写进 title，再 dump 出来
    probe = PATHS.BUILD / '_probe.html'
    html = Path(SRC).read_text(encoding='utf-8')
    js = '''
<script>
window.addEventListener('load', () => {
  const out = [];
  const push = (label, el) => {
    if (!el) { out.push(label + ': (missing)'); return; }
    const r = el.getBoundingClientRect();
    out.push(label + ': x=' + Math.round(r.x) + ' y=' + Math.round(r.y) +
             ' w=' + Math.round(r.width) + ' h=' + Math.round(r.height));
  };
  push('viewport', { getBoundingClientRect: () => ({ x: 0, y: 0, width: innerWidth, height: innerHeight }) });
  push('doc.scrollHeight', { getBoundingClientRect: () => ({ x: 0, y: 0, width: 0, height: document.documentElement.scrollHeight }) });
  push('.shell', document.querySelector('.shell'));
  push('.layout', document.querySelector('.layout'));
  push('.play-area', document.querySelector('.play-area'));
  push('canvas#canvas', document.getElementById('canvas'));
  push('.board', document.querySelector('.board'));
  push('.board-actions', document.querySelector('.board-actions'));
  push('.navbtns', document.querySelector('.navbtns'));
  push('.topbar', document.querySelector('.topbar'));
  push('.status-slot', document.querySelector('.status-slot'));
  push('#inspect', document.getElementById('inspect'));
  push('#feedback', document.getElementById('feedback'));
  push('aside.left', document.querySelector('.layout > aside'));
  push('aside.right', document.querySelector('.right'));
  push('footer', document.querySelector('footer'));
  // 侧栏是否内部溢出（scrollHeight > clientHeight）—— v0.1.5 之前两栏都溢出，
  // "全部同屏"其实是假的。这条必须能机器验。
  const ov = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return sel + ':ov=-1';
    return sel + ':ov=' + (el.scrollHeight - el.clientHeight);
  };
  out.push(ov('.layout > aside'));
  out.push(ov('.layout > .right'));
  document.title = 'METRICS\\n' + out.join('\\n');
});
</script>
'''
    probe.write_text(html.replace('</body>', js + '</body>'), encoding='utf-8')
    dom = subprocess.run(
        [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
         '--hide-scrollbars', '--window-size=' + size_arg(),
         '--virtual-time-budget=1500', '--user-data-dir=' + str(PROF),
         '--dump-dom', 'file:///' + str(probe).replace('\\', '/')],
        capture_output=True).stdout.decode('utf-8', 'replace')
    m = re.search(r'<title>(.*?)</title>', dom, re.S)
    print(m.group(1).replace('\\n', '\n') if m else '(标题里没有 METRICS)')
    cleanup()
else:
    out = PATHS.BUILD / 'shot.png'
    if out.exists():
        out.unlink()
    run(chrome, URL, ['--window-size=' + size_arg(),
                      '--screenshot=' + str(out)], PROF)
    print('截图: %s  (%s bytes)' % (out, out.stat().st_size if out.exists() else '失败'))
    cleanup()
