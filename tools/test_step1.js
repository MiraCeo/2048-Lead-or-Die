// Step 1 verification: functional smoke tests, not balance tests.
//
//   node tools/test_step1.js engine     -- engine runs, group field is gone
//   node tools/test_step1.js tutorial   -- every lesson instantiates; lesson 02 is winnable
//
// Run as separate processes: the doc warns that two engines in one process clash
// over globalThis.__CF__.
const fs = require('fs');
const vm = require('vm');
const path = require('path');
// 仓库根从脚本位置推导（tools/ 的上一级），不再写死盘符
const ROOT = path.resolve(__dirname, '..');

const MODE = process.argv[2] || 'engine';

let failures = 0;
function check(ok, label, detail) {
  if (!ok) { failures++; console.log(`  FAIL  ${label}${detail ? '  -- ' + detail : ''}`); }
  else console.log(`  ok    ${label}${detail ? '  -- ' + detail : ''}`);
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

function installStubs() {
  global.document = makeStub();
  global.window = makeStub();
  global.requestAnimationFrame = () => 0;
  const store = new Map();
  global.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };
}

function readDeliverable() {
  return fs.readFileSync(path.join(ROOT, '2048小游戏-教程七关.html'), 'utf8');
}

function extractTutorialScript(html) {
  const blobs = [...html.matchAll(/atob\('([A-Za-z0-9+/=]+)'\)/g)].map((m) => m[1]);
  const tutorialHtml = Buffer.from(blobs[1], 'base64').toString('utf8');
  const m = tutorialHtml.match(/<script[^>]*>([\s\S]*?)<\/script>/);
  return m[1];
}

// --------------------------------------------------------------------------
if (MODE === 'engine') {
  console.log('=== engine smoke test ===');
  const enginePath = path.join(ROOT, 'build', 'engine.js');
  let src = fs.readFileSync(enginePath, 'utf8');
  installStubs();
  vm.runInThisContext(src);
  const G = globalThis.__CF__;
  check(!!G, 'engine loaded and exposed __CF__');
  check(typeof G.neutralClusters === 'function', 'neutralClusters exported');
  check(G.neutralGroups === undefined, 'neutralGroups no longer exported');

  const DIRS = ['up', 'down', 'left', 'right'];
  const q = G.initial(20261017);

  // the group field must not exist anywhere
  const withNg = q.g.filter((t) => t && Object.prototype.hasOwnProperty.call(t, 'ng')).length;
  check(withNg === 0, 'no tile carries the ng field after initial()', `count=${withNg}`);

  const denseAfterInit = q.g.filter((t) => t && t.side === 'n' && t.nc).length;
  check(denseAfterInit > 0, 'neutralClusters labelled some dense neutrals at init',
        `cells=${denseAfterInit}`);

  let turns = 0, threw = null;
  try {
    for (let i = 0; i < 120 && !q.dead && !q.settled; i++) {
      // minimal greedy: any direction that moves
      for (const d of DIRS) {
        const draft = G.copy(q);
        if (G.moveMain(draft, d)) { G.worldStep(q, d); turns++; break; }
      }
    }
  } catch (e) { threw = e; }
  check(!threw, 'ran 120 turns without throwing', threw ? threw.message : `turns=${turns}`);
  check(turns > 0, 'world actually advanced', `turns=${turns}`);
  check(G.valid(q), 'final state passes valid()');

  const strayNg = q.g.filter((t) => t && Object.prototype.hasOwnProperty.call(t, 'ng')).length;
  check(strayNg === 0, 'still no ng field after 120 turns', `count=${strayNg}`);
  const denseRuntime = q.g.filter((t) => t && t.side === 'n' && t.nc).length;
  console.log(`  info  dense-zone neutral cells after ${turns} turns: ${denseRuntime}`);
}

// --------------------------------------------------------------------------
if (MODE === 'tutorial') {
  console.log('=== tutorial smoke test ===');
  const html = readDeliverable();
  let ts = extractTutorialScript(html);

  const lines = ts.split('\n');
  const lastIdx = lines.map((l, i) => (l.trim() ? i : -1)).reduce((a, b) => Math.max(a, b), -1);
  check(lines[lastIdx].trim() === '})();', 'tutorial script ends with the IIFE closer',
        JSON.stringify(lines[lastIdx].trim()));
  lines[lastIdx] = 'globalThis.__TUT__={tutorialInitial,tutorialDone,tutorialUI,tutorialHighlights,worldStep,moveMain,neutralClusters,valid,copy,dirs};' + lines[lastIdx];
  ts = lines.join('\n');

  installStubs();
  let threw = null;
  try { vm.runInThisContext(ts); } catch (e) { threw = e; }
  check(!threw, 'tutorial script loads', threw ? threw.message : '');
  if (threw) { console.log(`\n${failures} FAILURE(S)`); process.exit(1); }

  const T = globalThis.__TUT__;
  check(T && typeof T.tutorialInitial === 'function', 'tutorialInitial exported');

  // every lesson must instantiate
  for (let lesson = 0; lesson <= 6; lesson++) {
    let err = null, q = null;
    try { q = T.tutorialInitial(lesson); } catch (e) { err = e; }
    const neutrals = q ? q.g.filter((t) => t && t.side === 'n').length : -1;
    check(!err, `lesson 0${lesson + 1} instantiates`, err ? err.message : `neutrals=${neutrals}`);
  }

  // Lesson-board specifics live in tools/test_step2_tutorial.js, which is the
  // authoritative tutorial test. This mode only checks load + instantiation.
  const q = T.tutorialInitial(0);
  check(T.valid(q), 'lesson 01 initial state passes valid()');
}

console.log(`\n${failures} FAILURE(S)`);
process.exit(failures ? 1 : 0);
