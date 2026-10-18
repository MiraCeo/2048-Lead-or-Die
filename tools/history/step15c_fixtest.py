"""修 test_fx.js 的 F 组：测试板本身有问题。

我的 mkState 默认已经在 (40,40) 放了一个 id=1 的核心；
F 组又加了一个 id=1 的核心，造成**重复 id** —— 于是 coreIndex(active=1) 找到的是
(40,40) 那个，(50,50) 那一组根本不受控，按右移碰不到敌人，自然没有对碰特效。

改成围绕默认核心 (40,40) 摆放。（这也暴露了 mkState 的脆弱处：再加同 id 的方块会撞号。）
"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_fx.js'
t = p.read_text(encoding='utf-8')

OLD = """  const mkClash = () => mkState([
    { i: P(50, 50), n: 8, side: 'p', core: true, id: 1, team: 1 },
    { i: P(50, 51), n: 4, side: 'p', id: 2, team: 1 },
    { i: P(50, 52), n: 2, side: 'e', core: true, id: 9, team: 9 },
  ]);"""
NEW = """  // 注意：mkState 默认已在 (40,40) 放了 id=1 的核心，这里围绕它摆，
  // 否则会造出第二个 id=1 的核心、受控核心就跑到别处去了。
  const mkClash = () => mkState([
    { i: P(40, 41), n: 4, side: 'p', id: 2, team: 1 },          // 与核心相连
    { i: P(40, 42), n: 2, side: 'e', core: true, id: 9, team: 9 },
  ]);"""

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('已修：F 组测试板围绕默认核心 (40,40) 摆放')
