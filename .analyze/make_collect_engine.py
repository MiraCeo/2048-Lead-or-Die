import re, os

SRC = r'D:\Hypergryph\模拟初筛\.analyze\core-fleet.engine.js'
OUT = r'D:\Hypergryph\模拟初筛\.analyze\core-fleet.engine.collect.js'

js = open(SRC, encoding='utf-8').read()

# 引擎内部版自动收集：n<CAP 的己方方块吸收四向中立，累积到阈值翻倍
AC = (
    "function __autoCollect(q){"
    "const CAP=8,TP=2,lvCore=lvl(sharedCore(q));let grown=0;"
    "for(let i=0;i<N*N;i++){"
    "const t=q.g[i];"
    "if(!t||t.side!=='p'||t.support||t.n>=CAP)continue;"
    "let used=0;"
    "for(const d in dirs){"
    "if(used>=TP||t.n>=CAP)break;"
    "const j=neighbor(i,d);if(j<0)continue;"
    "const u=q.g[j];"
    "if(!u||u.side!=='n'||u.n>CAP)continue;"
    "t.payload=(t.payload||0)+u.n;q.g[j]=null;used++;"
    "while(t.payload>=t.n&&t.n*2<=CAP){t.payload-=t.n;t.n*=2;t.cap=3**lvl(t.n)*lvCore;t.hp=t.cap;grown++;}"
    "if(t.payload<t.n)break;"
    "}}"
    "if(grown)rescale(q);"
    "return grown;}"
)

anchor_def = 'function worldStep(q,dir){'
assert js.count(anchor_def) == 1, 'worldStep 定义不唯一'
js = js.replace(anchor_def, AC + anchor_def, 1)

anchor_call = 'if(!q.dead)growFighters(q);'
assert js.count(anchor_call) == 1, 'growFighters 调用点不唯一'
js = js.replace(anchor_call, anchor_call + 'if(!q.dead)__autoCollect(q);', 1)

# 导出以便外部统计
js = js.replace('growFighters,extraStep};', 'growFighters,extraStep,__autoCollect};', 1)

open(OUT, 'w', encoding='utf-8').write(js)
print('written', OUT, len(js), 'bytes')
print('insert def at', js.find(AC[:40]))
print('insert call at', js.find('if(!q.dead)__autoCollect(q);'))
