"""初始吸收阈值 8 -> 4。

连带影响（按你之前定的规则推导，不是我自己加的）：
  - "每级翻倍" + "暂时先 32" => 阈值线变成三级：4 -> 8 -> 16 -> 32（保持上限 32 不变）
  - 敌方天花板按"默认等于基础值 => 4"，所以采集机自动可达上限变成 8（原来是 16）
  - 玩家核心起始是 8，现在**高于阈值 4**，所以核心不再自己吸收、不再自己长大
    —— 这正好解掉了我在 §12.4 标的"后果一"
  - 副作用：可吸收的只有 2 和 4 两档，且进度继承只在 2 -> 4 这一步发生
    （4 升到 8 就超过阈值，进度清零）

教程按你的要求不动。
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
SRC = ROOT / 'src'
applied = []


def fail(msg):
    print('\n中止：%s' % msg)
    print('内存中已应用：%s' % (', '.join(applied) or '无'))
    print('注意：尚未写入任何文件。')
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s：预期 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:200]))
    applied.append(label)
    return text.replace(old, new)


js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')

js = sub(js, 'const ABSORB_CAP=8,', 'const ABSORB_CAP=4,',
         1, '基础吸收阈值 8 -> 4')

js = sub(js, 'TECH_RADIUS_MAX=2,TECH_THRESHOLD_MAX=2;',
         'TECH_RADIUS_MAX=2,TECH_THRESHOLD_MAX=3;',
         1, '阈值线改为三级（4/8/16/32，保持上限 32）')

js = sub(js, 'AI_ABSORB_CEILING=8;', 'AI_ABSORB_CEILING=4;',
         1, '敌方天花板默认跟随基础值 -> 4')

js_path.write_text(js, encoding='utf-8', newline='')
print('引擎已改写：%d 字符' % len(js))

# 玩家手册里的阈值数字（教程不动，手册要准）
g_path = SRC / 'guide.html'
guide = g_path.read_text(encoding='utf-8')
guide = sub(guide, '（基础 8）', '（基础 4）', 1, '玩家手册：阈值数字 8 -> 4')
g_path.write_text(guide, encoding='utf-8', newline='')
print('玩家手册已更新')

print()
print('本次应用 %d 项：' % len(applied))
for a in applied:
    print('  - %s' % a)
