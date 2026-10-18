"""校验交付物里内嵌的两份文档（介绍页 / 教程）的品牌名是否已全部更新。

注意：这两份文档是 **base64 内嵌**的，在交付物 HTML 里**明文搜不到** ——
直接对 HTML 搜 "LEAD OR DIE" 会得到 False，那是方法错误，不是改动没生效。
"""
import base64
import io
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _root import PATHS

html = io.open(PATHS.DELIVERABLE, encoding='utf-8').read()
print('交付物: %s  (v%s)' % (PATHS.DELIVERABLE.name, PATHS.VERSION))
blobs = re.findall(r"atob\('([A-Za-z0-9+/=]+)'\)", html)
print('内嵌 blob 数: %d（应为 2：介绍页 + 教程）' % len(blobs))

guide = base64.b64decode(blobs[0]).decode('utf-8')
tut = base64.b64decode(blobs[1]).decode('utf-8')

def first(pat, text):
    m = re.search(pat, text)
    return m.group(1) if m else '(未找到)'

print()
print('介绍页 title  : %s' % first(r'<title>(.*?)</title>', guide))
print('介绍页 h1     : %s' % first(r'<h1>(.*?)</h1>', guide))
i = guide.rfind('<footer')
print('介绍页 footer : %s' % guide[i:i + 60].replace('\n', ' '))
print('介绍页残留旧品牌名: %d' % (guide.count('核心群岛') + guide.count('CORE ARCHIPELAGO')))

print()
print('教程 title    : %s' % first(r'<title>(.*?)</title>', tut))
print('教程残留旧品牌名  : %d' % (tut.count('核心群岛') + tut.count('CORE ARCHIPELAGO')))

# ---- 版本号一致性 ---------------------------------------------------------
# 版本号的唯一来源是 tools/_root.py 的 VERSION，由 build.py 注入三处：
# 主外壳页脚、教程外壳页脚、介绍页眉标。
# 这个工具本来就要**解码**内嵌文档，所以顺便校验注入是否处处生效 ——
# 否则漏注入会表现为"页脚还写着旧版本"，而那种错误在无头测试里看不出来。
print()
print('=== 版本号注入校验（期望 v%s） ===' % PATHS.VERSION)
ver = PATHS.VERSION
checks = [
    ('主外壳页脚', 'v%s · 自动保存' % ver in html),
    ('教程页脚', 'v%s · 自动保存' % ver in tut),
    ('介绍页眉标', 'V%s' % ver in guide),
]
for label, ok in checks:
    print('  %-12s %s' % (label, '✅' if ok else '❌ 未注入 v%s' % ver))
# 占位符绝不能漏到产物里
leftover = html.count('__VERSION__') + tut.count('__VERSION__') + guide.count('__VERSION__')
print('  %-12s %s' % ('占位符残留', '✅ 0 处' if not leftover else '❌ %d 处' % leftover))

print()
bad = 0
if guide.count('CORE ARCHIPELAGO') or guide.count('核心群岛'):
    bad += 1
if tut.count('CORE ARCHIPELAGO') or tut.count('核心群岛'):
    bad += 1
if not all(ok for _, ok in checks) or leftover:
    bad += 1
print('结论: %s' % ('✅ 品牌名与版本号均正确' if not bad else '❌ 有问题，见上'))
sys.exit(1 if bad else 0)
