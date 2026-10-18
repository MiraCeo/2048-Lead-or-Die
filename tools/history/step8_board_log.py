"""危险区改造：棋盘信息编码 + 战报只留重要事件。

按任务书评估后定的方案（我负责的部分）：

【棋盘信息编码】任务书只说"要有一份紧凑图例"，但没指出编码本身有问题：
  1. 进度条只有 20×2 像素 —— 太小的尺寸装不下"可数"的档位
  2. "不可吸收"用暗灰条，和"空进度"的暗轨道撞色
  3. 低血量时填充圆角比底色圆角小，底部两角会出现暗色缺口
修法：
  - 进度条 20×2 -> 22×4，轨道改成更深的底色（提高与填充的对比）
  - 加"档位刻度"：按 1/n 画分隔线，让 0/1/2/3/4 这种小整数进度可数
  - "不可吸收"改成明显更亮的满格灰（#7f8f7f）：仍是"满格灰"（按你的规格），
    但亮度比原来翻倍，不再和空条撞色
  - tileBody 改用画布裁剪：填充被裁进方块圆角内，低血缺口从根上消失

【战报】不是"信息重复"，是它已经被例行数据冲垮：
  worldStep 每回合写一行例行数据，而 log() 只留 12 条 —— 重要事件几条之内就被挤出去。
修法：
  - 例行回合行、每次血量对碰、每次额外操作、每次置换 -> 从战报摘掉
    （这些都已经在棋盘下方的即时反馈里）
  - 对碰只在"有方块被摧毁"时记；置换只在"触发分化"时记；敌机成长合并成一行
  - 保留上限 12 -> 30，让战报有历史可展开
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SRC = Path(r'D:\2048') / 'src'
p = SRC / 'main.script.js'
js = p.read_text(encoding='utf-8')
applied = []


def sub(old, new, n, label):
    global js
    c = js.count(old)
    if c != n:
        print('\n中止：%s：预期 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:200]))
        print('内存中已应用：%s' % (', '.join(applied) or '无'))
        print('注意：尚未写入文件。')
        sys.exit(1)
    js = js.replace(old, new)
    applied.append(label)
    print('已改：%s' % label)


# ============================================================ 1. tileBody 改用裁剪
sub("function tileBody(p,half,size,rad,fill,stroke,t){\n"
    "rect(p.x-half,p.y-half,size,size,rad,'#101a14',null);\n"
    "const h=Math.round(size*Math.max(0,Math.min(1,t.hp/t.cap)));\n"
    "if(h>0)rect(p.x-half,p.y+half-h,size,h,Math.min(rad,Math.floor(h/2)),fill,null);\n"
    "rect(p.x-half,p.y-half,size,size,rad,null,stroke);}\n",
    "function tileBody(p,half,size,rad,fill,stroke,t){\n"
    "ctx.save();ctx.beginPath();ctx.roundRect(p.x-half,p.y-half,size,size,rad);ctx.clip();\n"
    "ctx.fillStyle='#101a14';ctx.fillRect(p.x-half,p.y-half,size,size);\n"
    "const h=Math.round(size*Math.max(0,Math.min(1,t.hp/t.cap)));\n"
    "if(h>0){ctx.fillStyle=fill;ctx.fillRect(p.x-half,p.y+half-h,size,h);}\n"
    "ctx.restore();\n"
    "rect(p.x-half,p.y-half,size,size,rad,null,stroke);}\n",
    1, 'tileBody 改用画布裁剪（低血圆角缺口从根上消失）')

# ============================================================ 2. 进度条
# 注意：这段代码在被补丁覆盖的那一行里，必须保持"单行"形态，
# 否则会把那一行拆成多行、补丁锚点随之失效。
sub("if(t.side==='p'&&!t.support){const over=t.n>absorbThreshold(q);"
    "rect(p.x-10,p.y+9,20,2,1,over?'#4a5a4a':'#15231955');"
    "if(!over){const pr=Math.max(0,Math.min(1,(t.payload||0)/t.n));"
    "if(pr>0)rect(p.x-10,p.y+9,20*pr,2,1,'#c8f195');}}",
    "if(t.side==='p'&&!t.support){const th=absorbThreshold(q),bx=p.x-11,by=p.y+8,bw=22,bh=4;"
    "if(t.n>th){rect(bx,by,bw,bh,2,'#7f8f7f',null);}"
    "else{rect(bx,by,bw,bh,2,'#0d1512',null);"
    "const pr=Math.max(0,Math.min(1,(t.payload||0)/t.n));"
    "if(pr>0)rect(bx,by,Math.max(2,Math.round(bw*pr)),bh,2,'#c8f195',null);"
    "if(t.n<=8)for(let k=1;k<t.n;k++)rect(bx+Math.round(bw*k/t.n),by,1,bh,0,'#16321f',null);}}",
    1, '进度条加大 + 档位刻度 + 高对比满格灰')

# ============================================================ 3. 战报容量
sub('function log(q,t){q.logs.unshift(t);q.logs=q.logs.slice(0,12);}',
    'function log(q,t){q.logs.unshift(t);q.logs=q.logs.slice(0,30);}',
    1, '战报上限 12 -> 30（让重要事件有历史可展开）')

# ============================================================ 4. 对碰只在有摧毁时记
sub("neutralClusters(q);log(q,`血量对碰 ${Math.ceil(aHP)} ↔ ${Math.ceil(bHP)} · "
    "${aDead&&bDead?'双方消失':advanced?'进攻方存活并进入目标格':'防守方存活'}`);"
    "return{aHP,bHP,aDead,bDead,advanced};}",
    "neutralClusters(q);if(aDead||bDead)log(q,`血量对碰 · "
    "${aDead&&bDead?'双方消失':'一方被击破'}（${Math.ceil(aHP)} ↔ ${Math.ceil(bHP)}）`);"
    "return{aHP,bHP,aDead,bDead,advanced};}",
    1, '对碰：只在有方块被摧毁时进战报')

# ============================================================ 5. 摘掉例行回合行
sub("log(q,`回合 ${q.turn} · 射击 ${playerShots}/${enemyShots} · "
    "补给内${supply.inside}/外${supply.outside} · 行动点 +${earned}`);"
    "if(q.dead)log(q,'所有己方核心已失去，远征结束。');",
    "if(q.dead)log(q,'所有己方核心已失去，远征结束。');",
    1, '摘掉每回合的例行战报行（即时反馈里已有）')

# ============================================================ 6. 摘掉额外操作行
sub("log(q,info+' · 行动点 −1，时间冻结');return{info,newId};}",
    "return{info,newId};}",
    1, '摘掉每次额外操作的战报行')

# ============================================================ 7. 置换只在分化时记
sub("log(q,`两块位置互换 · 行动点 −1 · 分化 ${splits} 个核心 · 世界冻结`);return{splits};}",
    "if(splits)log(q,`两块位置互换触发分化 · ${splits} 个新核心`);return{splits};}",
    1, '置换：只在触发分化时进战报')

# ============================================================ 8. 敌机成长合并成一行
sub("function growFighters(q){let count=0;for(const t of q.g){"
    "if(!t?.core||t.side!=='e'||t.kind!=='fighter')continue;"
    "if(t.nextGrowth===undefined)t.nextGrowth=q.turn+40;"
    "if(q.turn>=t.nextGrowth){t.n*=2;t.nextGrowth+=40;count++;"
    "log(q,`敌机成长 · core=${fmt(t.n)}`);}}"
    "if(count)rescale(q);return count;}",
    "function growFighters(q){let count=0,top=0;for(const t of q.g){"
    "if(!t?.core||t.side!=='e'||t.kind!=='fighter')continue;"
    "if(t.nextGrowth===undefined)t.nextGrowth=q.turn+40;"
    "if(q.turn>=t.nextGrowth){t.n*=2;t.nextGrowth+=40;count++;"
    "if(t.n>top)top=t.n;}}"
    "if(count){log(q,`敌机成长 · ${count} 架核心翻倍（最高 ${fmt(top)}）`);rescale(q);}"
    "return count;}",
    1, '敌机成长合并成一行')

p.write_text(js, encoding='utf-8', newline='')
print()
print('引擎已改写：%d 字符' % len(js))
print('本次应用 %d 项' % len(applied))
