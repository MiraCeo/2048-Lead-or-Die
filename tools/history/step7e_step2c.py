"""step2 的 C 组同步到阈值 4（n=8 现在已经是"超过阈值"了）。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_step2.js'
t = p.read_text(encoding='utf-8')

OLD = ("  const at = mkState([{ i: P(50, 50), n: 8, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
       "  G.autoCollect(at);\n"
       "  check(at.g[P(50, 51)] === null, '数字等于阈值（8）的方块可以吸收');\n"
       "\n"
       "  const over = mkState([{ i: P(50, 50), n: 16, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
       "  G.autoCollect(over);\n"
       "  check(over.g[P(50, 51)] !== null, '数字超过阈值（16）的方块不吸收');")

NEW = ("  const at = mkState([{ i: P(50, 50), n: 4, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
       "  G.autoCollect(at);\n"
       "  check(at.g[P(50, 51)] === null, '数字等于阈值（4）的方块可以吸收');\n"
       "\n"
       "  const over = mkState([{ i: P(50, 50), n: 8, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
       "  G.autoCollect(over);\n"
       "  check(over.g[P(50, 51)] !== null, '数字超过阈值（8）的方块不吸收');")

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('step2 C 组已同步到阈值 4')
