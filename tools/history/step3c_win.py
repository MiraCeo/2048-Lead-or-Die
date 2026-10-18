"""Step 3 (fix): lesson 02's win condition was satisfied by the decorative capped 8.

The board includes a friendly 8 purely to demonstrate the cap rule. The win
condition asked only for "some friendly non-core tile with n >= 8", which that
decoration satisfies from turn 0 -- so the lesson reported complete after the
first press.

Fix: also require that only the spared neutral remains, i.e. both absorptions
have actually happened.
"""
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

LES = Path(r'D:\2048') / 'src' / 'tutorial.lessons.js'
les = LES.read_text(encoding='utf-8')

OLD = "if(q.lesson===1)return q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=8)&&q.g.some(t=>t?.side==='n'&&t.n===2);"
NEW = ("if(q.lesson===1)return q.g.filter(t=>t?.side==='n').length===1"
       "&&q.g.some(t=>t?.side==='p'&&!t.core&&t.n>=8);")

c = les.count(OLD)
if c != 1:
    sys.exit('LESSON FIX FAILED: win condition matched %d times (expected 1)' % c)

LES.write_text(les.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('lesson02 win condition fixed: both absorptions must happen')
