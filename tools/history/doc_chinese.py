"""项目文档：术语全部改回中文，并记录本次改动。

你明确说看不懂 CAP 这类英文缩写，而项目文档是这个项目唯一的工作记录，
所以它必须你能读。这里把所有英文缩写换成中文说法，并追加本次改动的记录。
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

DOC = Path(r'D:\2048') / '项目文档.md'
t = DOC.read_text(encoding='utf-8')

# 顺序很重要：先换长的（含缩写的名字），再换短的（裸缩写）
SWEEP = [
    ('ABSORB_CAP', '吸收阈值常量'),
    ('ABSORB_TP', '每回合吸收次数常量'),
    ('ABSORB_RADIUS', '吸收半径常量'),
    ('SITE_TP', '站点吞吐上限'),
    ('REGEN_FRAC', '回血比例'),
    ('SCORE_PER_TECH', '积分兑换比'),
    ('TECH_TP_MAX', '吞吐等级上限'),
    ('TECH_RADIUS_MAX', '半径等级上限'),
    ('TECH_THRESHOLD_MAX', '阈值等级上限'),
    ('AI_ABSORB_CEILING', '敌方吸收上限'),
    ('AI_REGEN_RATE', '敌方回血比例'),
    ('absorbThreshold', '吸收阈值（函数）'),
    ('aiAbsorbCeiling', '敌方上限（函数）'),
    ('regenTiles', '回血（函数）'),
    ('markCombat', '战斗计数（函数）'),
    ('upThreshold', '阈值等级'),
    ('upRadius', '半径等级'),
    ('upTp', '吞吐等级'),
    ('payload', '升级进度'),
    ('neutralGroups', '中立成组（旧函数）'),
    ('neutralClusters', '中立密集区（函数）'),
    ('waveSpec', '波次规格（函数）'),
    ('fillEnemy', '补员（函数）'),
    ('nextGrowth', '下次成长回合'),
    ('techCost', '升级成本（函数）'),
    ('techMax', '等级上限（函数）'),
    ('techLevel', '等级读取（函数）'),
    ('survey', '探索结算（函数）'),
]

report = []
for old, new in SWEEP:
    n = t.count(old)
    if n:
        t = t.replace(old, new)
        report.append((old, new, n))

# 裸缩写（用词边界，避免误伤别的词）
for pat, new in [(r'(?<![A-Za-z])CAP(?![A-Za-z])', '阈值'),
                 (r'(?<![A-Za-z])TP(?![A-Za-z])', '吞吐'),
                 (r'(?<![A-Za-z])AI(?![A-Za-z])', '敌方'),
                 (r'(?<![A-Za-z])seed(?![A-Za-z])', '随机种子')]:
    n = len(re.findall(pat, t))
    if n:
        t = re.sub(pat, new, t)
        report.append((pat, new, n))

# §11.1 已解决（阈值线就是那条新轴）
OLD_111 = """### 11.1 第二条线要换成真正不同的轴（评审 #3）

**受阻**：我给的两个候选都依赖阈值，而阈值按决策 5 暂缓（单 seed 结论不可信）。详见 §5 的评审表。

**不受阻的替代（推荐）**：把"**吞吐 吞吐**"这条线换成"**恢复**"线——让玩家**购买回血**。
它同时解决三件事：①与半径线真正正交（生存 vs 发育）；②复用已有机制而非新造；
③**把 §5 的"回血模型"未决问题从"我替你选"变成"玩家自己买"**。"""

NEW_111 = """### 11.1 第二条线要换成真正不同的轴 —— 已解决 ✅

**解决方式**：你指出我漏掉了最基础的一条线——**提高自动合成阈值**。它回到树里之后，
"两条线同向"的问题自然消失：**阈值决定发育天花板，半径决定覆盖面**，是两条真正不同的轴。
同时"恢复"不做成可购买项（你已定为固定 5% + 10 回合门槛的规则）。

我原先的两个候选（阈值本身、阈值的补偿）之所以做不了，是因为我把阈值排除在外；
阈值一回到树里，它们就不再是"候选"而是**正常的一条线**。这个判断错误已记在 §5 的评审表里。"""

if OLD_111 in t:
    t = t.replace(OLD_111, NEW_111)
    report.append(('§11.1 改为已解决', '', 1))
else:
    # 缩写已被替换，用替换后的形态再试一次
    alt = OLD_111.replace('CAP', '阈值').replace('TP', '吞吐')
    if alt in t:
        t = t.replace(alt, NEW_111)
        report.append(('§11.1 改为已解决（缩写替换后匹配）', '', 1))
    else:
        print('警告：§11.1 未匹配，留给下一轮手工处理')

print('术语替换：')
for old, new, n in report:
    print('  %-24s -> %-16s %d 处' % (old, new, n))

DOC.write_text(t, encoding='utf-8', newline='')
print()
print('项目文档已更新：%d 字符' % len(t))
