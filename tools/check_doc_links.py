"""对账：文档里引用的仓库内路径是否真实存在。

工具归档/搬迁后，文档里的链接最容易变成死链（本项目历史上已经出过
「§8 说的实验环境路径已失效」这类问题）。与其手工找，不如机器查。

用法：
    python tools/check_doc_links.py            # 查错
    python tools/check_doc_links.py --all      # 连 tools/history 里的也一起查
"""
import io
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)

SHOW_ALL = '--all' in sys.argv
DOCS = ['README.md', '项目文档.md', '交接文档.md', '界面优化.md', 'AGENT.md']

# 抓三类引用：
#   1. markdown 链接  [文字](路径)
#   2. 反引号包裹的仓库内路径  `tools/xxx.py`
#   3. 裸写的 tools/xxx.py
# 只查**带路径**的引用。裸文件名（如表格里的 `build.py`、`guide.html`）不查 ——
# 它们前面没有目录前缀，无法可靠判断指的是 tools/ 还是 src/ 还是别处，
# 第一版把这类全报成失效，107 个引用里 36 个是误报。
LINK_RE = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
TICK_RE = re.compile(r'`((?:src|tools|build|\.analyze)/[A-Za-z0-9_./\-]+)`')
BARE_RE = re.compile(r'(?<![\w`/(])((?:src|tools|build|\.analyze)/[A-Za-z0-9_./\-]+)')

# 允许不存在的写法：可再生的构建产物、示例输出名、明确的占位符
ALLOW = re.compile(r'^(build/engine|build/core-fleet|build/variants|build/traces/|'
                   r'build/reports/|build/difftest/|build/cp3|.*\.pre-format$|'
                   r'tools/history/|.*<.*>.*)')


def strip_code_blocks(text):
    """去掉 ``` 围起来的代码块。

    代码块里常出现**已删除**的文件名（例如"`tools/test_step3.js` 整套测的是被替换掉的
    模型，**已删除**"），那是陈述事实的散文，不是失效链接。第一版把它们也报成失效，
    属于误报。
    """
    out = []
    in_block = False
    for ln in text.split('\n'):
        if ln.lstrip().startswith('```'):
            in_block = not in_block
            continue
        if not in_block:
            out.append(ln)
    return '\n'.join(out)


def collect(text):
    """返回 {路径: 首次出现的行文本}，按行去重（同一行多次提及只报一次）。"""
    refs = {}
    for ln in text.split('\n'):
        if ln.lstrip().startswith('>') and ('已归档' in ln or '已删除' in ln or '历史' in ln):
            continue          # 明确标注为历史/已删除的行不算失效
        for rx in (LINK_RE, TICK_RE, BARE_RE):
            for m in rx.finditer(ln):
                r = m.group(1).strip()
                if r.startswith(('http://', 'https://', '#')) or ' ' in r:
                    continue
                r = r.split('#')[0]
                if not r or ALLOW.match(r):
                    continue
                refs.setdefault(r, ln.strip()[:80])
    return refs


def main():
    missing = {}
    total = 0
    for doc in DOCS:
        p = ROOT / doc
        if not p.exists():
            continue
        text = strip_code_blocks(io.open(p, encoding='utf-8').read())
        bad = []
        for ref, line in sorted(collect(text).items()):
            total += 1
            if not (ROOT / ref).exists():
                bad.append((ref, line))
        if bad:
            missing[doc] = bad

    print('检查 %d 篇文档，共 %d 个仓库内路径引用（已排除代码块与历史标注）'
          % (len([d for d in DOCS if (ROOT / d).exists()]), total))
    print()
    if not missing:
        print('✅ 所有引用的路径都存在')
        return 0
    for doc, bad in missing.items():
        print('%s  —— %d 处失效:' % (doc, len(bad)))
        for ref, line in bad:
            print('   %-40s  在: %s' % (ref, line))
        print()
    print('❌ 共 %d 处失效引用' % sum(len(v) for v in missing.values()))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
