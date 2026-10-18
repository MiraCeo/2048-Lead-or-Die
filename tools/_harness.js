// 共享的无头对局基础设施：DOM 桩 + 引擎加载 + 确定性智能体。
//
// 为什么抽出来：这套代码原本在 `harness.js` / `trace.js` / `difftest.js` 里
// **各有一份**（前两个已随阶段 4 归档）。再给平衡基准写第四份是不可接受的 ——
// 一旦智能体实现出现细微分叉，"两个工具测的不是同一个玩家"，数据就没法互相印证。
//
// 口径说明（重要）：
//   · 智能体是**确定性贪心**，不追求"会玩"，只追求"固定"。平衡测量关心的是
//     "同一套打法下，引擎改动让结果往哪边走"，而不是绝对难度。
//   · `difftest.js` 用这套口径产出行为基线（总摘要 e8ebee9b）。
//     本文件的任何行为改动都会让它失配 —— 那正是它该起的作用。
'use strict';
const fs = require('fs');
const vm = require('vm');

const DIRS = ['up', 'down', 'left', 'right'];

/** DOM 桩：无头环境下页面元素全部是 Proxy，任何访问都返回一个新桩。 */
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

/**
 * 装上 DOM 桩并载入引擎，返回 `globalThis.__CF__`。
 * 一个进程只能载一份引擎（两份会互相覆盖 __CF__，见项目文档 §14.7）。
 */
const storage = new Map();

function loadEngine(enginePath) {
  global.document = makeStub();
  global.window = makeStub();
  global.requestAnimationFrame = () => 0;
  global.localStorage = {
    getItem: (k) => (storage.has(k) ? storage.get(k) : null),
    setItem: (k, v) => storage.set(k, String(v)),
    removeItem: (k) => storage.delete(k),
  };
  vm.runInThisContext(fs.readFileSync(enginePath, 'utf8'));
  const G = globalThis.__CF__;
  if (!G || typeof G.initial !== 'function' || typeof G.worldStep !== 'function') {
    console.error('引擎没有导出 initial/worldStep —— __CF__ 不完整');
    process.exit(2);
  }
  return G;
}

/** 清空 localStorage 桩。每局开始前调用，保证局与局之间不共享存档状态。 */
function clearStorage() {
  storage.clear();
}

/** 花行动点做单块调整，优先选择能让棋盘变少的走法。返回用掉几点。 */
function spendAP(G, q, budget) {
  let used = 0;
  for (let k = 0; k < budget; k++) {
    if (q.ap < 1) break;
    const ids = q.g.filter((t) => t && t.side === 'p' && !t.core && !t.support).map((t) => t.id);
    let found = null;
    for (const id of ids) {
      for (const d of DIRS) {
        const draft = G.copy(q);
        const r = G.extraStep(draft, id, d);
        if (r.error) continue;
        if (draft.g.filter(Boolean).length < q.g.filter(Boolean).length) { found = draft; break; }
      }
      if (found) break;
    }
    if (!found) break;
    Object.assign(q, found);
    used++;
  }
  return used;
}

/**
 * 贪心选方向：合并权重 10、收编 4、按距离轻微惩罚、对碰加分。
 * 返回 `{d, score}` 或 null。
 */
function chooseDir(G, q) {
  const targets = [];
  q.g.forEach((t, i) => { if (t && t.side === 'n') targets.push(i); });
  q.g.forEach((t, i) => { if (t && t.side === 'e') targets.push(i); });
  if (!targets.length) return null;
  let pick = null;
  for (const d of DIRS) {
    const draft = G.copy(q);
    const r = G.moveMain(draft, d);
    if (!r) continue;
    const di = draft.g.findIndex((t) => t && t.core && t.id === draft.active);
    const dist = di >= 0 ? Math.min(...targets.map((t) => Math.sqrt(G.dist2(di, t)))) : 99;
    const score = r.merges * 10 + r.recruited * 4 - dist * 0.6 + (r.contacts || 0);
    if (!pick || score > pick.score) pick = { d, score };
  }
  return pick;
}

/**
 * 跑一局。`onTurn` 可选，每回合结束后回调 `(q, info)`，用于采集指标。
 * 返回 `{q, turns, apUsed}`。
 */
function playGame(G, seed, maxTurns, opts) {
  const o = opts || {};
  const apBudget = o.apBudget === undefined ? 12 : o.apBudget;
  const q = G.initial(seed);
  let turns = 0;
  let apUsed = 0;
  if (o.onStart) o.onStart(q);
  for (let step = 0; step < maxTurns; step++) {
    if (q.dead || q.settled) break;
    apUsed += spendAP(G, q, apBudget);
    const pick = chooseDir(G, q);
    let r = null;
    let dir = null;
    if (pick) { dir = pick.d; r = G.worldStep(q, dir); }
    if (!r) {
      for (const d of DIRS) {
        if (d === dir) continue;
        r = G.worldStep(q, d);
        if (r) { dir = d; break; }
      }
    }
    if (!r) break;
    turns++;
    if (o.onTurn) o.onTurn(q, { dir, r });
  }
  return { q, turns, apUsed };
}

module.exports = { DIRS, makeStub, loadEngine, clearStorage, spendAP, chooseDir, playGame };
