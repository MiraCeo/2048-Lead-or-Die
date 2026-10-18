"""收尾：把两处过时的测试期望同步到新规则。

1. test_step2.js 缺 CAP 辅助函数（D 组新写的断言用到了它）
2. test_step2_tutorial.js 第 02 关的弧线期望仍是旧规则：
   新规则下第一次下移会一次吸到两个中立（2 和 4），所以 2 直接跳到 8，
   第二次下移 8 -> 16（越过阈值、进度清零）。
   旧的"满上限 8 旁边的中立存活"断言已不成立，换成"越过阈值后进度清零"。
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TOOLS = Path(r'D:\2048') / 'tools'


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        sys.exit('%s：预期 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:200]))
    print('已改：%s' % label)
    return text.replace(old, new)


# ---------------------------------------------------------------- 1
p = TOOLS / 'test_step2.js'
t = p.read_text(encoding='utf-8')
t = sub(t, 'const P = (r, c) => r * 100 + c;',
        'const P = (r, c) => r * 100 + c;\nconst CAP = (n) => 3 ** G.lvl(n) * G.lvl(8);',
        1, 'test_step2.js 补上 CAP 辅助函数')
p.write_text(t, encoding='utf-8', newline='')

# ---------------------------------------------------------------- 2
p2 = TOOLS / 'test_step2_tutorial.js'
t2 = p2.read_text(encoding='utf-8')

OLD = """// --- lesson 02 walks 2 -> 4 -> 8 over two presses ---------------------------
console.log('\\n=== lesson 02 is a two-press arc and demonstrates the cap rule ===');
{
  const DIRS = ['down', 'left', 'right', 'up'];
  const q = T.tutorialInitial(1);
  const press = () => {
    for (const d of DIRS) {
      const draft = T.copy(q);
      if (T.moveMain(draft, d)) { T.worldStep(q, d); return true; }
    }
    return false;
  };
  const absorber = () => q.g.find((t) => t && t.side === 'p' && !t.core);

  const n0 = absorber().n;
  press();
  const n1 = absorber().n;
  const neutralsAfter1 = q.g.filter((t) => t && t.side === 'n').length;
  check(n1 === 4, 'press 1: 2 stepped up to 4', `${n0} -> ${n1}`);
  check(neutralsAfter1 === 2, 'press 1 consumed exactly one neutral', `${neutralsAfter1} left`);
  check(!T.tutorialDone(q), 'lesson is NOT complete after one press (it is a real arc)');

  press();
  const n2 = absorber().n;
  check(n2 === 8, 'press 2: 4 stepped up to 8 (payload reached its value)', `${n1} -> ${n2}`);

  // the neutral that ended up beside the capped 8 must have survived it
  const spared = q.g.some((t) => t && t.side === 'n' && t.n === 2);
  check(spared, 'the neutral 2 beside the capped 8 SURVIVED (cap rule holds)');
  check(T.tutorialDone(q), 'lesson reports complete after the arc');
  check(T.valid(q), 'lesson 02 final state passes valid()');
}"""

NEW = """// --- 第 02 关：两次下移把吸收方块喂过阈值 --------------------------------
console.log('\\n=== 第 02 关是一条两次下移的弧线，并演示阈值 ===');
{
  const DIRS = ['down', 'left', 'right', 'up'];
  const q = T.tutorialInitial(1);
  const press = () => {
    for (const d of DIRS) {
      const draft = T.copy(q);
      if (T.moveMain(draft, d)) { T.worldStep(q, d); return true; }
    }
    return false;
  };
  const absorber = () => q.g.find((t) => t && t.side === 'p' && !t.core);

  const n0 = absorber().n;
  press();
  const n1 = absorber().n;
  const neutralsAfter1 = q.g.filter((t) => t && t.side === 'n').length;
  check(n1 === 8, '第一次下移：2 一次吸到两个中立，升到 8', `${n0} -> ${n1}`);
  check(neutralsAfter1 === 1, '第一次下移吃掉两个中立', `剩余=${neutralsAfter1}`);
  check(!T.tutorialDone(q), '一次下移还不算完成（是一条真正的弧线）');

  press();
  const ab = absorber();
  check(ab.n === 16, '第二次下移：8 升到 16（越过阈值）', `${n1} -> ${ab.n}`);
  check((ab.payload || 0) === 0, '越过阈值后进度清零（不变量）', `进度=${ab.payload || 0}`);
  check(T.tutorialDone(q), '弧线走完，本关完成');
  check(T.valid(q), '第 02 关终局通过 valid()');
}"""

t2 = sub(t2, OLD, NEW, 1, 'test_step2_tutorial.js 第 02 关弧线期望改到新规则')
p2.write_text(t2, encoding='utf-8', newline='')
print('完成')
