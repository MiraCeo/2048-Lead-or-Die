// ==== 40-combat ====
// 来源: main.script.js 第 49–57 行（原样搬移，未改一字符）
// 接触、主移动、额外操作
    for (let k = 0; k < 2; k++) {
      const i = uniformEmpty(q);
      if (i < 0) break;
      const id = q.serial++,
        n = 8,
        cap = 3 ** lvl(n) * lvl(n);
      q.g[i] = { id, n, side: 'e', core: true, team: id, kind: 'squad', hp: cap, cap };
      fillEnemy(q, id);
    }
    for (let k = 0; k < 450; k++) {
      let i = Math.floor(rand(q) * (N * N));
      if (!q.g[i]) add(Math.floor(i / N) - 25, (i % N) - 25, rand(q) < 0.8 ? 2 : 4);
    }
    for (const core of cores(q, 'e')) fillEnemy(q, core.id);
    neutralClusters(q);
    normalize(q);
    rescale(q);
    checkGoal(q, 0);
    log(q, '远征开始：初始2支编队，第20回合起出现敌机、碉堡、采集机。');
    log(q, '额外碰撞已有核心主体：由目标接纳选中块，不转移旁边成员。');
    return q;
  }
  function contact(q, i, j, fx) {
    const a = q.g[i],
      b = q.g[j];
    if (!a || !b || a.side === 'n' || b.side === 'n' || a.side === b.side) return null;
    const aHP = a.hp,
      bHP = b.hp,
      aDead = aHP <= bHP,
      bDead = bHP <= aHP;
    a.hp = Math.max(0, aHP - bHP);
    b.hp = Math.max(0, bHP - aHP);
    markCombat(q, a);
    markCombat(q, b);
    if (fx) {
      fx.push({ kind: 'hit', at: i, dmg: Math.ceil(bHP) });
      fx.push({ kind: 'hit', at: j, dmg: Math.ceil(aHP) });
    }
    if (bDead) kill(q, j, fx);
    if (aDead) kill(q, i, fx);
    let advanced = false;
    if (!aDead && q.g[i]?.id === a.id && !q.g[j]) {
      q.g[j] = a;
      q.g[i] = null;
      advanced = true;
    }
    neutralClusters(q);
    if (aDead || bDead)
      log(q, `血量对碰 · ${aDead && bDead ? '双方消失' : '一方被击破'}（${Math.ceil(aHP)} ↔ ${Math.ceil(bHP)}）`);
    return { aHP, bHP, aDead, bDead, advanced };
  }
  function moveMain(q, dir, id = q.active, fx) {
    const ci = coreIndex(q, id);
    if (ci < 0) return null;
    const team = q.g[ci].team,
      side = q.g[ci].side,
      ids = [...connected(q, id)]
        .sort((a, b) => (dir === 'right' || dir === 'down' ? b - a : a - b))
        .map((i) => q.g[i].id),
      moved = new Set(),
      merged = new Set();
    let changed = 0,
      recruited = 0,
      merges = 0,
      contacts = 0;
    function push(i) {
      const a = q.g[i];
      if (!a || a.support || moved.has(a.id) || merged.has(a.id)) return false;
      const j = neighbor(i, dir);
      if (j < 0) return false;
      const b = q.g[j];
      if (b && b.side !== 'n' && b.side !== side) {
        recruited += capture(q, a, team, side);
        rescale(q);
        const clash = contact(q, i, j, fx);
        if (clash) {
          changed++;
          contacts++;
          moved.add(a.id);
          return !q.g[i] || q.g[i].id !== a.id;
        }
        return false;
      }
      if (b?.support) {
        if (side !== 'p') return false;
        recruited += capture(q, b, team, side);
        changed++;
      }
      if (b?.side === 'e' && b.core && b.kind === 'bunker') return false;
      if (!b) {
        recruited += capture(q, a, team, side);
        q.g[j] = a;
        q.g[i] = null;
        moved.add(a.id);
        changed++;
        return true;
      }
      if (
        a.n === b.n &&
        !merged.has(b.id) &&
        (side === 'e' ? Number.isFinite(a.n * 2) : Number.isSafeInteger(a.n * 2))
      ) {
        recruited += capture(q, a, team, side);
        recruited += capture(q, b, team, side);
        const n = a.n * 2,
          newId = b.core ? b.id : a.core ? a.id : b.id;
        const cap = 3 ** lvl(n);
        q.g[j] = {
          id: newId,
          n,
          side,
          team,
          core: !!(a.core || b.core),
          hp: cap,
          cap,
          kind: b.core ? b.kind : a.core ? a.kind : undefined,
          payload: b.core ? b.payload : a.core ? a.payload : undefined,
          nextGrowth: b.core ? b.nextGrowth : a.core ? a.nextGrowth : undefined,
        };
        q.g[i] = null;
        if (side === 'p') q.score += n;
        moved.add(a.id);
        moved.add(b.id);
        merged.add(newId);
        merges++;
        changed++;
        return true;
      }
      if (moved.has(b.id) || merged.has(b.id) || !push(j)) return false;
      recruited += capture(q, a, team, side);
      q.g[j] = a;
      q.g[i] = null;
      moved.add(a.id);
      changed++;
      return true;
    }
    for (const uid of ids) {
      if (q.dead) break;
      const i = q.g.findIndex((t) => t?.id === uid);
      if (i >= 0) push(i);
    }
    if (!changed) return null;
    const splits = q.dead ? 0 : normalize(q);
    rescale(q);
    if (side === 'p') checkGoal(q, q.turn + 1);
    return { merges, recruited, splits, contacts };
  }
