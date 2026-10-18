// ==== 50-absorb ====
// 溯源: 阶段 2 的压缩文本 main.script.js 第 58–74 行（此后经阶段 3 改名、阶段 4 格式化）
// 回血、吸收结算、自动收集、科技树取值
  function extraStep(q, id, dir) {
    if (q.dead || q.settled) return { error: '已失去所有核心，请撤销或重新开始。' };
    if (q.ap < 1) return { error: '行动点不足：每两次有效主移动获得 1 点。' };
    const i = q.g.findIndex((t) => t?.id === id),
      a = q.g[i];
    if (!a || a.side !== 'p' || a.core || a.support) return { error: '只能额外操作己方非核心方块。' };
    const j = neighbor(i, dir);
    if (j < 0) return { error: '超出地图边界，不消耗行动点。' };
    const b = q.g[j];
    if (b?.side === 'e') {
      const efx = [];
      const clash = contact(q, i, j, efx);
      q.ap--;
      if (!q.dead) normalize(q);
      rescale(q);
      return {
        info:
          '单块血量对碰：' +
          (clash.aDead ? '选中方块被摧毁' : clash.advanced ? '击破敌方并进入目标格' : '防守方存活') +
          ' · 行动点 −1',
        newId: clash.aDead ? null : id,
        fx: efx,
      };
    }
    const annexed = b?.support ? capture(q, b, a.team, 'p') : 0;
    let info,
      newId = id;
    if (!b) {
      q.g[j] = a;
      q.g[i] = null;
      info = '单块移动一格';
    } else {
      const receiver = b.side === 'p' ? teamCore(q, b.team) : null;
      const resultTeam = receiver ? b.team : a.team;
      if (a.n === b.n && Number.isSafeInteger(a.n * 2)) {
        if (b.side === 'n') capture(q, b, resultTeam, 'p');
        const n = a.n * 2,
          cap = 3 ** lvl(n);
        q.g[j] = { id: b.core ? b.id : a.id, n, side: 'p', core: !!b.core, team: resultTeam, hp: cap, cap };
        q.g[i] = null;
        newId = b.core ? null : a.id;
        q.score += n;
        info = receiver ? '选中块合入目标核心主体' : '合并并收编目标方块';
      } else if (receiver && a.team !== b.team) {
        a.team = b.team;
        info = '目标主体接纳选中块，双方位置不变，原成员不转移';
      } else if (b.side === 'n' || b.team !== a.team) {
        const count = capture(q, b, a.team, 'p');
        info = `碰撞收编 ${count} 个方块，双方位置不变`;
      } else if (annexed) info = `吞并友方碉堡 ${annexed} 块，双方位置不变`;
      else return { error: '同主体异值方块阻挡，不消耗行动点。' };
    }
    q.ap--;
    normalize(q);
    rescale(q);
    checkGoal(q);
    if (q.g.some((t) => t?.id === newId && t.core)) newId = null;
    return { info, newId };
  }
  function dist2(i, j) {
    return (Math.floor(i / N) - Math.floor(j / N)) ** 2 + ((i % N) - (j % N)) ** 2;
  }
  function kill(q, i, fx) {
    const t = q.g[i];
    if (!t) return;
    if (fx) fx.push({ kind: 'kill', at: i });
    if (t.side === 'p' && t.core && t.id === q.primary) {
      q.playerCore = t.n;
      q.primaryLost = true;
      log(q, `主核心被毁 · 全体保留 core=${t.n} 的共享加成`);
    }
    q.g[i] = null;
    if (t.side === 'e') {
      q.kills++;
      if (t.core || t.kind === 'bunker') q.tech = (q.tech || 0) + 1;
    }
    if (t.structure) {
      for (const u of q.g)
        if (u?.support && u.team === t.team) {
          u.side = 'n';
          u.team = null;
          delete u.support;
          delete u.structure;
          delete u.supportCore;
        }
      log(q, '友方支援碉堡被摧毁，残部转为中立。');
    }
    if (t.core) {
      log(q, `${t.side === 'p' ? '己方' : '敌方'}核心 ${t.n} 被摧毁`);
      for (const u of q.g)
        if (u && u.side === t.side && u.team === t.team) {
          u.core = false;
          if (t.side === 'e') {
            u.side = 'n';
            u.team = null;
          } else u.team = 'orphan-' + t.id;
        }
      if (t.side === 'p' && !cores(q, 'p').length) {
        q.dead = true;
        q.active = null;
      }
    }
    rescale(q);
  }
  const shotOffsets = [];
  for (let dr = -8; dr <= 8; dr++)
    for (let dc = -8; dc <= 8; dc++) if (dr * dr + dc * dc <= 64) shotOffsets.push([dr, dc, dr * dr + dc * dc]);
  function fire(q, side, fx, filter = () => true) {
    const ids = q.g.filter((t) => t?.side === side && filter(t)).map((t) => t.id),
      enemy = side === 'p' ? 'e' : 'p',
      positions = new Map(),
      opponents = [];
    q.g.forEach((t, i) => {
      if (t) positions.set(t.id, i);
      if (t?.side === enemy) opponents.push(i);
    });
    let count = 0;
    for (const id of ids) {
      if (q.dead) break;
      const i = positions.get(id),
        a = q.g[i];
      if (!a || a.side !== side) continue;
      let target = -1,
        min = 65;
      const row = Math.floor(i / N),
        col = i % N;
      for (const [dr, dc, d] of shotOffsets) {
        if (d >= min || row + dr < 0 || row + dr >= N || col + dc < 0 || col + dc >= N) continue;
        const j = (row + dr) * N + col + dc;
        if (q.g[j]?.side === enemy) {
          min = d;
          target = j;
        }
      }
      if (target < 0) continue;
      const dmg = damage(q, a);
      q.g[target].hp -= dmg;
      markCombat(q, q.g[target]);
      fx.push({ from: i, to: target, side });
      fx.push({ kind: 'hit', at: target, dmg: dmg });
      q.shots++;
      count++;
      if (q.g[target].hp <= 0) kill(q, target, fx);
    }
    neutralClusters(q);
    if (!q.dead) normalize(q);
    return count;
  }
  function collect(q, id) {
    const i = coreIndex(q, id),
      t = q.g[i];
    if (!t) return false;
    let target = -1;
    for (const d in dirs) {
      const j = neighbor(i, d);
      if (j < 0 || q.g[j]?.side !== 'n') continue;
      const candidate = q.g[j],
        old = q.g[target];
      if (target < 0 || (candidate.nc && !old.nc) || (!!candidate.nc === !!old.nc && candidate.n > old.n)) target = j;
    }
    if (target < 0) return false;
    t.payload = (t.payload || 0) + q.g[target].n;
    q.g[target] = null;
    while (t.payload >= t.n) {
      t.payload -= t.n;
      const oldCap = t.cap || 1,
        oldHp = t.hp ?? oldCap;
      t.n *= 2;
      t.cap = 3 ** lvl(t.n) * lvl(t.n);
      t.hp = Math.max(1, Math.min(t.cap, Math.round((oldHp * t.cap) / oldCap)));
      log(q, `采集机升级 · core=${t.n}`);
      if (t.n > aiAbsorbCeiling(q)) {
        t.payload = 0;
        break;
      }
    }
    rescale(q);
    return true;
  }
  function ai(q) {
    const ids = cores(q, 'e').map((t) => t.id);
    let moves = 0;
    for (const id of ids) {
      if (q.dead || coreIndex(q, id) < 0) continue;
      const unit = q.g[coreIndex(q, id)],
        kind = unit.kind || 'squad';
      if (kind === 'bunker') continue;
      if (kind === 'collector') collect(q, id);
      const attempts = kind === 'fighter' ? 2 : 1;
      for (let step = 0; step < attempts; step++) {
        if (coreIndex(q, id) < 0) break;
        const pcores = cores(q, 'p').map((t) => coreIndex(q, t.id));
        if (!pcores.length) break;
        let goals = pcores;
        if (kind === 'collector') {
          const here = coreIndex(q, id),
            resources = q.g
              .map((t, i) => (t?.side === 'n' ? i : -1))
              .filter((i) => i >= 0)
              .sort((a, b) => dist2(a, here) - dist2(b, here));
          const dense = resources.filter((i) => q.g[i].nc);
          if (dense.length) goals = dense;
          else if (resources.length) goals = resources.slice(0, 5);
        }
        let best = null;
        for (const dir of ['up', 'left', 'down', 'right']) {
          const draft = copy(q),
            r = moveMain(draft, dir, id);
          if (!r) continue;
          const ci = coreIndex(draft, id);
          if (ci < 0) continue;
          const distance = Math.min(...goals.map((i) => Math.sqrt(dist2(ci, i))));
          const core = draft.g[ci];
          let value = -distance * 10 + r.merges * 3 + r.recruited * 0.5;
          if (kind !== 'collector' && core.hp / core.cap < 0.3 && distance < 4) value -= 25;
          if (!best || value > best.value) best = { draft, value };
        }
        if (best) {
          Object.assign(q, best.draft);
          moves++;
        } else break;
      }
    }
    return moves;
  }
