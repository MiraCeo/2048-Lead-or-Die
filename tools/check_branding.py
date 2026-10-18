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
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)

html = io.open(ROOT / '尔领死吧-v0.1.0.html', encoding='utf-8').read()
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

print()
bad = 0
if guide.count('CORE ARCHIPELAGO') or guide.count('核心群岛'):
    bad += 1
if tut.count('CORE ARCHIPELAGO') or tut.count('核心群岛'):
    bad += 1
print('结论: %s' % ('✅ 两份内嵌文档品牌名均已更新' if not bad else '❌ 仍有残留'))
sys.exit(1 if bad else 0)
