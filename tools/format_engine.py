"""阶段 4：把 src/engine/ 的压缩代码格式化为可读代码。

## 为什么必须整体格式化

单个模块文件**语法不完整**（10-prelude 以 `(()=>{` 开头、99-boot 以 `})();` 结尾），
prettier 解析不了。实测：11 个模块里只有 4 个能单独通过。

所以做法是：**先拼成完整脚本，整体格式化，再按标记切回各模块。**

## 怎么保证"逻辑不变"

1. 拼接时在模块之间插入 `/*! __SPLIT_<n>__ */` 标记。选 `/*!` 是因为
   prettier 对"法律注释"（legal comment）有保留约定，实测确实原样保留。
2. 用 `prettier --debug-check`：它格式化后会重新解析输出、与输入比对 AST，
   不等价就报错。这是我们能拿到的最强的"格式化不改语义"保证。
3. 切回各模块后，bundle_engine.py 重建 main.script.js，再跑：
   - build.py（产物应在**语义**上不变；字节会变，因为教程侧格式没变）
   - 9 组功能测试
   - difftest（逐回合逐位一致 —— 这是最强的行为判据）

## 教程侧会怎样（重要）

13 条补丁的 `old`（引擎侧）会随格式化而失效。重建流程见项目文档 §17。
教程侧（`new`）**保持原样**，所以教程脚本会变成"引擎部分已格式化、教程专属部分未格式化"
的混合体 —— 这是可接受的，且能正常工作。

用法：
    python tools/format_engine.py --check        # 只检查 prettier 是否可用
    python tools/format_engine.py --dry-run      # 格式化到临时文件，不写回
    python tools/format_engine.py --apply        # 写回 src/engine/*.js
"""
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = next((p for p in [HERE, *HERE.parents] if (p / 'src').is_dir()), HERE)
ENGINE_DIR = ROOT / 'src' / 'engine'
MANIFEST = ENGINE_DIR / 'manifest.json'
TMP = ROOT / '.fmt'

PRETTIER = 'prettier@3.9.9'
PRINT_WIDTH = '120'
MARK = '/*! __SPLIT_%d__ */'

APPLY = '--apply' in sys.argv
DRY = '--dry-run' in sys.argv or APPLY


def run_prettier(path, extra=()):
    cmd = ['npx', '--yes', PRETTIER, '--parser', 'babel',
           '--print-width', PRINT_WIDTH, '--single-quote']
    cmd += list(extra)
    cmd.append(str(path))
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', shell=True)
    return r


def main():
    if not MANIFEST.exists():
        sys.exit('找不到 %s —— 先跑 tools/extract_engine.py' % MANIFEST)
    man = json.loads(io.open(MANIFEST, encoding='utf-8').read())
    header_lines = man.get('headerLines', 3)
    names = [m['name'] for m in man['modules']]

    # ---- 1. 读各模块正文（去注释头） --------------------------------------
    bodies = []
    for name in names:
        p = ENGINE_DIR / (name + '.js')
        text = io.open(p, encoding='utf-8', newline='').read()
        lines = text.split('\n')
        if text.endswith('\n'):
            lines = lines[:-1]
        bodies.append(lines[header_lines:])

    # ---- 2. 拼接（模块间插标记） ------------------------------------------
    combined = []
    for i, body in enumerate(bodies):
        if i:
            combined.append(MARK % i)
        combined.extend(body)
    src_text = '\n'.join(combined) + '\n'

    TMP.mkdir(parents=True, exist_ok=True)
    src = TMP / 'combined.js'
    io.open(src, 'w', encoding='utf-8', newline='\n').write(src_text)
    print('拼接: %d 个模块 -> %d 行, %d 字节'
          % (len(names), len(combined), len(src_text.encode('utf-8'))))

    # ---- 3. prettier --debug-check（AST 等价校验） ------------------------
    print('\n=== prettier --debug-check（AST 等价校验） ===')
    r = run_prettier(src, extra=['--debug-check'])
    out = (r.stdout or '') + (r.stderr or '')
    if r.returncode != 0:
        print(out[:1500])
        print('❌ --debug-check 失败 —— 格式化会改变 AST，已中止。')
        return 1
    print('  ✅ 通过（格式化后重新解析的 AST 与输入等价）')

    if not DRY:
        print('\n（未写回；--dry-run 只做上述校验，--apply 才写回）')
        return 0

    # ---- 4. 真正格式化 ----------------------------------------------------
    print('\n=== prettier 格式化 ===')
    r = run_prettier(src)
    if r.returncode != 0 or not (r.stdout or '').strip():
        print(((r.stdout or '') + (r.stderr or ''))[:1500])
        print('❌ 格式化失败')
        return 1
    formatted = r.stdout
    io.open(TMP / 'formatted.js', 'w', encoding='utf-8', newline='\n').write(formatted)
    print('  输出 %d 行, %d 字节'
          % (len(formatted.split('\n')) - 1, len(formatted.encode('utf-8'))))

    # ---- 5. 按标记切回各模块 ----------------------------------------------
    lines = formatted.split('\n')
    if lines and lines[-1] == '':
        lines = lines[:-1]

    marks = {MARK % i: i for i in range(1, len(names))}
    blocks = {}
    cur = 0
    buf = []
    unknown = []
    dropped = 0
    for ln in lines:
        s = ln.strip()
        if s in marks:
            blocks[cur] = buf
            cur = marks[s]
            buf = []
            dropped += 1
            continue
        if s.startswith('/*! __SPLIT_') and s not in marks:
            unknown.append(s)
        buf.append(ln)
    blocks[cur] = buf
    print('  按标记切分为 %d 块（丢弃标记 %d 行）' % (len(blocks), dropped))

    if unknown:
        print('  !! 出现未预期的标记: %s' % unknown[:3])
    if len(blocks) != len(names):
        print('  ❌ 切分得到 %d 块，期望 %d 块 —— 标记可能被 prettier 改动'
              % (len(blocks), len(names)))
        return 1

    # ⚠️ 这里**不做任何空行裁剪**。
    # 标记行在拼接时"取代"了模块边界处原本的那一行；切分时标记被丢弃，
    # 边界空行就落在**前一块的尾部**。若在此裁掉块尾空行，重建结果会比
    # prettier 输出少一行/每个边界 —— 实测正好少 10 行 216 字节。
    # 保持原样，bundle_engine.py 的 '\n'.join 会精确补回边界换行。

    print('\n=== 写回各模块 ===')
    total = 0
    for i, name in enumerate(names):
        body = blocks[i]
        total += len(body)
        old_path = ENGINE_DIR / (name + '.js')
        old_text = io.open(old_path, encoding='utf-8', newline='').read()
        old_lines = old_text.split('\n')
        header = old_lines[:header_lines]
        # 头部第 2 行标注来源与改动情况
        text = '\n'.join(header + body) + '\n'
        io.open(old_path, 'w', encoding='utf-8', newline='').write(text)
        print('  %-14s %4d -> %4d 行' % (name, len(old_lines) - 1 - header_lines, len(body)))
    print('  %-14s %4d 行合计' % ('', total))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
