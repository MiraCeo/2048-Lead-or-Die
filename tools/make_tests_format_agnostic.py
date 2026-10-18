"""阶段 4 配套：把测试里的源码层断言改成**忽略空白**，使其对代码格式化免疫。

## 为什么

test_display / test_shell / test_fx 里有一批"源码层断言"，例如：

    check(ENGINE.includes('bx=p.x-11,by=p.y+8,bw=22,bh=4'), '进度条加大到 22×4');

它们查的是**压缩写法**（无空格）。prettier 格式化会加空格：

    const bx = p.x - 11, by = p.y + 8, bw = 22, bh = 4;

于是断言失败 —— 但**被测的机制并没有坏**。这类断言记录的是历史实现约束
（如"进度条 22×4"、"核心已排除血量配色"），意图正确、写法过时。

## 做法

不再逐个改断言字符串（21 处，且下次再格式化又会失效），而是：
  1. 在每个测试文件顶部插入一个忽略空白的匹配助手 `has(src, pat)` / `notHas(src, pat)`
     —— 把两侧的**所有空白字符删掉**再比对；
  2. 把 `X.includes('…')` / `!X.includes('…')` 机械替换为 `has(X, '…')` / `notHas(X, '…')`。

这样断言表达的是"这段代码语义上在场"，与排版无关。

## 注意

`notHas` 走同样的归一化，所以**负向断言也仍然有效**：
`!ENGINE.includes('20*t.hp/t.cap')` 与格式化后的 `20 * t.hp / t.cap` 归一化后相等，
依然会被正确判定为"已移除"。

用法：
    python tools/make_tests_format_agnostic.py --check
    python tools/make_tests_format_agnostic.py --apply
"""
import io
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)

APPLY = '--apply' in sys.argv

FILES = [
    'tools/test_display.js',
    'tools/test_shell.js',
    'tools/test_fx.js',
]

HELPER = '''
// 源码层断言助手：忽略**所有空白**再比对。
// 原因：断言检查的是实现约束（如"进度条 22×4"），而 prettier 会加空格，
// 用裸 includes 会因排版差异误报。归一化后断言表达的是"语义在场"，与排版无关。
const _sq = (v) => String(v).replace(/\\s+/g, '');
function has(src, pat) {
  const found = _sq(src).includes(_sq(pat));
  if (!found) console.log('        [has] 未找到（归一化后）: ' + pat);
  return found;
}
function notHas(src, pat) {
  const found = _sq(src).includes(_sq(pat));
  if (found) console.log('        [notHas] 不该存在但找到了（归一化后）: ' + pat);
  return !found;
}
'''

# ⚠️ 严格匹配：只认**具名接收者**的 .includes(。
# 上一版写成任意标识符，结果把数组字面量 `[...].includes(x)` 也匹配了，
# 而且 `(?P<neg>!)?` 会吃掉属于外层代码的 `!`
# （`!['满血',50,100].includes(x)` 被改成 `ofnotHas(...)`）。
# 现在：接收者限定为 RECEIVERS，否定符由**前一个字符**单独判定，绝不纳入匹配范围。
RECEIVERS = ['ENGINE', 'HTML', 'GUIDE']
RECV_ALT = '|'.join(RECEIVERS)
CALL_RE = re.compile(
    r'(?P<obj>' + RECV_ALT + r')\.includes\('
    r'(?P<arg>(?:\'(?:\\.|[^\'\\])*\'|"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`))'
    r'\)'
)


def main():
    print('=== 预检 ===')
    plans = []
    for rel in FILES:
        p = ROOT / rel
        text = io.open(p, encoding='utf-8', newline='').read()
        hits = list(CALL_RE.finditer(text))
        helper_present = 'function has(src, pat)' in text

        # 找一个合适的插入点：ENGINE 常量声明之后
        m = re.search(r"^const ENGINE\b[^\n]*$", text, re.M)
        if not m and not helper_present:
            print('  !! %s: 找不到 const ENGINE 行，无法确定插入点' % rel)
            continue
        plans.append((rel, text, hits, helper_present, m.end() if m else None))
        print('  %-26s includes 调用 %3d 处，助手%s'
              % (rel.split('/')[-1], len(hits), '已存在' if helper_present else '待插入'))

    total = sum(len(h) for _, _, h, _, _ in plans)
    print('  合计 %d 处待改' % total)
    if not APPLY:
        print()
        print('（预检模式，未写入；加 --apply 执行）')
        return 0

    print()
    print('=== 写入 ===')
    for rel, text, hits, helper_present, ins in plans:
        # **先替换、后插助手**：助手自身也调用 .includes(，若先插入会被自己的规则改写。
        for m in reversed(hits):
            obj, arg = m.group('obj'), m.group('arg')
            # 否定符只看**紧邻的前一个字符**，且必须真的是逻辑非（前面不是标识符/引号）
            k = m.start() - 1
            neg = False
            if k >= 0 and text[k] == '!':
                p = k - 1
                if p < 0 or not (text[p].isalnum() or text[p] in '_$)]}\'"`'):
                    neg = True
                    k = p          # 连同 '!' 一起替换
            fn = 'notHas' if neg else 'has'
            text = text[:k + 1] + '%s(%s, %s)' % (fn, obj, arg) + text[m.end():]
        if not helper_present and ins is not None:
            # 助手插入点：重新定位（前面的替换改变了偏移）
            m2 = re.search(r"^const ENGINE\b[^\n]*$", text, re.M)
            at = m2.end() if m2 else ins
            text = text[:at] + '\n' + HELPER + text[at:]
        io.open(ROOT / rel, 'w', encoding='utf-8', newline='').write(text)
        print('  %-26s 助手%s，替换 %d 处'
              % (rel.split('/')[-1], '已存在' if helper_present else '已插入', len(hits)))
    print()
    print('下一步：跑 node tools/test_display.js / test_shell.js / test_fx.js')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
