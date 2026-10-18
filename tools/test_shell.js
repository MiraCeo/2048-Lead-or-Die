// 外壳结构与命名的验证。
//
//   node tools/test_shell.js
//
// 为什么需要这个：重构 markup 最容易悄悄弄坏的是「元素 id」。
// 而无头环境的 document 是 Proxy stub —— $('xxx') 永远返回一个假元素，
// 所以 id 掉了、测试也不会报错，只有真人打开浏览器才会发现界面空了。
// 这里直接把「引擎引用的 id」与「交付文件里真实存在的 id」对起来。
const fs = require('fs');
const vm = require('vm');

let failures = 0;
function check(ok, label, detail) {
  if (!ok) { failures++; console.log(`  失败  ${label}${detail ? '  -- ' + detail : ''}`); }
  else console.log(`  通过  ${label}${detail ? '  -- ' + detail : ''}`);
}

function makeStub() {
  const f = function () {};
  return new Proxy(f, {
    get(t, k) {
      if (k === 'then') return undefined;
      if (k === Symbol.toPrimitive) return () => '';
      if (k === Symbol.iterator) return function* () {};
      if (k === 'toString' || k === 'valueOf') return () => '';
      if (k === 'length') return 0;
      if (!(k in t)) t[k] = makeStub();
      return t[k];
    },
    set() { return true; },
    apply() { return makeStub(); },
    construct() { return makeStub(); },
  });
}
global.document = makeStub();
global.window = makeStub();
global.requestAnimationFrame = () => 0;
const store = new Map();
global.localStorage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };

const ENGINE = fs.readFileSync('D:\\2048\\build\\engine.js', 'utf8');
vm.runInThisContext(ENGINE);
const HTML = fs.readFileSync('D:\\2048\\2048小游戏-教程七关.html', 'utf8');

// 介绍页是 base64 嵌在交付文件里的，解出来才能验"规则真的搬过去了"
function embeddedGuide() {
  const m = HTML.match(/atob\('([A-Za-z0-9+/=]+)'\)/);
  return m ? Buffer.from(m[1], 'base64').toString('utf8') : '';
}
const GUIDE = embeddedGuide();

console.log('\n=== 引擎引用的元素 id 是否都真的存在（最关键）===');
{
  const wanted = new Set();
  for (const m of ENGINE.matchAll(/\$\(['"]([A-Za-z0-9_-]+)['"]\)/g)) wanted.add(m[1]);
  const present = new Set();
  for (const m of HTML.matchAll(/id="([A-Za-z0-9_-]+)"/g)) present.add(m[1]);
  const missing = [...wanted].filter((id) => !present.has(id));
  check(missing.length === 0, `引擎引用的 ${wanted.size} 个 id 全部存在于交付文件`,
        missing.length ? '缺失：' + missing.join(', ') : '');
}

console.log('\n=== 关键 id 必须唯一 ===');
{
  for (const id of ['canvas', 'minimap', 'previewHint', 'feedback', 'inspect', 'log',
                    'tech', 'techTree', 'convertScore', 'fleets', 'gameOver',
                    'openTech', 'closeTech', 'techDialog']) {
    const n = (HTML.match(new RegExp(`id="${id}"`, 'g')) || []).length;
    check(n === 1, `#${id} 恰好出现一次`, `count=${n}`);
  }
}

console.log('\n=== 状态条改为不占位的临时浮层 ===');
{
  check(!HTML.includes('id="status"'), '常驻状态条已删除');
  check(HTML.includes('class="feedback"'), '临时浮层在场');
  check(HTML.includes('.feedback{position:absolute'), '浮层是绝对定位（不占布局空间）');
  check(ENGINE.includes("$('feedback')"), 'say() 已改到浮层');
  check(!ENGINE.includes("$('status')"), '旧的状态条引用已清除');
  const iHint = HTML.indexOf('id="previewHint"'), iCanvas = HTML.indexOf('id="canvas"');
  check(iHint > 0 && iCanvas > 0 && iHint < iCanvas, '预览结果位仍在棋盘之前');
}

console.log('\n=== 规则搬进游戏介绍 ===');
{
  check(GUIDE.includes('>画面与科技<'), '介绍页导航加入了新章节');
  check(GUIDE.includes('画面读法、小地图与科技点'), '介绍页含新章节标题');
  check(GUIDE.includes('整体轮廓'), '画布底部的轮廓说明已搬入介绍');
  check(GUIDE.includes('科技点'), '科技点来源已写入介绍');
  check(!ENGINE.includes('实心底色区分阵营'), '画布底部规则文字已从引擎移除');
  check(!ENGINE.includes('碉堡每回合射击'), '画布底部的射程/补给说明已移除');
  check(!HTML.includes('点击绿色核心标记切换视野'), '小地图提示不再常驻');
  check(HTML.includes('<div id="previewHint" class="mini-detail map-keyhint"></div>'),
        '棋盘上方的预览位默认是空的');
  check(ENGINE.includes("$('previewHint').textContent=''"),
        'clearPreview() 清空预览位，而不是把操作说明写回去');
}

console.log('\n=== 信息重复与命名 ===');
{
  check(!HTML.includes('class="badge">100 × 100 世界'), '顶部重复的世界／视野徽标已删除');
  check(HTML.includes('COMMAND / 当前控制核心'), '标题为「当前控制核心」');
  check(HTML.includes('全队共享 core'), '「全队共享 core」在场');
  check(HTML.includes('最高合成值'), '「最高合成值」在场');
  check(!HTML.includes('每2回合 +1'), '行动点固定规则不再常驻');
  check(!HTML.includes('补给：视野内每2回合 +1，视野外每回合 +3'), '战场面板重复的补给规则已删除');
  check(!HTML.includes('EXPLORATION · FORMATION'), '页脚装饰英文已改为中文');
  check(HTML.includes('font-size:11px;letter-spacing:0'),
        '面板标题字号已放大、字距已归零（否则长标题会折行）');
  check(!/h2\{[^}]*letter-spacing:1px/.test(HTML),
        'h2 规则里不再有 1px 字距（那会让标题多出约 18px）');
  check(/h2\{[^}]*letter-spacing:0/.test(HTML), 'h2 字距明确为 0');
}

console.log('\n=== 棋盘尺寸不再用魔法数字 ===');
{
  check(HTML.includes('max-height:calc(100dvh - var(--board-chrome,230px))'),
        '棋盘高度交给浏览器按可用空间算（开销是单个可调变量）');
  check(HTML.includes('.board canvas{width:auto;height:auto'), 'canvas 等比缩放（不再拉伸）');
}

console.log('\n=== 画布：去掉顶部标签与下方留空，坐标保留 ===');
{
  check(HTML.includes('id="canvas" width="860" height="860"'), '画布改为 860×860（下方不再留白）');
  check(!ENGINE.includes('EXPEDITION SECTOR'), '顶部左侧「100 × 100」标签已删');
  check(!ENGINE.includes('CORE-CENTERED VIEW'), '顶部右侧「25 × 25」标签已删');
  check(!ENGINE.includes('886'), '引擎里不再有任何 886（坐标映射全部跟进）');
  check(ENGINE.includes('text(cam.c+c+1') && ENGINE.includes('text(cam.r+c+1'),
        '棋盘四周的行列坐标仍然保留');
  check(ENGINE.includes("preview?'") === false, '画布不再自绘模式文字（顶栏 #modeLabel 已在显示）');
}

console.log('\n=== 科技面板：侧栏只留入口，详情在按需面板 ===');
{
  check(HTML.includes('<strong id="tech"></strong><span class="mini-detail">科技点</span></div>'
                      + '<button id="openTech">打开科技树</button>'),
        '侧栏只剩「余额 + 打开科技树」');
  check(HTML.includes('id="techDialog"'), '按需面板在场');
  check(HTML.includes('class="panel-dialog"'), '按需面板有独立样式');
  check(ENGINE.includes("row.className='tech-row'"),
        '列表改为行式渲染（名称/效果/按钮分开，不再挤进一个按钮标签）');
  const guards = (ENGINE.match(/\$\('techDialog'\)\.open/g) || []).length;
  check(guards >= 2, '面板打开时棋盘输入被拦住（鼠标与键盘各一处）', `guard=${guards}`);
  check(ENGINE.includes("$('openTech').onclick") && ENGINE.includes("$('closeTech').onclick"),
        '打开/关闭已接线');
}

console.log('\n=== 核心从血量配色中排除 ===');
{
  check(ENGINE.includes("if(t.side==='p'&&!t.core&&t.hp<t.cap)"), '核心不再参与血量配色');
}

console.log(`\n${failures} 项失败`);
process.exit(failures ? 1 : 0);
