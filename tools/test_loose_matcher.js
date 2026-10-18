// 自测：确认 test_fx 里的 hasLoose/stripParens 既**能命中**也**能失败**。
// 一个永远返回 true 的断言是负资产 —— 必须证明它会失败。
const fs = require('fs');

const _sq = (v) => String(v).replace(/\s+/g, '');

function stripParens(s) {
  const n = s.length;
  const matchClose = (openIdx) => {
    let d = 1;
    for (let k = openIdx + 1; k < n; k++) {
      const c = s[k];
      if (c === "'" || c === '"' || c === '`') {
        k++;
        while (k < n) {
          if (s[k] === '\\') { k += 2; continue; }
          if (s[k] === c) break;
          k++;
        }
        continue;
      }
      if (c === '(') d++;
      else if (c === ')') { d--; if (d === 0) return k; }
    }
    return -1;
  };
  let i = 0;
  while (i < n) {
    const c = s[i];
    if (c === "'" || c === '"' || c === '`') {
      i++;
      while (i < n) {
        if (s[i] === '\\') { i += 2; continue; }
        if (s[i] === c) { i++; break; }
        i++;
      }
      continue;
    }
    if (c === '(') {
      const j = matchClose(i);
      if (j > i) {
        const raw = s.slice(i + 1, j);
        // 只在括号内容**明显冗余**时才剥（保守白名单）。
        // 反例：`f('(a)')` 的括号属于函数调用，绝不能剥成 `f'(a)'`。
        const safe = raw !== '' &&
          !raw.includes(',') && !raw.includes(';') && raw !== ')' &&
          !(raw[0] === "'" || raw[0] === '"' || raw[0] === '`');
        if (safe) {
          const inner = stripParens(raw);
          s = s.slice(0, i) + inner + s.slice(j + 1);
          i += inner.length;
          continue;
        }
      }
    }
    i++;
  }
  return s;
}

const loose = (src, pat) => _sq(stripParens(src)).includes(_sq(stripParens(pat)));

// 仓库根从脚本位置推导，别依赖 CWD（本项目其它测试都这么做）
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const real = fs.readFileSync(path.join(ROOT, 'src', 'main.script.js'), 'utf8');
let fails = 0;
const ck = (ok, label) => { if (!ok) { fails++; console.log('  FAIL ' + label); } else console.log('  通过 ' + label); };

// 1. 真实模式必须命中
ck(loose(real, "effects=effects.filter(f=>now-f.start<(DUR[f.kind||'shot']||450))"),
   '真实（压缩写法）模式命中');
ck(loose(real, "effects = effects.filter((f) => now - f.start < (DUR[f.kind || 'shot'] || 450))"),
   '同一模式的格式化写法也命中');

// 2. 臆造模式必须**不**命中（否则 hasLoose 是"永远通过"）
ck(!loose(real, 'effects=effects.filterZZZ(f=>nope)'),
   '臆造模式不命中（证明断言会失败）');
ck(!loose(real, 'THIS_STRING_IS_NOT_IN_THE_ENGINE_AT_ALL'),
   '完全无关的字符串不命中');

// 3. 字符串内的括号不能被当作结构括号剥掉
ck(stripParens("k==='x'") === "k==='x'", '字符串内的引号内容未被改动');
ck(stripParens("f('(a)')") === "f('(a)')", '字符串内的括号未被误剥  ->  实际=' + JSON.stringify(stripParens("f('(a)')")));
ck(stripParens('(a)') === 'a', '最外层纯分组括号被剥掉');
ck(stripParens('((a))') === 'a', '嵌套纯分组括号被完全剥掉');

console.log(`\n${fails} 项失败`);
process.exit(fails ? 1 : 0);
