"""Side-by-side series from two trace files, to see WHEN a quantity diverges.

first_divergence.py tells us the first differing turn; this tells us the shape of
the divergence (e.g. when the main core's growth actually stalls).

Usage:
    python tools/trace_series.py build/traces/norm.jsonl build/traces/supply.jsonl
    python tools/trace_series.py a.jsonl b.jsonl --every 5 --fields sharedCore,mainN
"""
import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ap = argparse.ArgumentParser()
ap.add_argument('a')
ap.add_argument('b')
ap.add_argument('--every', type=int, default=5)
ap.add_argument('--fields', default='sharedCore,mainN,mainHp,pCores,nPlayer,nNeutral,nEnemy')
ap.add_argument('--turns', type=int, default=0, help='stop after this turn (0 = all)')
args = ap.parse_args()

fields = args.fields.split(',')


def load(p):
    return [json.loads(ln) for ln in Path(p).read_text(encoding='utf-8').splitlines() if ln.strip()]


A, B = load(args.a), load(args.b)
na, nb = Path(args.a).stem, Path(args.b).stem

# header: turn | a.f1 a.f2 ... | b.f1 b.f2 ...
head = '%6s | %s | %s | diff' % (
    'turn',
    ' '.join('%-9s' % f for f in fields),
    ' '.join('%-9s' % f for f in fields))
print('%s  vs  %s' % (na, nb))
print('-' * len(head))
print(head)
print('-' * len(head))

n = min(len(A), len(B))
for i in range(n):
    turn = A[i]['turn']
    if args.turns and turn > args.turns:
        break
    if i % args.every and i != n - 1:
        continue
    av = ' '.join('%-9s' % A[i].get(f) for f in fields)
    bv = ' '.join('%-9s' % B[i].get(f) for f in fields)
    same = A[i]['hash'] == B[i]['hash']
    print('%6s | %s | %s | %s' % (turn, av, bv, '=' if same else 'DIFF'))
