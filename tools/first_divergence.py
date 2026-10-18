"""Locate the first turn where two trace files diverge.

Finding the FIRST differing turn narrows the causal mechanism to something that
happens at that turn, instead of speculating about the whole 300-turn run.

Usage:
    python tools/first_divergence.py build/traces/norm.jsonl build/traces/supply.jsonl
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

if len(sys.argv) < 3:
    sys.exit('usage: first_divergence.py <a.jsonl> <b.jsonl>')

pa, pb = Path(sys.argv[1]), Path(sys.argv[2])


def load(p):
    return [json.loads(ln) for ln in p.read_text(encoding='utf-8').splitlines() if ln.strip()]


A, B = load(pa), load(pb)
FIELDS = ['turn', 'note', 'ap', 'sharedCore', 'mainN', 'mainHp', 'mainCap', 'pCores',
          'nPlayer', 'nNeutral', 'nEnemy', 'nSupport', 'empty', 'kills', 'rng', 'hash']

print('A = %s  (%d rows)' % (pa.name, len(A)))
print('B = %s  (%d rows)' % (pb.name, len(B)))

n = min(len(A), len(B))
first = None
for i in range(n):
    if A[i]['hash'] != B[i]['hash']:
        first = i
        break

if first is None:
    print('\nNo board divergence in the first %d turns.' % n)
    sys.exit(0)

print('\n*** FIRST BOARD DIVERGENCE at row %d ***' % first)
print('    (A turns=%d, B turns=%d)' % (
    sum(1 for r in A if r['turn'] > 0), sum(1 for r in B if r['turn'] > 0)))

for i in range(max(0, first - 1), min(n, first + 3)):
    mark = '   <== DIVERGED HERE' if i == first else ''
    print('\n--- row %d%s ---' % (i, mark))
    if i < 1:
        print('  (initial state)')
    diffs = [f for f in FIELDS if A[i].get(f) != B[i].get(f)]
    if not diffs:
        print('  identical')
        continue
    print('  %-12s %-16s %-16s' % ('field', pa.name, pb.name))
    for f in diffs:
        print('  %-12s %-16s %-16s  <-- differs' % (f, A[i].get(f), B[i].get(f)))

# how many rows diverge in total, and whether they stay diverged
ndiff = sum(1 for i in range(n) if A[i]['hash'] != B[i]['hash'])
print('\nrows with differing board hash: %d / %d' % (ndiff, n))
