"""Step 3 (continued): expand tutorial lesson 02.

User feedback: "5 稍微拓展一些" -- the lesson finished in a single press and only
showed one idea.

Now the lesson walks the full arc in two presses and shows three things at once:
  1. an under-cap tile absorbs and steps up level by level (2 -> 4 -> 8)
  2. payload must reach the tile's own value before it doubles
  3. a tile at the cap never absorbs -- a neutral right beside the capped 8
     survives, and must be recruited by hand instead

Board (move DOWN), board space is an 11x11 view centred on the core:

    (50,50) core 8     [5050]  provider + at the cap
    (51,50) player 2   [5150]  the absorber (under the cap)
    (52,50) player 8   [5250]  at the cap
    (51,51) neutral 2  [5151]  eaten on press 1  -> 2 becomes 4
    (53,51) neutral 4  [5351]  eaten on press 2  -> 4 becomes 8
    (54,51) neutral 2  [5451]  never in any core radius ring; ends up beside the
                               capped 8 (which lands on (54,50)) and survives
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
LES = ROOT / 'src' / 'tutorial.lessons.js'
applied = []


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        sys.exit('LESSON EXPAND FAILED: %s -- expected %d, found %d\n  anchor: %r'
                 % (label, n, c, old[:220]))
    applied.append(label)
    return text.replace(old, new)


les = LES.read_text(encoding='utf-8')

les = sub(les,
          "else if(level===1){add(5150,4,'p');add(5250,8,'p');add(5151,4);add(5351,2);}",
          "else if(level===1){add(5150,2,'p');add(5250,8,'p');add(5151,2);add(5351,4);add(5451,2);}",
          1, 'lesson02: two-step board + a cap-proof neutral that no radius can reach')

les = sub(les,
          "if(q.lesson===1)return q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=8);",
          "if(q.lesson===1)return q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=8)&&q.g.some(t=>t?.side==='n'&&t.n===2);",
          1, 'lesson02: win condition -> reached the cap AND the capped neighbour was spared')

les = sub(les,
          "{title:'自动收集',intro:'己方数字未满上限时会自己吸收相邻的中立数字；已经达到上限的方块不再吸收，只能靠推动或合并。'}",
          "{title:'自动收集',intro:'未满上限的方块会吸收中立并逐级升级，累积到当前数字就翻倍；达到上限的方块不再吸收。'}",
          1, 'lesson02: title + intro')

les = sub(les,
          "task=s.turn?'换成别的方向，看看谁还在吸收':'按 ↓，观察自动吸收';hint=s.turn?'只有未满上限的方块会吸收。已达上限的方块（数字 8）旁边的中立不会被自动吃掉，要收编它得手动推动或合并。':'下方那个己方 4 未满上限，会把范围内的中立 4 吸过来升到 8；核心已经是 8，达到上限，不参与吸收。';",
          "task=s.turn?'再按 ↓，把它喂到上限':'按 ↓，观察自动吸收';hint=s.turn?'累积量要够到当前数字才会翻倍。核心和右边那个 8 都已经达到上限，不会吸收——它们旁边的中立只能靠推动或合并来收编。':'下方那个己方 2 未满上限，会把范围内的中立吸过来。累积够 2 就升到 4，再够 4 就升到 8。';",
          1, 'lesson02: two-stage task/hint text')

les = sub(les,
          "s.lesson===1&&s.turn===1&&neutral===1?'观察成功：未满上限的 4 升到了 8，而满上限方块旁边的中立没有被自动吃掉。'",
          "s.lesson===1&&s.turn===1&&neutral===2?'观察成功：未满上限的 2 升到了 4；旁边那个已达上限的 8 没有吸收中立。'",
          1, 'lesson02: mid-lesson observation message')

LES.write_text(les, encoding='utf-8', newline='')

print('LESSON EXPANSION APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
