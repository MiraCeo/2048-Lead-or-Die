"""精简科技点：侧栏只留余额 + 入口，详情移入按需面板。

设计判断（详见对话）：
  现在的 180px 侧栏装不下每项需要的 5 个字段（名称／等级／当前效果／升级后效果／花费），
  而 7 次购买也撑不起一个全屏界面。所以拆成两层：
    侧栏（常驻）= 科技点余额 + 一个入口按钮
    按需面板    = 每项一行：名称与等级、当前效果 → 升级后效果、升级按钮
  这个按需面板就是未来的科技树——内容从竖排清单长成带前置与分支的树时，容器不用换。

面板里每一项改成"两行文字 + 右侧按钮"，不再把全部信息挤进一个按钮标签里。

引擎侧：
  - techUI() 渲染结构改为行式；techUI 的调用点没动（在 ui() 里，被补丁覆盖）所以补丁不受影响
  - 打开/关闭的接线是新增行，不在补丁范围内
  - inputBlocked() 与 keydown 被补丁覆盖，加了 techDialog 判断，需要重新锚定
    （不加的话：面板开着按 WASD 仍会移动主体）
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


# ==================================================== 外壳
shell_path = SRC / 'main.shell.html'
sh = shell_path.read_text(encoding='utf-8')

sh = sub(sh,
         '<div class="panel"><h2>TECH / 科技点</h2><div class="inline-bank"><strong id="tech"></strong>'
         '<span class="mini-detail" style="cursor:help" '
         'title="击破敌方核心或碉堡、探索新区块、用合成分兑换">科技点</span></div>'
         '<div id="techTree" class="compact-list"></div>'
         '<button id="convertScore" title="每 100 积分兑换 1 点科技点，会消耗积分">兑换积分 → 科技点</button></div>',
         '<div class="panel"><h2>TECH / 科技点</h2><div class="inline-bank"><strong id="tech"></strong>'
         '<span class="mini-detail">科技点</span></div><button id="openTech">打开科技树</button></div>',
         1, '侧栏科技面板精简为「余额 + 入口」')

sh = sub(sh, '</footer></main>',
         '</footer>'
         '<dialog id="techDialog" class="panel-dialog" aria-label="科技树">'
         '<div class="panel-dialog-bar"><span>科技树 · 打开时世界时间冻结</span>'
         '<button id="closeTech">关闭 ✕</button></div>'
         '<div class="panel-dialog-body">'
         '<div class="mini-detail">科技点来源与机制见「游戏介绍」</div>'
         '<div id="techTree" class="tech-list"></div>'
         '<button id="convertScore" title="每 100 积分兑换 1 点科技点，会消耗积分">兑换积分 → 科技点</button>'
         '</div></dialog></main>',
         1, '新增按需面板 #techDialog（含科技列表与兑换）')

sh = sub(sh, '</style></head><body>',
         '/* 按需面板：科技树 */\n'
         '.panel-dialog{width:min(560px,92vw);max-height:88vh;padding:0;overflow:hidden;'
         'border:1px solid #55734c;border-radius:14px;background:#101918;color:#e5eddb}\n'
         '.panel-dialog::backdrop{background:#07100be8}\n'
         '.panel-dialog-bar{height:46px;display:flex;align-items:center;justify-content:space-between;'
         'padding:8px 16px;background:#1c2c21;border-bottom:1px solid #3b5036;font-size:12px}\n'
         '.panel-dialog-body{padding:16px;display:flex;flex-direction:column;gap:12px;overflow:auto;'
         'max-height:calc(88vh - 46px)}\n'
         '.tech-list{display:grid;gap:10px}\n'
         '.tech-row{display:flex;align-items:center;gap:12px;justify-content:space-between;'
         'border:1px solid #2c4036;border-radius:10px;padding:10px 12px;background:#16211c}\n'
         '.tech-info{display:flex;flex-direction:column;gap:4px;min-width:0}\n'
         '.tech-info strong{font-size:13px;color:#e0efcf}\n'
         '.tech-info span{font-size:11px;color:#9db18f;line-height:1.6}\n'
         '.tech-row button{flex-shrink:0}\n'
         '</style></head><body>',
         1, '新增按需面板的样式')

shell_path.write_text(sh, encoding='utf-8', newline='')
print('外壳已改写：%d 字符' % len(sh))

# ==================================================== 引擎
js_path = SRC / 'main.script.js'
js = js_path.read_text(encoding='utf-8')

# 打开/关闭接线（新增行，不在补丁范围内）
js = sub(js, 'function growFighters(q){',
         "function openTech(){const d=$('techDialog');if(d)d.showModal();}\n"
         "function closeTech(){const d=$('techDialog');if(d)d.close();"
         "if(canvas)canvas.focus({preventScroll:true});}\n"
         "$('openTech')&&($('openTech').onclick=openTech);\n"
         "$('closeTech')&&($('closeTech').onclick=closeTech);\n"
         "function growFighters(q){",
         1, '新增打开/关闭科技面板的接线')

# 列表改为「两行文字 + 右侧按钮」
js = re.sub(r'^function techInfoAt\(line,lv\)\{.*\}$',
            lambda m: (
                "function techInfoAt(line,lv){"
                "if(line==='tp')return '每块每回合吸收 '+absorbTpAt(lv)+' 个';"
                "if(line==='radius'){const r=siteRadiusAt(lv);"
                "return '覆盖 '+((2*r+1)*(2*r+1)-1)+' 格 · 站点吞吐 '+siteBudgetAt(lv)+'/回合';}"
                "return '阈值 '+absorbThresholdAt(lv)+' · 可自动长到 '+(2*absorbThresholdAt(lv));}"
                "function techUI(){const t=$('tech');if(t)t.textContent=(s.tech||0)+' 点';"
                "const cb=$('convertScore');if(cb)cb.onclick=techConvert;"
                "const box=$('techTree');if(!box)return;"
                "const mk=(line,label)=>{const lv=techLevel(s,line),max=techMax(line);"
                "const row=document.createElement('div');row.className='tech-row';"
                "const info=document.createElement('div');info.className='tech-info';"
                "const name=document.createElement('strong');name.textContent=label+' '+lv+' / '+max;"
                "const eff=document.createElement('span');"
                "const b=document.createElement('button');"
                "if(lv>=max){eff.textContent=techInfoAt(line,lv)+'（已满级）';"
                "b.textContent='已满级';b.disabled=true;}"
                "else{const cost=techCost(line,lv);"
                "eff.textContent=techInfoAt(line,lv)+' → '+techInfoAt(line,lv+1);"
                "b.textContent='升级 '+cost+' 点';b.disabled=(s.tech||0)<cost;}"
                "info.appendChild(name);info.appendChild(eff);"
                "b.onclick=()=>techBuy(line);"
                "row.appendChild(info);row.appendChild(b);return row;};"
                "box.replaceChildren(mk('threshold','自动合成阈值'),mk('tp','吸收吞吐'),"
                "mk('radius','收集半径'));}"
            ),
            js, count=1, flags=re.M)
applied.append('科技列表改为行式渲染（名称/效果/按钮分开）')
print('已改：科技列表改为行式渲染（名称/效果/按钮分开）')

# 面板开着时不能动棋盘
js = sub(js, "function inputBlocked(){return s.dead||s.settled||$('goalDialog').open||"
             "$('dialog').open||$('guideDialog').open||$('tutorialDialog').open;}",
         "function inputBlocked(){return s.dead||s.settled||$('goalDialog').open||"
         "$('dialog').open||$('guideDialog').open||$('tutorialDialog').open||$('techDialog').open;}",
         1, 'inputBlocked 也考虑科技面板')

js = sub(js, "window.addEventListener('keydown',e=>{if($('dialog').open||$('goalDialog').open||"
             "$('guideDialog').open||$('tutorialDialog').open||e.ctrlKey||e.altKey||e.metaKey)return;",
         "window.addEventListener('keydown',e=>{if($('dialog').open||$('goalDialog').open||"
         "$('guideDialog').open||$('tutorialDialog').open||$('techDialog').open||"
         "e.ctrlKey||e.altKey||e.metaKey)return;",
         1, '键盘守卫也考虑科技面板（否则面板开着按 WASD 仍会移动）')

js_path.write_text(js, encoding='utf-8', newline='')
print('引擎已改写：%d 字符' % len(js))

print()
print('本次应用 %d 项' % len(applied))
