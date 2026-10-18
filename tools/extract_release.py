"""从 git 历史里取出某个提交的交付产物（二进制安全），用于版本归档。

为什么需要脚本：PowerShell 的 `>` 重定向会把输出写成 UTF-16 并加 BOM，
取出来的 HTML 就废了（实测第一字节 0xFF）。必须走 subprocess 取原始字节。

用法：
    python tools/extract_release.py <commit> <out-path>
    python tools/extract_release.py 4a84310 releases/尔领死吧-v0.1.0.html
    python tools/extract_release.py 4a84310 --list     # 只列出该提交里的 html
"""
import hashlib
import io
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)


def git(*args, binary=False):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise SystemExit('git %s 失败: %s' % (' '.join(args),
                                              r.stderr.decode('utf-8', 'replace')))
    return r.stdout if binary else r.stdout.decode('utf-8', 'replace')


def list_html(commit):
    # -c core.quotePath=false：否则中文路径会被转义成 \345\260\224 之类，无法匹配
    out = git('-c', 'core.quotePath=false', 'ls-tree', '-r', '--name-only', commit)
    return [ln for ln in out.splitlines()
            if ln.endswith('.html') and not ln.startswith(('src/', 'reference/'))
            and not ln.startswith('build/')]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    commit, target = sys.argv[1], sys.argv[2]

    cands = list_html(commit)
    print('提交 %s 里的交付产物候选:' % commit)
    for c in cands:
        print('  ' + c)
    if target == '--list' or not cands:
        return 0

    # 选第一个（历史上只有一个交付产物）
    src = cands[0]
    data = git('show', '%s:%s' % (commit, src), binary=True)
    print()
    print('取出: %s:%s' % (commit, src))
    print('  字节数: %d' % len(data))
    print('  sha256: %s' % hashlib.sha256(data).hexdigest())
    # 头 16 字节检查：确认不是 UTF-16 BOM 之类的损坏
    if data[:2] in (b'\xff\xfe', b'\xfe\xff'):
        sys.exit('取出的内容带 UTF-16 BOM，说明提取方式错了')
    text = data.decode('utf-8')
    print('  含 fleetSummary:', 'fleetSummary' in text)
    print('  含 log-wrap    :', 'log-wrap' in text)

    out = ROOT / target
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, 'wb').write(data)
    print('  已写入: %s' % out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
