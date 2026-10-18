"""动效（§9）：吸收 / 被攻击 / 摧毁，外加升级脉冲与恢复完成。

设计要点 —— 通道怎么走：
  吸收与结算发生在 worldStep 内部，而 fx 数组原本在它们之后才创建；
  更要紧的是**敌方 AI 与操作预览都会用副本模拟 moveMain**，
  若动效事件走全局缓冲，那些模拟会产生大量幽灵特效。

  所以：**把 fx 显式往下传**。真实调用带 fx，模拟调用不带 —— 没有 fx 就不产生特效，
  不需要任何"是否在模拟"的标志位。
    moveMain(q,dir,id,fx) -> push() -> contact(q,i,j,fx) -> kill(q,i,fx)
    fire(q,side,fx,...) 已经带 fx，补上命中与击毁
    autoCollect(q,fx) / settleTiles(q,lvCore,fx) / regenTiles(q,fx) 新增 fx 参数
  三个函数的新参数都是可选的，所以现有的无头测试调用方式不受影响。

特效种类：shot（原有弹道）/ absorb / pulse / hit / kill / regen
  - 每种有自己的时长，draw() 里按种类过滤，frame() 仍然只在有特效时重绘（不新增循环）
  - "回血"只在**回满血那一刻**放一次特效：每回合给每个受伤方块都放环会变成常驻闪烁，
    那是噪声不是反馈。

注意：§9 当初写的是"回血时血条有回涨提示"，但之后展示层改过——血量已经是
方块的背景高度、细条已改成升级进度条，所以这里对应改成"方块上的恢复脉冲"。
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


def sub(text, old, new, n, label):
    c = text.count(old)
    if c != n:
        print('\n中止：%s：预期 %d 次，实际 %d 次\n  锚点：%r' % (label, n, c, old[:220]))
        print('内存中已应用：%s' % (', '.join(applied) or '无'))
        print('注意：尚未写入任何文件。')
        sys.exit(1)
    applied.append(label)
    print('已改：%s' % label)
    return text.replace(old, new)


js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')

# ==================================================== 通道：把 fx 传下去
js = sub(js, 'function moveMain(q,dir,id=q.active){', 'function moveMain(q,dir,id=q.active,fx){',
         1, 'moveMain 接收 fx')
js = sub(js, 'const clash=contact(q,i,j);if(clash){', 'const clash=contact(q,i,j,fx);if(clash){',
         1, 'push() 把 fx 传给 contact')

js = sub(js, 'function contact(q,i,j){', 'function contact(q,i,j,fx){',
         1, 'contact 接收 fx')
js = sub(js, 'b.hp=Math.max(0,bHP-aHP);markCombat(q,a);markCombat(q,b);if(bDead)kill(q,j);if(aDead)kill(q,i);',
         "b.hp=Math.max(0,bHP-aHP);markCombat(q,a);markCombat(q,b);"
         "if(fx){fx.push({kind:'hit',at:i,dmg:Math.ceil(bHP)});fx.push({kind:'hit',at:j,dmg:Math.ceil(aHP)});}"
         "if(bDead)kill(q,j,fx);if(aDead)kill(q,i,fx);",
         1, '对碰：两侧各出一个受击特效，并把 fx 传给 kill')

js = sub(js, 'function kill(q,i){const t=q.g[i];if(!t)return;',
         "function kill(q,i,fx){const t=q.g[i];if(!t)return;if(fx)fx.push({kind:'kill',at:i});",
         1, 'kill 发出摧毁特效')

js = sub(js, 'const dmg=damage(q,a);q.g[target].hp-=dmg;markCombat(q,q.g[target]);fx.push({from:i,to:target,side});',
         "const dmg=damage(q,a);q.g[target].hp-=dmg;markCombat(q,q.g[target]);"
         "fx.push({from:i,to:target,side});fx.push({kind:'hit',at:target,dmg:dmg});",
         1, '射击命中发出受击特效')
js = sub(js, 'if(q.g[target].hp<=0)kill(q,target);', 'if(q.g[target].hp<=0)kill(q,target,fx);',
         1, '射击击毁把 fx 传给 kill')

# ==================================================== 吸收 / 升级 / 恢复
js = sub(js, 'function autoCollect(q){', 'function autoCollect(q,fx){',
         1, 'autoCollect 接收 fx')
js = sub(js, "const v=u.n;q.g[j]=null;absorbed++;budget--;grown+=absorbValue(q,q.g[recv],v,lvCore);}}",
         "const v=u.n;q.g[j]=null;absorbed++;budget--;"
         "if(fx)fx.push({kind:'absorb',from:j,to:recv});"
         "grown+=absorbValue(q,q.g[recv],v,lvCore);}}",
         1, '半径收集发出吸收特效')
js = sub(js, "const v=u.n;q.g[j]=null;absorbed++;used++;grown+=absorbValue(q,t,v,lvCore);}}",
         "const v=u.n;q.g[j]=null;absorbed++;used++;"
         "if(fx)fx.push({kind:'absorb',from:j,to:i});"
         "grown+=absorbValue(q,t,v,lvCore);}}",
         1, '贴身吸收发出吸收特效')
js = sub(js, 'grown+=settleTiles(q,lvCore);regenTiles(q);',
         'grown+=settleTiles(q,lvCore,fx);regenTiles(q,fx);',
         1, '结算与回血也接收 fx')

js = sub(js, 'function settleTiles(q,lvCore){', 'function settleTiles(q,lvCore,fx){',
         1, 'settleTiles 接收 fx')
js = sub(js, "t.hp=Math.max(1,Math.min(t.cap,Math.round(oldHp*t.cap/oldCap)));grown++;",
         "t.hp=Math.max(1,Math.min(t.cap,Math.round(oldHp*t.cap/oldCap)));grown++;"
         "if(fx)fx.push({kind:'pulse',at:i});",
         1, '升级发出脉冲')

js = sub(js, 'function regenTiles(q){', 'function regenTiles(q,fx){',
         1, 'regenTiles 接收 fx')
js = sub(js, 't.hp=Math.min(t.cap,t.hp+amt);healed++;}',
         "t.hp=Math.min(t.cap,t.hp+amt);healed++;"
         "if(t.hp>=t.cap&&fx)fx.push({kind:'regen',at:i});}",
         1, '回满血那一刻发出恢复特效')

# ==================================================== extraStep 也带 fx
js = sub(js, "if(b?.side==='e'){const clash=contact(q,i,j);q.ap--;",
         "if(b?.side==='e'){const efx=[];const clash=contact(q,i,j,efx);q.ap--;",
         1, 'extraStep 也为对碰准备 fx')
js = sub(js, "' · 行动点 −1',newId:clash.aDead?null:id};}",
         "' · 行动点 −1',newId:clash.aDead?null:id,fx:efx};}",
         1, 'extraStep 把特效随返回值带出')

# ==================================================== worldStep：fx 提前创建
js = sub(js, 'function worldStep(q,dir){if(q.dead||q.settled)return null;const r=moveMain(q,dir);if(!r)return null;'
             'q.turn++;const earned=q.turn%2===0?1:0;q.ap+=earned;if(!q.dead)autoCollect(q);'
             'if(!q.dead)growFighters(q);const fx=[];const playerShots=fire(q,\'p\',fx);',
         'function worldStep(q,dir){if(q.dead||q.settled)return null;const fx=[];'
         'const r=moveMain(q,dir,q.active,fx);if(!r)return null;'
         'q.turn++;const earned=q.turn%2===0?1:0;q.ap+=earned;if(!q.dead)autoCollect(q,fx);'
         'if(!q.dead)growFighters(q);const playerShots=fire(q,\'p\',fx);',
         1, 'worldStep：fx 提前创建，并传给移动与吸收')

# ==================================================== actUnsafe：额外操作也出特效
js = sub(js, 'remember();s=draft;selected=r.newId;effects=[];say(r.info+',
         'remember();s=draft;selected=r.newId;'
         'effects=(r.fx||[]).map(f=>({...f,start:performance.now()}));say(r.info+',
         1, '额外操作的特效也接上')

# ==================================================== draw：渲染各类特效
OLD_FX = ("const now=performance.now();effects=effects.filter(f=>now-f.start<450);if(!preview){"
          "ctx.save();ctx.beginPath();ctx.rect(X,Y,800,800);ctx.clip();for(const f of effects){"
          "if(!visible(f.from,cam)&&!visible(f.to,cam))continue;"
          "const a=screenPoint(f.from,cam),b=screenPoint(f.to,cam);"
          "ctx.globalAlpha=(1-(now-f.start)/450)*.8;"
          "ctx.strokeStyle=f.side==='e'?'#ff9879':'#d6ef9a';ctx.lineWidth=1.5;"
          "ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}ctx.restore();}")

NEW_FX = (
    "const now=performance.now(),DUR={shot:450,absorb:420,pulse:480,hit:600,kill:520,regen:640};"
    "effects=effects.filter(f=>now-f.start<(DUR[f.kind||'shot']||450));"
    "if(!preview){ctx.save();ctx.beginPath();ctx.rect(X,Y-18,800,818);ctx.clip();"
    "for(const f of effects){const k=f.kind||'shot',age=Math.min(1,(now-f.start)/(DUR[k]||450)),fade=1-age;"
    "if(k==='shot'){if(!visible(f.from,cam)&&!visible(f.to,cam))continue;"
    "const a=screenPoint(f.from,cam),b=screenPoint(f.to,cam);"
    "ctx.globalAlpha=fade*.8;ctx.strokeStyle=f.side==='e'?'#ff9879':'#d6ef9a';ctx.lineWidth=1.5;"
    "ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();continue;}"
    "if(!visible(f.at,cam))continue;const p=screenPoint(f.at,cam);"
    "if(k==='absorb'){const o=screenPoint(f.from,cam);"
    "ctx.globalAlpha=fade*.8;ctx.strokeStyle='#c8f195';ctx.lineWidth=2;"
    "ctx.beginPath();ctx.moveTo(o.x,o.y);ctx.lineTo(p.x,p.y);ctx.stroke();"
    "ctx.globalAlpha=fade;ctx.fillStyle='#e6ff9c';ctx.beginPath();"
    "ctx.arc(o.x+(p.x-o.x)*age,o.y+(p.y-o.y)*age,2.5,0,6.2832);ctx.fill();}"
    "else if(k==='pulse'){ctx.globalAlpha=fade*.9;ctx.strokeStyle='#e6ff9c';ctx.lineWidth=2;"
    "ctx.beginPath();ctx.arc(p.x,p.y,6+18*age,0,6.2832);ctx.stroke();}"
    "else if(k==='regen'){ctx.globalAlpha=fade*.7;ctx.strokeStyle='#8fd98a';ctx.lineWidth=2;"
    "ctx.beginPath();ctx.arc(p.x,p.y,10+12*age,0,6.2832);ctx.stroke();}"
    "else if(k==='hit'){ctx.globalAlpha=fade*.75;ctx.fillStyle='#ff6b5a';"
    "ctx.beginPath();ctx.arc(p.x,p.y,13,0,6.2832);ctx.fill();"
    "if(f.dmg){ctx.globalAlpha=fade;text('-'+f.dmg,p.x,p.y-16-14*age,10,'#ffd7cf');}}"
    "else if(k==='kill'){ctx.globalAlpha=fade*.9;ctx.strokeStyle='#c9d3c3';ctx.lineWidth=2;"
    "ctx.beginPath();ctx.arc(p.x,p.y,8+22*age,0,6.2832);ctx.stroke();"
    "ctx.globalAlpha=fade*.55;ctx.strokeStyle='#e8f0dd';ctx.lineWidth=1.5;"
    "ctx.beginPath();ctx.moveTo(p.x-9,p.y-9);ctx.lineTo(p.x+9,p.y+9);"
    "ctx.moveTo(p.x+9,p.y-9);ctx.lineTo(p.x-9,p.y+9);ctx.stroke();}"
    "}ctx.globalAlpha=1;ctx.restore();}")

js = sub(js, OLD_FX, NEW_FX, 1, 'draw 渲染六类特效（按种类各自计时）')

js_path.write_text(js, encoding='utf-8', newline='')
print()
print('引擎已改写：%d 字符' % len(js))
print('本次应用 %d 项' % len(applied))
