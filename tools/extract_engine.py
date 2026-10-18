"""拆分器：把 src/main.script.js 切成 src/engine/ 下的域模块。

**这是纯搬移，不改一个字符。** 验收标准是拼回去必须与原文件逐字节相同。

为什么切分点必须落在行首：
    13 条教程补丁是精确子串匹配，锚点就是那些未格式化的压缩长行
    （最长单行 2284 字符）。重建差一个字节 -> 锚点全失配 -> 构建失败。

切分依据（机械推导，非人工挑选）：
    tools/engine_structure.py 扫描出的「IIFE 内部相对深度 0 且位于行首」的位置，
    共 125 个顶层单元。本脚本按行号区间把它们归组为 13 个域模块。

每个模块文件头部写入 `_start` / `_end`（原文件行号），作用有二：
    1. 重建时**校验**内容确实是那一段（不是靠文件名猜）；
    2. 将来出问题时能一眼看出是哪段搬错了位置。

模块文件格式：
    // ==== <模块名> ====
    // 来源: main.script.js 第 <start>–<end> 行（原样搬移，未改一字符）
    // <说明>
    <原样内容>
"""
import io
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)
SRC = ROOT / 'src' / 'main.script.js'
OUTDIR = ROOT / 'src' / 'engine'

# (模块名, 起始行, 结束行, 说明)  —— 行号含两端，1 基，闭区间
# 切分点来自 tools/engine_structure.py 的实测输出（125 个顶层单元的行区间），
# 不是人工挑选。区间必须无缝覆盖 1..161，见下方覆盖性校验。
MANIFEST = [
    ('10-prelude',  1,  13, "IIFE 头、'use strict'、DOM/常量、全局状态、工具函数"),
    ('20-board',   14,  25, 'core 取值、rescale、连通、分化、中性密集区、轮廓'),
    ('30-units',   26,  48, '存档编码、敌方编成、初始盘面'),
    ('40-combat',  49,  57, '接触、主移动、额外操作'),
    ('50-absorb',  58,  74, '回血、吸收结算、自动收集、科技树取值'),
    ('60-tech',    75,  93, '科技树 UI 与购买、飞行器成长、置换'),
    ('70-turn',    94, 105, 'worldStep 回合循环、camera/屏幕映射'),
    ('80-ui',     106, 129, '重绘/撤销/重开、小地图、ui()、拖拽绘制'),
    ('90-draw',   130, 148, '方块绘制、整帧 draw、特效渲染'),
    ('95-input',  149, 160, '指针/键盘/对话框接线、教程与介绍'),
    ('99-boot',   161, 161, 'valid() 与启动引导'),
]


def main():
    text = io.open(SRC, encoding='utf-8', newline='').read()
    lines = text.split('\n')
    # split 后若以换行结尾，最后一个元素是空串：去掉它，让 lines 长度 == 行数
    trailing_nl = text.endswith('\n')
    if trailing_nl:
        lines = lines[:-1]

    # ⚠️ 源码已被阶段 4 格式化为 2282 行，而 MANIFEST 的行区间是针对**阶段 2 的 161 行**
    # 压缩文本写的。所以现在的 extract 只能做两件事之一：
    #   --manifest-only  只重新生成清单（安全，不碰模块内容）
    #   其他             **仅当源码仍是 161 行时**才允许重切模块，否则拒绝
    # 之所以要这道闸：重切会把格式化后的模块覆盖回压缩内容，那是破坏性的。
    manifest_only = '--manifest-only' in sys.argv
    if not manifest_only and len(lines) != 161:
        sys.exit('拒绝执行：src/main.script.js 现有 %d 行，而本脚本的行区间是针对 161 行\n'
                 '的压缩文本写的。重切会覆盖掉已格式化的模块内容。\n'
                 '  · 只想更新清单：加 --manifest-only\n'
                 '  · 真要重新拆分：请先确认源码已回到 161 行压缩格式' % len(lines))

    print('原文件: %d 行%s%s' % (len(lines), '（以换行结尾）' if trailing_nl else '',
                                 '  [--manifest-only]' if manifest_only else ''))

    # 覆盖性校验：区间必须无缝且连续（针对**清单自身**，与当前文件无关）
    expect = 1
    for name, a, b, _ in MANIFEST:
        if a != expect:
            sys.exit('区间不连续：%s 从 %d 开始，期望 %d' % (name, a, expect))
        if b < a:
            sys.exit('区间非法：%s [%d,%d]' % (name, a, b))
        expect = b + 1
    # 只有真的要重切模块时，才要求清单覆盖**当前**文件
    if not manifest_only and expect != len(lines) + 1:
        sys.exit('区间未覆盖全文件：覆盖到 %d，实际 %d 行' % (expect - 1, len(lines)))

    OUTDIR.mkdir(parents=True, exist_ok=True)
    written = []

    if not manifest_only:
        for name, a, b, desc in MANIFEST:
            body = lines[a - 1:b]
            # ⚠️ 措辞随阶段演进：阶段 2 是"原样搬移"，阶段 3 改过 KEY，
            # 阶段 4 被 prettier 格式化过。写死"未改一字符"会误导人。
            header = ('// ==== %s ====\n'
                      '// 溯源: 阶段 2 的压缩文本 main.script.js 第 %d\u2013%d 行'
                      '（此后经阶段 3 改名、阶段 4 格式化）\n'
                      '// %s\n' % (name, a, b, desc))
            out = OUTDIR / (name + '.js')
            io.open(out, 'w', encoding='utf-8', newline='').write(header + '\n'.join(body) + '\n')
            written.append((name, a, b, len(body)))

    # 写清单，供 bundler 使用（bundler 以清单为准，不从文件名序号猜顺序）
    #
    # ⚠️ 这里**不记每个模块的行数**。
    # 阶段 2 当时记了 `lines`，用来校验拆分没切错；但阶段 4 的 prettier 格式化
    # 必然改变行数，那个字段就永久过期了 —— 而它会出现在 bundler 的输出里
    # （"正文 413 行，清单记 23 行"），让人以为哪里坏了。
    # 改成只留**仍然成立**的字段：
    #   · name / 顺序      —— 拼接顺序，永远有效
    #   · headerLines      —— 每个模块文件的注释头行数，永远有效
    #   · origStart/origEnd —— 该模块来自**阶段 2 那个压缩文本**的哪几行，
    #                          仅供溯源（模块头注释里也写着）。格式化后与现文无关。
    man = {
        'source': 'src/main.script.js',
        'trailingNewline': trailing_nl,
        'headerLines': 3,
        'note': ('origStart/origEnd 指向阶段 2 的压缩文本（161 行），仅供溯源。'
                 '阶段 4 格式化后模块行数与它无关，故本清单不记行数。'),
        'modules': [{'name': n, 'origStart': a, 'origEnd': b}
                    for (n, a, b, _) in MANIFEST],
    }
    io.open(OUTDIR / 'manifest.json', 'w', encoding='utf-8', newline='\n').write(
        json.dumps(man, ensure_ascii=False, indent=2) + '\n')

    print()
    if manifest_only:
        print('已重新生成清单（未改动任何模块文件）: %s' % (OUTDIR / 'manifest.json'))
        print()
        for (name, a, b, desc) in MANIFEST:
            print('  %-14s 溯源 %d\u2013%d   %s' % (name, a, b, desc))
    else:
        print('%-14s %-12s %8s  %s' % ('模块', '溯源区间', '行数', '说明'))
        print('-' * 96)
        for (name, a, b, desc), (_, _, _, ln) in zip(MANIFEST, written):
            print('%-14s %-12s %8d  %s' % (name, '%d\u2013%d' % (a, b), ln, desc))
        print('-' * 96)
        print('%-14s %-12s %8d' % ('合计', '', sum(w[3] for w in written)))
        print()
        print('清单: %s' % (OUTDIR / 'manifest.json'))


if __name__ == '__main__':
    main()
