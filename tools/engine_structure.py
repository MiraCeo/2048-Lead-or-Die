"""分析 src/main.script.js 的顶层结构，找出**字节级安全**的切分点。

为什么要分析而不是直接按函数拆：
  拆分 + 重建必须逐字节还原原文件，否则 13 条教程补丁锚点会失配。
  而 JS 的顶层顺序是**有语义**的（const 初始化顺序、函数提升、IIFE 作用域），
  所以切分点必须落在"行首且括号深度为 0"的位置，不能凭模块划分的直觉决定。

做法：手写扫描器（不能用正则——字符串/模板串/正则字面量/注释里的括号会骗过它），
逐字符跟踪：
    - 单引号 / 双引号 / 模板串（含 ${} 嵌套）
    - 行注释 / 块注释
    - () [] {} 深度
在"深度为 0 且位于行首"的偏移处记录切分点。

输出：每个顶层单元的行区间与首行摘要，供决定模块归组。
"""
import io
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)
SRC = ROOT / 'src' / 'main.script.js'

text = io.open(SRC, encoding='utf-8').read()
n = len(text)


def scan(text):
    """返回 IIFE 内部「相对深度 0 且位于行首」的偏移列表。

    注意：整个文件被 `(()=>{ ... })();` 包着，所以绝对深度恒 ≥1。
    要找的是**相对 IIFE 体**的深度 0 —— 即顶层语句的起点。
    """
    points = []
    depth = 0
    base = None            # IIFE 体的绝对深度
    i = 0
    n = len(text)
    line_start = True
    while i < n:
        ch = text[i]

        if ch == '\n':
            line_start = True
            i += 1
            continue

        # 注释
        if ch == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] != '\n':
                i += 1
            continue
        if ch == '/' and i + 1 < n and text[i + 1] == '*':
            i += 2
            while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
            continue

        # 字符串
        if ch in "'\"":
            q = ch
            i += 1
            while i < n:
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i] == q:
                    i += 1
                    break
                i += 1
            line_start = False
            continue

        # 模板串
        if ch == '`':
            i += 1
            tdepth = 0
            while i < n:
                c = text[i]
                if c == '\\':
                    i += 2
                    continue
                if c == '$' and i + 1 < n and text[i + 1] == '{':
                    tdepth += 1
                    i += 2
                    continue
                if c == '}' and tdepth > 0:
                    tdepth -= 1
                    i += 1
                    continue
                if c == '`' and tdepth == 0:
                    i += 1
                    break
                i += 1
            line_start = False
            continue

        # 括号
        if ch in '([{':
            depth += 1
            if ch == '{' and base is None and depth == 2:
                # 首行的 `(()=>{` 里，函数体左花括号落在深度 2；
                # 它就是 IIFE 体的起点，之后的顶层语句都在这个深度。
                base = depth
            line_start = False
            i += 1
            continue
        if ch in ')]}':
            depth -= 1
            line_start = False
            i += 1
            continue

        # 行首 + 相对深度 0 + 非空白 -> 一个顶层语句的起点
        if line_start and base is not None and depth == base and not ch.isspace():
            points.append(i)
        if not ch.isspace():
            line_start = False
        i += 1
    return points


pts = scan(text)
# 去掉偏移 0 本身（它是文件开头，留给"前导"处理）
starts = [p for p in pts if p > 0]

lines = text.split('\n')
# 行号（1 基）-> 偏移
line_off = [0]
for ln in lines:
    line_off.append(line_off[-1] + len(ln) + 1)


def line_of(off):
    lo, hi = 0, len(line_off) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_off[mid] <= off:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


print('文件: %s' % SRC)
print('字节 %d · 行 %d · 顶层切分点 %d 个' % (len(text.encode('utf-8')), len(lines), len(starts)))
print()
print('前导（文件开头到第一个切分点）: 第 1–%d 行, %d 字符'
      % (line_of(starts[0]) - 1, starts[0]))

# 逐个单元输出
bounds = starts + [n]
print()
print('%-4s %-10s %-10s %8s  %s' % ('#', '起始行', '结束行', '字符数', '首行摘要'))
print('-' * 110)
for k in range(len(bounds) - 1):
    a, b = bounds[k], bounds[k + 1]
    chunk = text[a:b]
    la, lb = line_of(a), line_of(b - 1)
    head = chunk.split('\n')[0].strip()
    if len(head) > 62:
        head = head[:62] + '…'
    print('%-4d %-10d %-10d %8d  %s' % (k + 1, la, lb, len(chunk), head))
