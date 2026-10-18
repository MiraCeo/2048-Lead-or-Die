"""吸收阈值规则 + 敌方天花板 + 乙（受伤可升级）+ 回血。

本次实现你锁定的规格：

【吸收阈值】
  - 数字 <= 阈值的己方块可以吸收（原来是严格小于）
  - 升级后若新数字仍 <= 阈值 -> 继承多余进度；超过阈值 -> 进度清零
  - 不变量：不存在"数字 > 阈值 且 进度不为 0"的方块（对手动合并出来的高值块也强制清零）
  - 基础 8，每级翻倍，暂时到 32（8 -> 16 -> 32）
  - 因此方块自动可达的上限是阈值的两倍（这是你确认过的底层规则）
  - 吸收仍然删除格子，不留伴生块

【敌方天花板】
  - 采集机不再无上限：独立参数（默认 8），玩家升阈值不会连带强化敌方
  - 采集机升级也不再回满血，改为等比例继承（与玩家同一条规则）

【乙】
  - 受伤也能升级（不再需要满血）
  - 升级只等比例继承血量，不回满

【回血】
  - 固定为方块血量上限的百分比，基础每回合 5%
  - 必须先脱离战斗 10 回合
  - 受伤即计数归零，且每个核心独立计数（实现上按"队伍"计数，每个核心自成一支队伍）
  - 不加"满血自动增加升级进度"那部分
  - 敌方回血参数存在但默认 0（等于不启用）

因为回血不再消耗进度，"受伤 -> 进度转血量"这条旧规则被整体移除。
"""
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = Path(r'D:\2048')
SRC = ROOT / 'src'
applied = []


def fail(msg):
    print()
    print('实施中止：%s' % msg)
    print('内存中已应用的改动：%s' % (', '.join(applied) or '无'))
    print('注意：尚未写入任何源文件，src/ 与交付物保持原样。')
    sys.exit(1)


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        fail('%s：预期命中 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:220]))
    applied.append(label)
    return text.replace(old, new)


def sub_re(text, pattern, new, n, label, flags=0):
    c = len(re.findall(pattern, text, flags))
    if c != n:
        fail('%s：预期匹配 %d 次，实际 %d 次\n  模式：%r' % (label, n, c, pattern[:220]))
    applied.append(label)
    return re.sub(pattern, new, text, flags=flags)


js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')

# ============================================================ 常量
js = sub(js,
         'const ABSORB_CAP=8,ABSORB_TP=2,ABSORB_RADIUS=1,SITE_TP=4,REGEN_FRAC=0.1;',
         'const ABSORB_CAP=8,ABSORB_TP=2,ABSORB_RADIUS=1,SITE_TP=4,'
         'REGEN_RATE=0.05,REGEN_DELAY=10,AI_REGEN_RATE=0,AI_ABSORB_CEILING=8;',
         1, '常量：回血改为固定 5% + 10 回合门槛，新增敌方天花板与敌方回血参数')

js = sub(js, 'const SCORE_PER_TECH=100,TECH_TP_MAX=2,TECH_RADIUS_MAX=2;',
         'const SCORE_PER_TECH=100,TECH_TP_MAX=2,TECH_RADIUS_MAX=2,TECH_THRESHOLD_MAX=2;',
         1, '常量：阈值线等级上限')

# ============================================================ 阈值曲线
js = sub(js, 'function siteRadiusAt(lv){return ABSORB_RADIUS+(lv||0);}',
         'function absorbThresholdAt(lv){return ABSORB_CAP*(2**(lv||0));}'
         'function absorbThreshold(q){return absorbThresholdAt(q.upThreshold||0);}'
         'function aiAbsorbCeiling(q){return AI_ABSORB_CEILING;}'
         'function siteRadiusAt(lv){return ABSORB_RADIUS+(lv||0);}',
         1, '阈值曲线（基础 8，每级翻倍）')

# ============================================================ 战斗计数 + 回血
js = sub(js, 'function settleTiles(q,lvCore){',
         'function markCombat(q,t){if(!t||t.side===\'n\')return;q.combat=q.combat||{};q.combat[t.team]=q.turn;}\n'
         'function regenTiles(q){let healed=0;q.combat=q.combat||{};'
         'for(let i=0;i<N*N;i++){const t=q.g[i];'
         'if(!t||t.support||t.side===\'n\')continue;'
         'if(t.hp>=t.cap)continue;'
         'const rate=t.side===\'p\'?REGEN_RATE:AI_REGEN_RATE;'
         'if(!(rate>0))continue;'
         'const last=q.combat[t.team];'
         'if(last!==undefined&&q.turn-last<REGEN_DELAY)continue;'
         'const amt=Math.max(1,Math.ceil(t.cap*rate));'
         't.hp=Math.min(t.cap,t.hp+amt);healed++;}'
         'return healed;}\n'
         'function settleTiles(q,lvCore){',
         1, '新增 markCombat 与 regenTiles')

# 结算重写：受伤也能升级 + 进度继承 + 不变量；移除"受伤转回血"
js = sub_re(js, r'^function settleTiles\(q,lvCore\)\{.*\}$',
            lambda m: (
                "function settleTiles(q,lvCore){const th=absorbThreshold(q);let grown=0;"
                "for(let i=0;i<N*N;i++){const t=q.g[i];"
                "if(!t||t.side!=='p'||t.support)continue;"
                "if(t.n>th){if(t.payload)t.payload=0;continue;}"
                "let pay=t.payload||0;if(pay<=0)continue;"
                "while(pay>=t.n){pay-=t.n;"
                "const oldCap=t.cap||1,oldHp=t.hp??oldCap;"
                "t.n*=2;t.cap=3**lvl(t.n)*lvCore;"
                "t.hp=Math.max(1,Math.min(t.cap,Math.round(oldHp*t.cap/oldCap)));"
                "grown++;"
                "if(t.n>th){pay=0;break;}}"
                "t.payload=pay;}"
                "return grown;}"
            ),
            1, '结算重写：受伤可升级 · 进度继承 · 超阈值清零', re.M)

# ============================================================ autoCollect 整体重写
js = sub_re(js, r'^function autoCollect\(q\)\{.*\}$',
            lambda m: (
                "function autoCollect(q){const lvCore=lvl(sharedCore(q));let grown=0,absorbed=0;"
                "const tps=absorbTp(q),th=absorbThreshold(q);survey(q);"
                "for(let s=0;s<N*N;s++){const site=q.g[s];"
                "if(!site||site.side!=='p'||!(site.core||site.support))continue;"
                "const R=site.collectRadius??siteRadius(q),ring=ringCells(s,R);"
                "const receivers=ring.filter(i=>{const t=q.g[i];"
                "return !!t&&t.side==='p'&&!t.support&&t.n<=th;});"
                "let budget=siteBudget(q);"
                "const cands=ring.filter(j=>{const u=q.g[j];return !!u&&u.side==='n'&&u.n<=th;})"
                ".sort((a,b)=>dist2(s,a)-dist2(s,b)||a-b);"
                "for(const j of cands){if(budget<=0)break;const u=q.g[j];"
                "if(!u||u.side!=='n')continue;"
                "let recv=-1,bestD=Infinity;"
                "for(const i of receivers){const d=dist2(i,j);"
                "if(d<bestD||(d===bestD&&i<recv)){bestD=d;recv=i;}}"
                "if(recv<0&&!site.support&&site.n<=th)recv=s;"
                "if(recv<0)continue;"
                "const v=u.n;q.g[j]=null;absorbed++;budget--;"
                "grown+=absorbValue(q,q.g[recv],v,lvCore);}}"
                "for(let i=0;i<N*N;i++){const t=q.g[i];"
                "if(!t||t.side!=='p'||t.support||t.n>th)continue;"
                "let used=0;"
                "for(const d in dirs){if(used>=tps||t.n>th)break;"
                "const j=neighbor(i,d);if(j<0)continue;const u=q.g[j];"
                "if(!u||u.side!=='n'||u.n>th)continue;"
                "const v=u.n;q.g[j]=null;absorbed++;used++;"
                "grown+=absorbValue(q,t,v,lvCore);}}"
                "grown+=settleTiles(q,lvCore);regenTiles(q);"
                "if(grown||absorbed)rescale(q);return grown;}"
            ),
            1, '吸收主流程重写：准入放宽到 <= 阈值，并在结算后跑回血', re.M)

# ============================================================ 敌方采集机：天花板 + 等比例继承
js = sub(js,
         'while(t.payload>=t.n&&Number.isFinite(t.n*2)){t.payload-=t.n;t.n*=2;'
         't.cap=3**lvl(t.n)*lvl(t.n);t.hp=t.cap;log(q,`采集机升级 · core=${t.n}`);}',
         'while(t.payload>=t.n&&t.n*2<=aiAbsorbCeiling(q)){t.payload-=t.n;'
         'const oldCap=t.cap||1,oldHp=t.hp??oldCap;t.n*=2;'
         't.cap=3**lvl(t.n)*lvl(t.n);'
         't.hp=Math.max(1,Math.min(t.cap,Math.round(oldHp*t.cap/oldCap)));'
         'log(q,`采集机升级 · core=${t.n}`);}',
         1, '敌方采集机：显式天花板 + 升级等比例继承血量')

# ============================================================ 受伤处记账
js = sub(js, 'q.g[target].hp-=dmg;', 'q.g[target].hp-=dmg;markCombat(q,q.g[target]);',
         1, '射击命中后记入战斗计数')
js = sub(js, 'b.hp=Math.max(0,bHP-aHP);',
         'b.hp=Math.max(0,bHP-aHP);markCombat(q,a);markCombat(q,b);',
         1, '血量对碰后记入战斗计数（双方）')

# ============================================================ 状态字段
js = sub(js, 'tech:0,upTp:0,upRadius:0,visited:null',
         'tech:0,upTp:0,upRadius:0,upThreshold:0,visited:null,combat:null',
         1, '新增状态字段：阈值等级、战斗计数')

# ============================================================ 科技树第三条线
js = sub(js, "function techLevel(q,line){return line==='tp'?(q.upTp||0):(q.upRadius||0);}",
         "function techLevel(q,line){return line==='tp'?(q.upTp||0):"
         "line==='radius'?(q.upRadius||0):(q.upThreshold||0);}",
         1, '科技树：等级读取支持第三条线')

js = sub(js, "function techMax(line){return line==='tp'?TECH_TP_MAX:TECH_RADIUS_MAX;}",
         "function techMax(line){return line==='tp'?TECH_TP_MAX:"
         "line==='radius'?TECH_RADIUS_MAX:TECH_THRESHOLD_MAX;}",
         1, '科技树：等级上限支持第三条线')

js = sub(js, "if(line==='tp')q.upTp=lv+1;else q.upRadius=lv+1;",
         "if(line==='tp')q.upTp=lv+1;else if(line==='radius')q.upRadius=lv+1;"
         "else q.upThreshold=lv+1;",
         1, '科技树：购买写入第三条线')

js = sub_re(js, r'^function techInfoAt\(line,lv\)\{.*\}$',
            lambda m: (
                "function techInfoAt(line,lv){"
                "if(line==='tp')return '每块每回合吸收 '+absorbTpAt(lv)+' 个';"
                "if(line==='radius'){const r=siteRadiusAt(lv);"
                "return '覆盖 '+((2*r+1)*(2*r+1)-1)+' 格 · 站点吞吐 '+siteBudgetAt(lv)+'/回合';}"
                "return '阈值 '+absorbThresholdAt(lv)+' · 可自动长到 '+(2*absorbThresholdAt(lv));}"
                "function techUI(){const t=$('tech');if(t)t.textContent=(s.tech||0)+' 点';"
                "const cb=$('convertScore');if(cb)cb.onclick=techConvert;"
                "const box=$('techTree');if(!box)return;"
                "const mk=(line,label)=>{const lv=techLevel(s,line),max=techMax(line),"
                "b=document.createElement('button');"
                "if(lv>=max){b.textContent=label+' '+lv+'/'+max+' · 已满级 · '+techInfoAt(line,lv);"
                "b.disabled=true;}"
                "else{const cost=techCost(line,lv);"
                "b.textContent=label+' '+lv+'/'+max+' · 升级 '+cost+' 点 · '+techInfoAt(line,lv)"
                "+' → '+techInfoAt(line,lv+1);b.disabled=(s.tech||0)<cost;}"
                "b.onclick=()=>techBuy(line);return b;};"
                "box.replaceChildren(mk('threshold','自动合成阈值'),mk('tp','吞吐 TP'),"
                "mk('radius','收集半径'));}"
            ),
            1, '科技树界面：加入阈值按钮并预告效果', re.M)

js_path.write_text(js, encoding='utf-8', newline='')
print('引擎已改写：%d 字符' % len(js))

# ============================================================ 玩家手册
g_path = SRC / 'guide.html'
guide = g_path.read_text(encoding='utf-8')

guide = sub(guide,
            '己方方块数字<strong>未达吸收上限（8）</strong>时，每回合自动吸收四向相邻的中立数字：'
            '中立消失，数值计入该方块的累积量；累积到当前数字即翻倍升级。'
            '升级后血量<strong>按比例保留，不回满</strong>。已达上限的方块不再吸收，只能靠推动或合并。',
            '己方方块数字<strong>不超过吸收阈值</strong>（基础 8）时，每回合自动吸收四向相邻的中立数字：'
            '中立消失，数值计入该方块的<strong>升级进度</strong>；进度攒够当前数字就翻倍升级。'
            '升级后若新数字仍不超过阈值，<strong>多出来的进度会继承</strong>；'
            '一旦升级后<strong>超过阈值，进度清零</strong>——所以不存在"数字超过阈值却还留着进度"的方块。'
            '超过阈值的方块不再吸收，只能靠推动或合并。'
            '升级只<strong>按比例继承血量</strong>，不会回满。',
            1, '玩家手册：吸收阈值规则')

guide = sub(guide, '半径内的中立会被吸给半径内最近的、仍未达上限的己方方块。',
            '半径内的中立会被吸给半径内最近的、数字仍未超过阈值的己方方块。',
            1, '玩家手册：半径归属措辞')

guide = sub(guide,
            '<p><strong>受伤即停长，转而恢复。</strong>方块满血时，累积量用于升级；'
            '一旦掉血，累积量就改为回血——每回合最多恢复上限的一成，成长暂停。'
            '这给防御赋予了经济意义：敌人不必打死你，打掉血就能让你的发育停下来。</p>',
            '<p><strong>受伤不影响成长，但影响恢复。</strong>方块血量上限的 <strong>5%</strong> 会在每回合自动回血，'
            '但必须<strong>脱离战斗满 10 回合</strong>才会开始——受伤即重新计时，且<strong>每个核心各算各的</strong>。'
            '所以被打退的一方恢复很慢，而脱离接触的一方回得快。</p>'
            '<p><strong>怎么读棋盘：</strong>方块<strong>背景颜色的高度</strong>表示剩余血量（剩一半血就只有下半有色）；'
            '方块下方那根细条是<strong>升级进度</strong>。进度条画成<strong>满格灰</strong>表示该方块已超过阈值、不再吸收。</p>',
            1, '玩家手册：回血规则与读图说明')

g_path.write_text(guide, encoding='utf-8', newline='')
print('玩家手册已更新：%d 字符' % len(guide))

# ============================================================ 无头工具导出
be = ROOT / 'tools' / 'build_engine.py'
txt = be.read_text(encoding='utf-8')
if "'regenTiles'" not in txt:
    txt = txt.replace("'techInfoAt',",
                      "'techInfoAt', 'absorbThreshold', 'absorbThresholdAt', 'aiAbsorbCeiling', "
                      "'regenTiles', 'markCombat',", 1)
    if "'regenTiles'" not in txt:
        fail('tools/build_engine.py：找不到导出锚点')
    be.write_text(txt, encoding='utf-8', newline='')
    applied.append('无头工具导出清单')
    print('无头工具导出清单已更新')

print()
print('本次应用改动 %d 项：' % len(applied))
for a in applied:
    print('  - %s' % a)
