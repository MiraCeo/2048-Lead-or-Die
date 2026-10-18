"""规则变更后，把过时的旧测试更新到新规格。

规则变了三处，直接推翻了三组旧断言：
  1. 准入从"数字 < 阈值"放宽到"数字 <= 阈值"
     -> step2 的 C、D 两组测的是"到达上限就不吸收"，现在阈值本身仍可吸收
        （越过阈值才停），所以改成用"超过阈值"的方块来测
  2. "不满血 -> 进度转回血"这条旧规则被整体移除（回血改成固定百分比）
     -> step3 整套测的都是旧模型，作废；其中仍然有效的整局不变量搬进 test_rules
  3. 教程第 02 关的盘面建立在"8 是天花板"之上
     -> 本轮先让它在新规则下仍可通关，展示层的重做留到"进度条/满格灰"那一步

本脚本只改测试与文档，不改引擎。
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
SRC = ROOT / 'src'
TOOLS = ROOT / 'tools'
applied = []


def fail(msg):
    print('\n中止：%s' % msg)
    print('内存中已应用：%s' % (', '.join(applied) or '无'))
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s：预期 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:200]))
    applied.append(label)
    return text.replace(old, new)


# ===================================================== step2：C 与 D 改到新规则
p = TOOLS / 'test_step2.js'
t = p.read_text(encoding='utf-8')

t = sub(t,
        "console.log('\\n=== C. a tile at the cap does not absorb ===');\n"
        "{\n"
        "  const q = mkState([{ i: P(50, 50), n: 8, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
        "  G.autoCollect(q);\n"
        "  check(q.g[P(50, 51)] !== null, 'the neutral beside a capped tile survives');\n"
        "}",
        "console.log('\\n=== C. 超过阈值才停：阈值本身仍可吸收 ===');\n"
        "{\n"
        "  const at = mkState([{ i: P(50, 50), n: 8, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
        "  G.autoCollect(at);\n"
        "  check(at.g[P(50, 51)] === null, '数字等于阈值（8）的方块可以吸收');\n"
        "\n"
        "  const over = mkState([{ i: P(50, 50), n: 16, side: 'p' }, { i: P(50, 51), n: 2, side: 'n' }]);\n"
        "  G.autoCollect(over);\n"
        "  check(over.g[P(50, 51)] !== null, '数字超过阈值（16）的方块不吸收');\n"
        "}",
        1, 'step2 C：改成测"等于阈值可吸收 / 超过阈值不吸收"')

t = sub(t,
        "console.log('\\n=== D. a capped SITE does not vacuum: no eligible receiver means no absorption ===');\n"
        "{\n"
        "  const q = mkState([{ i: P(50, 50), n: 2, side: 'n' }]); // only the core nearby, and it is at 8\n"
        "  // the core sits at P(40,40); put a neutral in its ring\n"
        "  q.g[P(50, 50)] = null;\n"
        "  q.g[P(39, 39)] = { id: 7001, n: 2, side: 'n', core: false, team: null, hp: 3 ** G.lvl(2) * 3, cap: 3 ** G.lvl(2) * 3 };\n"
        "  G.autoCollect(q);\n"
        "  check(q.g[P(39, 39)] !== null, 'neutral in a capped core\\'s radius survives (no receiver under the cap)');\n"
        "}",
        "console.log('\\n=== D. 站点自身也不越权：超过阈值且无其他受方时，不吸收 ===');\n"
        "{\n"
        "  const q = mkState([]);\n"
        "  const core = q.g[P(40, 40)];\n"
        "  core.n = 16; core.cap = CAP(16); core.hp = CAP(16);   // 核心已超过阈值\n"
        "  q.g[P(39, 39)] = { id: 7001, n: 2, side: 'n', core: false, team: null, hp: CAP(2), cap: CAP(2) };\n"
        "  G.autoCollect(q);\n"
        "  check(q.g[P(39, 39)] !== null, '核心超过阈值、环内又没有其他己方块时，中立不被吸收');\n"
        "}",
        1, 'step2 D：改成测"超过阈值的站点不当受方"')

p.write_text(t, encoding='utf-8', newline='')
print('已更新 test_step2.js')

# ===================================================== step3 作废：搬走仍有效的不变量
p4 = TOOLS / 'test_rules.js'
t4 = p4.read_text(encoding='utf-8')
t4 = sub(t4,
         "  const badN = q.g.filter((t) => t && !Number.isInteger(Math.log2(t.n)));\n"
         "  check(badN.length === 0, '所有数字仍是 2 的幂', `违例=${badN.length}`);\n"
         "}",
         "  const badN = q.g.filter((t) => t && !Number.isInteger(Math.log2(t.n)));\n"
         "  check(badN.length === 0, '所有数字仍是 2 的幂', `违例=${badN.length}`);\n"
         "  const overHeal = q.g.filter((t) => t && t.hp > t.cap);\n"
         "  check(overHeal.length === 0, '没有方块血量超过上限', `违例=${overHeal.length}`);\n"
         "  const negProgress = q.g.filter((t) => t && (t.payload || 0) < 0);\n"
         "  check(negProgress.length === 0, '没有方块进度为负', `违例=${negProgress.length}`);\n"
         "}",
         1, '把原先 step3 里仍有效的整局不变量搬进 test_rules')

p4.write_text(t4, encoding='utf-8', newline='')
print('已更新 test_rules.js')

(TOOLS / 'test_step3.js').unlink()
applied.append('删除 test_step3.js（旧模型作废）')
print('已删除 test_step3.js（它整套测的是被替换掉的"进度转回血"模型）')

# ===================================================== 教程第 02 关：先在新规则下可通关
p2 = SRC / 'tutorial.lessons.js'
les = p2.read_text(encoding='utf-8')

les = sub(les, "else if(level===1){add(5150,2,'p');add(5250,8,'p');add(5151,2);add(5351,4);add(5451,2);}",
          "else if(level===1){add(5150,2,'p');add(5151,2);add(5251,4);add(5351,8);}",
          1, '教程第 02 关：盘面改为沿纵列摆放 2 / 4 / 8 三个中立')

les = sub(les, "if(q.lesson===1)return q.g.filter(t=>t?.side==='n').length===1&&q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=8);",
          "if(q.lesson===1)return q.g.filter(t=>t?.side==='n').length===0&&q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=16);",
          1, '教程第 02 关：过关条件改为"吃光中立并把吸收方块喂到 16（越过阈值）"')

les = sub(les,
          "task=s.turn?'再按 ↓，把它喂到上限':'按 ↓，观察自动吸收';hint=s.turn?'累积量要够到当前数字才会翻倍。核心和右边那个 8 都已经达到上限，不会吸收——它们旁边的中立只能靠推动或合并来收编。':'下方那个己方 2 未满上限，会把范围内的中立吸过来。累积够 2 就升到 4，再够 4 就升到 8。';",
          "task=s.turn?'继续按 ↓，喂到超过阈值':'按 ↓，观察自动吸收';hint=s.turn?'进度要够到当前数字才翻倍。8 仍然可以吸收，但升到 16 就超过阈值了——超过阈值的方块不再吸收，进度也会清零。':'下方那个己方 2 不超过阈值，会把范围内的中立吸过来。累积够 2 就升到 4，够 4 就升到 8，够 8 就升到 16。';",
          1, '教程第 02 关：任务与提示改为讲"阈值"')

les = sub(les, "s.lesson===1&&s.turn===1&&neutral===2?'观察成功：未满上限的 2 升到了 4；旁边那个已达上限的 8 没有吸收中立。'",
          "s.lesson===1&&s.turn===1&&neutral===2?'观察成功：不超过阈值的方块自己把中立吸过来了。'",
          1, '教程第 02 关：中途提示改为讲"阈值"')

p2.write_text(les, encoding='utf-8', newline='')
print('已更新教程第 02 关')

# 教程测试的期望值同步
p3 = TOOLS / 'test_step2_tutorial.js'
t3 = p3.read_text(encoding='utf-8')

t3 = sub(t3, "  check(neutrals.length === 3, 'three neutrals on the board', `count=${neutrals.length}`);",
         "  check(neutrals.length === 3, '盘面有三个中立', `数量=${neutrals.length}`);",
         1, '教程测试：中立数量标签改中文')

t3 = sub(t3, "  const core = q.g.find((t) => t && t.core && t.side === 'p');\n"
             "  check(core && core.n >= 8, 'the core starts at the cap (cannot absorb)', `core=${core && core.n}`);",
         "  const core = q.g.find((t) => t && t.core && t.side === 'p');\n"
         "  check(core && core.n === 8, '核心是 8（等于阈值，仍可吸收）', `核心=${core && core.n}`);",
         1, '教程测试：核心断言改到新规则')

p3.write_text(t3, encoding='utf-8', newline='')
print('已更新 test_step2_tutorial.js')

print()
print('本次应用 %d 项：' % len(applied))
for a in applied:
    print('  - %s' % a)
