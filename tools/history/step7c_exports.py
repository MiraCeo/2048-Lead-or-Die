"""展示层的验证。

canvas 画出来的东西在无头环境里看不到，所以这里分两层验：
  1. 运行层：draw() 与 tileBody() 在新代码路径上不抛错
  2. 源码层：关键公式在场、旧血条代码已消失（防止它被悄悄改回来）
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
be = ROOT / 'tools' / 'build_engine.py'
txt = be.read_text(encoding='utf-8')
if "'tileBody'" not in txt:
    txt = txt.replace("'regenTiles', 'markCombat',",
                      "'regenTiles', 'markCombat', 'tileBody', 'draw',", 1)
    if "'tileBody'" not in txt:
        sys.exit('导出清单锚点未命中')
    be.write_text(txt, encoding='utf-8', newline='')
    print('无头工具导出清单已加入 tileBody 与 draw')
else:
    print('导出清单已包含 tileBody')
