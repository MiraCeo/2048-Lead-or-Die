// 修正吸收时序：移动 → 吸收 → 己方射击 → 敌方行动（吸收紧贴移动，且仍在挨打之前）
const fs = require('fs');
const vm = require('vm');

const HEAL = process.argv[2] !== 'keep';
const SEED = 20261017;
const MAX = Number(process.argv[3] || 700);
const CAP = 8, TP = 2;

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

function bootEngine(disableGroups) {
  let js = fs.readFileSync(__dirname + '/core-fleet.engine.js', 'utf8');
  if (disableGroups) {
    const start = js.indexOf('function neutralGroups(q){');
    let i = js.indexOf('{', start), depth = 0, end = -1;
    for (let k = i; k < js.length; k++) {
      if (js[k] === '{') depth++;
      else if (js[k] === '}') { depth--; if (depth === 0) { end = k; break; } }
    }
    js = js.slice(0, start) + 'function neutralGroups(q){return 0;}' + js.slice(end + 1);
  }
  const sandbox = {
    document: makeStub(), window: makeStub(), requestAnimationFrame: () => 0,
    TextDecoder, atob, btoa, console, performance,
  };
  const store = new Map();
  sandbox.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(js, sandbox);
  return sandbox.__CF__;
}

const DIRS = ['up', 'down', 'left', 'right'];
const OFF = [[-1, 0], [1, 0], [0, -1], [0, 1]];
const coreIdx = (G, q) => q.g.findIndex((t) => t && t.core && t.id === q.active);

// 吸收：n<cap 的己方方块吃四向相邻中立，累积到阈值翻倍
function autoCollect(G, q) {
  let grown = 0, eaten = 0;
  const lvCore = G.lvl(G.sharedCore(q));
  for (let i = 0; i < 10000; i++) {
    const t = q.g[i];
    if (!t || t.side !== 'p' || t.support || t.n >= CAP) continue;
    let used = 0;
    const r = Math.floor(i / 100), c = i % 100;
    for (const [dr, dc] of OFF) {
      if (used >= TP || t.n >= CAP) break;
      const rr = r + dr, cc = c + dc;
      if (rr < 0 || rr >= 100 || cc < 0 || cc >= 100) continue;
      const j = rr * 100 + cc, u = q.g[j];
      if (!u || u.side !== 'n' || u.n > CAP) continue;
      const hp0 = t.hp, cap0 = t.cap;
      t.payload = (t.payload || 0) + u.n;
      q.g[j] = null; eaten++; used++;
      while (t.payload >= t.n && t.n * 2 <= CAP) {
        t.payload -= t.n;
        t.n *= 2;
        t.cap = 3 ** G.lvl(t.n) * lvCore;
        t.hp = HEAL ? t.cap : Math.max(1, Math.ceil(hp0 / Math.max(1, cap0) * t.cap));
        grown++;
      }
      if (t.payload < t.n) break;
    }
  }
  if (grown) G.rescale(q);   // 与引擎 collect() 一致：吸收后重算全场 cap / hp
  return { grown, eaten };
}

// 复刻 worldStep，把吸收插在 moveMain 之后、射击之前
function stepWithCollect(G, q, dir) {
  if (q.dead || q.settled) return null;
  const r = G.moveMain(q, dir);
  if (!r) return null;
  q.turn++;
  const earned = q.turn % 2 === 0 ? 1 : 0;
  q.ap += earned;
  if (!q.dead) G.growFighters(q);
  const col = autoCollect(G, q);                    // ← 移动后立即吸收
  const fx = [];
  const playerShots = G.fire(q, 'p', fx);
  let enemyShots = 0, enemyMoves = 0;
  if (!q.dead && q.turn % 2 === 0) enemyMoves = G.ai(q);
  if (!q.dead) enemyShots = G.fire(q, 'e', fx, (t) => q.turn % 2 === 0 || G.teamCore(q, t.team)?.kind === 'bunker');
  let supply = { inside: 0, outside: 0 };
  if (!q.dead) {
    G.normalize(q);
    if (q.turn % 10 === 0) G.replenish(q);
    if (q.turn === q.nextWave) G.reinforce(q);
    if (q.turn >= (q.nextSupport ?? 20)) { G.spawnSupport(q); q.nextSupport = q.turn + 20; }
    supply = G.spawn(q);
    const ci = coreIdx(G, q);
    if (ci >= 0) q.lastFocus = ci;
  }
  return { ...r, earned, playerShots, enemyShots, enemyMoves, supply, col };
}

function spendAP(G, q, budget) {
  let used = 0;
  for (let k = 0; k < budget; k++) {
    if (q.ap < 1) break;
    const ids = q.g.filter((t) => t && t.side === 'p' && !t.core && !t.support).map((t) => t.id);
    let found = null;
    for (const id of ids) {
      for (const d of DIRS) {
        const draft = G.copy(q);
        const rr = G.extraStep(draft, id, d);
        if (rr.error) continue;
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

function chooseDir(G, q) {
  const targets = [];
  q.g.forEach((t, i) => { if (t && t.side === 'n') targets.push(i); });
  q.g.forEach((t, i) => { if (t && t.side === 'e') targets.push(i); });
  if (!targets.length) return null;
  let pick = null;
  for (const d of DIRS) {
    const draft = G.copy(q);
    const rr = G.moveMain(draft, d);
    if (!rr) continue;
    const di = coreIdx(G, draft);
    const dist = di >= 0 ? Math.min(...targets.map((t) => Math.sqrt(G.dist2(di, t)))) : 99;
    const score = rr.merges * 10 + rr.recruited * 4 - dist * 0.6 + (rr.contacts || 0);
    if (!pick || score > pick.score) pick = { d, score };
  }
  return pick;
}

const G = bootEngine(true);
console.log(`=== 时序修正版：移动 → 吸收 → 射击 → 敌方行动 ｜ cap=${CAP} 吞吐=${TP} 回血=${HEAL} ===`);
console.log('（对照：play6 移动→射击→敌方→吸收 = 694 回合 / 峰值 16384 / T680 达成 2048）\n');

let q = G.initial(SEED);
let grown = 0, eaten = 0, apUsed = 0, peak = 2, peakTurn = 0, first2048 = null, maxMembers = 0;
const t0 = Date.now();
for (let step = 0; step < MAX; step++) {
  if (q.dead || q.settled) break;
  apUsed += spendAP(G, q, 12);
  const pick = chooseDir(G, q);
  let r = null, dir = null;
  if (pick) { dir = pick.d; r = stepWithCollect(G, q, dir); }
  if (!r) {
    for (const d of DIRS) { if (d === dir) continue; r = stepWithCollect(G, q, d); if (r) { dir = d; break; } }
  }
  if (!r) break;
  grown += r.col.grown; eaten += r.col.eaten;
  const members = q.g.filter((t) => t && t.side === 'p' && !t.support).length;
  if (members > maxMembers) maxMembers = members;
  const best = Math.max(2, ...q.g.filter((t) => t && t.side === 'p' && !t.support).map((t) => t.n));
  if (best > peak) { peak = best; peakTurn = q.turn; }
  if (first2048 === null && best >= 2048) first2048 = q.turn;
  if (q.turn % 100 === 0) {
    console.log(`  T${String(q.turn).padStart(4)} 最高${String(best).padStart(5)} 成员${String(members).padStart(3)} 共享core${String(G.sharedCore(q)).padStart(4)} 吸收${grown}/${eaten} AP${q.ap}`);
  }
}
console.log(`\n结束 ${q.turn} 回合 ${q.dead ? '阵亡' : '存活'} · 峰值 ${peak}(T${peakTurn}) · 首达2048 ${first2048 ?? '未达成'} · 成员峰值 ${maxMembers} · 吸收 ${grown}/${eaten} · AP ${apUsed} · ${((Date.now() - t0) / 1000).toFixed(0)}s`);
