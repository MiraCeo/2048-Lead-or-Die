"""规则测试同步到"基础阈值 4"。

阈值从 8 改成 4 之后，几组断言的取值要跟着变；其中 B 组最值得注意：
阈值 4 时"进度继承"只可能发生在 2 -> 4 这一步（4 一升到 8 就超过阈值、进度清零），
所以 B 组必须改用 2 起步，否则测不到继承。
"""
import sys
from pathlib import Path

TOOLS = Path(r'D:\2048') / 'tools'
p = TOOLS / 'test_rules.js'
t = p.read_text(encoding='utf-8')


def sub(old, new, n, label):
    global t
    c = t.count(old)
    if c != n:
        sys.exit('%s：预期 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:200]))
    t = t.replace(old, new)
    print('已改：%s' % label)


sub("  const q = mkState([{ i: P(50, 50), n: 8, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
    "  G.autoCollect(q);\n"
    "  check(q.g[P(50, 51)] === null, '阈值为 8 时，n=8 的方块把中立吸走了');",
    "  const q = mkState([{ i: P(50, 50), n: 4, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
    "  G.autoCollect(q);\n"
    "  check(q.g[P(50, 51)] === null, '阈值为 4 时，n=4 的方块（正好等于阈值）把中立吸走了');",
    1, 'A 组改到阈值 4')

sub("  const q = mkState([{ i: P(50, 50), n: 4, side: 'p', payload: 6 }]);\n"
    "  G.settleTiles(q, lvCore(q));\n"
    "  const t = q.g[P(50, 50)];\n"
    "  check(t.n === 8, '4 升到 8', `n=${t.n}`);\n"
    "  check(t.payload === 2, '多出的 2 点进度被继承（6-4=2）', `进度=${t.payload}`);",
    "  // 阈值 4 时，继承只可能发生在 2 -> 4 这一步\n"
    "  const q = mkState([{ i: P(50, 50), n: 2, side: 'p', payload: 3 }]);\n"
    "  G.settleTiles(q, lvCore(q));\n"
    "  const t = q.g[P(50, 50)];\n"
    "  check(t.n === 4, '2 升到 4', `n=${t.n}`);\n"
    "  check(t.payload === 1, '多出的 1 点进度被继承（3-2=1）', `进度=${t.payload}`);",
    1, 'B 组改到阈值 4 的可行区间（2 -> 4）')

sub("  const q = mkState([{ i: P(50, 50), n: 8, side: 'p', payload: 8 }]);\n"
    "  G.settleTiles(q, lvCore(q));\n"
    "  const t = q.g[P(50, 50)];\n"
    "  check(t.n === 16, '8 升到 16（越过阈值）', `n=${t.n}`);",
    "  const q = mkState([{ i: P(50, 50), n: 4, side: 'p', payload: 4 }]);\n"
    "  G.settleTiles(q, lvCore(q));\n"
    "  const t = q.g[P(50, 50)];\n"
    "  check(t.n === 8, '4 升到 8（越过阈值 4）', `n=${t.n}`);",
    1, 'C 组改到阈值 4')

sub("  const q2 = mkState([{ i: P(50, 50), n: 16, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
    "  G.autoCollect(q2);\n"
    "  check(q2.g[P(50, 51)] !== null, '超过阈值的方块不再吸收', '中立仍在');",
    "  const q2 = mkState([{ i: P(50, 50), n: 8, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
    "  G.autoCollect(q2);\n"
    "  check(q2.g[P(50, 51)] !== null, '超过阈值的方块（8 大于阈值 4）不再吸收', '中立仍在');",
    1, 'D 组第二个断言改到阈值 4')

sub("  check(G.absorbThresholdAt(0) === 8, '0 级阈值 8', `${G.absorbThresholdAt(0)}`);\n"
    "  check(G.absorbThresholdAt(1) === 16, '1 级阈值 16', `${G.absorbThresholdAt(1)}`);\n"
    "  check(G.absorbThresholdAt(2) === 32, '2 级阈值 32', `${G.absorbThresholdAt(2)}`);\n"
    "  // 阈值 16 时，8 可以继续吸收；且 16 本身也能吸收\n"
    "  const q = mkState([{ i: P(50, 50), n: 16, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
    "  q.upThreshold = 1;\n"
    "  G.autoCollect(q);\n"
    "  check(q.g[P(50, 51)] === null, '阈值 16 时，n=16 的方块可以吸收');",
    "  check(G.absorbThresholdAt(0) === 4, '0 级阈值 4（基础）', `${G.absorbThresholdAt(0)}`);\n"
    "  check(G.absorbThresholdAt(1) === 8, '1 级阈值 8', `${G.absorbThresholdAt(1)}`);\n"
    "  check(G.absorbThresholdAt(2) === 16, '2 级阈值 16', `${G.absorbThresholdAt(2)}`);\n"
    "  check(G.absorbThresholdAt(3) === 32, '3 级阈值 32（上限）', `${G.absorbThresholdAt(3)}`);\n"
    "  // 阈值升到 16 时，n=16 本身也能吸收\n"
    "  const q = mkState([{ i: P(50, 50), n: 16, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
    "  q.upThreshold = 2;\n"
    "  G.autoCollect(q);\n"
    "  check(q.g[P(50, 51)] === null, '阈值 16 时，n=16 的方块可以吸收');",
    1, 'E 组改为 4/8/16/32 四级')

sub("  check(G.aiAbsorbCeiling({}) === 8, '敌方天花板默认 8', `${G.aiAbsorbCeiling({})}`);",
    "  check(G.aiAbsorbCeiling({}) === 4, '敌方天花板默认跟随基础值 4', `${G.aiAbsorbCeiling({})}`);",
    1, 'M 组敌方天花板改为 4')

sub("  check(c.n === 16, '停在天花板的两倍（16），不再更高', `n=${c.n}`);",
    "  check(c.n === 8, '停在天花板的两倍（8），不再更高', `n=${c.n}`);",
    1, 'M 组采集机上限改为 8')

p.write_text(t, encoding='utf-8', newline='')
print('\ntest_rules.js 已同步')
