"""仓库根目录的**单一**推导来源。

改造前每个脚本各自写死 `ROOT = Path(r'D:\\2048')`（共 23 个文件、29 处），
后果是仓库一旦被克隆到别处或换个盘符，整个工具链立即全线失效 —— 而模块化与
改名都必然伴随目录变动，所以这是必须先拆掉的前置约束。

用法（tools/ 下的脚本）：

    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _root import PATHS

    PATHS.ROOT / 'src' / 'main.script.js'
    PATHS.DELIVERABLE

`.resolve()` 不可省略：`__file__` 在某些调用方式下是相对路径，
只有 resolve 之后取 parent 才稳定指向 tools/。

下划线前缀是有意的：避免与局部变量（尤其是 `path`）混淆，
也让它在 `tools/` 的按名排序里沉到底部。
"""
from pathlib import Path
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# tools/_root.py -> tools/ -> 仓库根
ROOT = Path(__file__).resolve().parent.parent


class PATHS:
    """所有脚本共用的路径。新增路径请加在这里，不要在脚本里另写相对推导。"""

    ROOT = ROOT
    TOOLS = ROOT / 'tools'
    SRC = ROOT / 'src'
    BUILD = ROOT / 'build'
    # 参照物是**输入**，不是构建产物 —— 所以放顶层，不放 build/。
    # （阶段 4 之前它在 build/reference/，名字会让人以为可以随便删，
    #   而其中的 tutorial.script.js 是 derive_patches.py 的活依赖。）
    REFERENCE = ROOT / 'reference'
    BASELINE = BUILD / 'baseline'
    REPORTS = BUILD / 'reports'
    TRACES = BUILD / 'traces'

    # 交付物：单个自包含 HTML，位于仓库根，玩家双击即开。
    # ⚠️ 文件名被多个脚本与文档引用；改名时**只改这一处**，
    #    其余脚本一律走 PATHS.DELIVERABLE（这正是本次改造的目的之一）。
    DELIVERABLE = ROOT / '尔领死吧-v0.1.0.html'

    # 步骤 0 的逐字节原始参照（历史快照，不要覆盖）
    ORIGINAL = REFERENCE / '2048.original.html'
    # 教程脚本参考：构建**不**依赖它，但 tools/derive_patches.py 依赖
    # —— 它是唯一的教程脚本模板，丢了就无法重新推导补丁。
    TUTORIAL_REFERENCE = REFERENCE / 'tutorial.script.js'
    # 无头引擎（构建产物）
    ENGINE = BUILD / 'engine.js'

def main():
    """直接运行可自检：打印解析结果并报告缺失项（便于排查搬运后的失效路径）。"""
    print('仓库根: %s' % PATHS.ROOT)
    print()
    for name in ('TOOLS', 'SRC', 'BUILD', 'REFERENCE', 'BASELINE', 'DELIVERABLE',
                 'ORIGINAL', 'TUTORIAL_REFERENCE', 'ENGINE'):
        p = getattr(PATHS, name)
        mark = '存在' if p.exists() else '缺失'
        kind = '目录' if p.is_dir() else '文件'
        print('  %-20s %-4s %-4s %s' % (name, kind, mark, p.relative_to(PATHS.ROOT) if p.is_relative_to(PATHS.ROOT) else p))
    print()
    missing = [n for n in ('SRC', 'BUILD', 'DELIVERABLE', 'REFERENCE')
               if not getattr(PATHS, n).exists()]
    if missing:
        print('⚠️  关键路径缺失: %s' % ', '.join(missing))
        return 1
    print('✅ 关键路径齐备')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
