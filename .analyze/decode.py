import re, base64, os

SRC = r'C:\Users\12782\Downloads\2048\2048小游戏-教程七关.html'
OUT = r'D:\Hypergryph\模拟初筛\.analyze'

s = open(SRC, encoding='utf-8').read()
blobs = re.findall(r"atob\('([A-Za-z0-9+/=]+)'\)", s)
print('atob blobs:', len(blobs))

names = ['guide', 'tutorial']
for i, b in enumerate(blobs):
    try:
        d = base64.b64decode(b).decode('utf-8')
    except Exception as e:
        print(i, 'decode fail', e)
        continue
    nm = names[i] if i < len(names) else 'blob%d' % i
    with open(os.path.join(OUT, nm + '.html'), 'w', encoding='utf-8') as f:
        f.write(d)
    title = re.search(r'<title>(.*?)</title>', d, re.S)
    txt = re.sub(r'<script.*?</script>', '', d, flags=re.S)
    txt = re.sub(r'<style.*?</style>', '', txt, flags=re.S)
    txt = re.sub(r'<[^>]+>', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt)
    print('---', nm, 'len', len(d), '---')
    print('TITLE:', title.group(1) if title else '?')
    print(txt[:1600])
    print()
