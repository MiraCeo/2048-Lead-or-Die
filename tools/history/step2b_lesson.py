"""Step 2 (fix): redesign lesson 02's board.

Diagnosis from tools/test_step2_tutorial.js:
  The board put the under-cap absorber adjacent to the core, so it sat inside the
  core's radius ring. The core (at the cap, so not a receiver itself) therefore
  routed the "proof" neutral 2 to that absorber via the RADIUS path -- the neutral
  was consumed anyway and the lesson could not demonstrate the cap rule.

Redesign: stack the group vertically in column 50 and move DOWN, so the neutrals
sit perpendicular to the move.

    (50,50) core 8   [5050]   at the cap
    (51,50) 4        [5150]   under the cap -> the absorber
    (52,50) 8        [5250]   at the cap
    (51,51) neutral 4 [5151]  beside the under-cap tile
    (53,51) neutral 2 [5351]  beside where the capped 8 lands -> must survive

After one DOWN press: core (51,50), 4 -> (52,50), capped 8 -> (53,50).
The core's ring is rows 50-52, cols 49-51, so it covers the neutral 4 (absorbed,
fed to the under-cap tile -> upgrades to 8) but NOT the neutral 2 at (53,51),
which ends up beside the capped 8 and is left alone. That is the cap rule, visible.
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
        sys.exit('LESSON FIX FAILED: %s -- expected %d, found %d\n  anchor: %r'
                 % (label, n, c, old[:200]))
    applied.append(label)
    return text.replace(old, new)


les = LES.read_text(encoding='utf-8')

les = sub(les, "else if(level===1){add(5051,4,'p');add(4951,2);add(5053,4);}",
          "else if(level===1){add(5150,4,'p');add(5250,8,'p');add(5151,4);add(5351,2);}",
          1, 'lesson02: vertical board, move down')

les = sub(les,
          "if(q.lesson===1)return q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=8)&&q.g.some(t=>t?.side==='n'&&t.n===2);",
          "if(q.lesson===1)return q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=8);",
          1, 'lesson02: win condition -> an under-cap friendly tile reached 8')

les = sub(les,
          "task=s.turn?'看看满上限的方块会不会吸收':'按 →，观察自动吸收';hint=s.turn?'核心已经是 8，达到上限，它上方的中立 2 不会自动被吃掉——要收编它必须手动推动或合并。':'右下方那个己方 4 会吸收相邻的中立 4 并升到 8；核心 8 已达上限，不参与吸收。';",
          "task=s.turn?'换成别的方向，看看谁还在吸收':'按 ↓，观察自动吸收';hint=s.turn?'只有未满上限的方块会吸收。已达上限的方块（数字 8）旁边的中立不会被自动吃掉，要收编它得手动推动或合并。':'下方那个己方 4 未满上限，会把范围内的中立 4 吸过来升到 8；核心已经是 8，达到上限，不参与吸收。';",
          1, 'lesson02: task/hint text for the down move')

les = sub(les, "s.lesson===1&&s.turn===1&&neutral===1?'观察成功：4 已升到 8，而满上限的核心没有吸收旁边的中立。'",
          "s.lesson===1&&s.turn===1&&neutral===1?'观察成功：未满上限的 4 升到了 8，而满上限方块旁边的中立没有被自动吃掉。'",
          1, 'lesson02: observation message')

LES.write_text(les, encoding='utf-8', newline='')

print('LESSON FIX APPLIED (%d):' % len(applied))
for a in applied:
    print('  - %s' % a)
