"""修正外壳测试的两条断言（是我断言写错了，不是代码错）。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_shell.js'
t = p.read_text(encoding='utf-8')


def sub(old, new, n, label):
    global t
    c = t.count(old)
    if c != n:
        sys.exit('%s：预期 %d 次，实际 %d 次' % (label, n, c))
    t = t.replace(old, new)
    print('已改：%s' % label)


# 导航在介绍页里，而介绍页是 base64 嵌进交付文件的 —— 要在解出来的 GUIDE 里查
sub("  check(HTML.includes('>画面与科技<'), '介绍页导航加入了新章节');",
    "  check(GUIDE.includes('>画面与科技<'), '介绍页导航加入了新章节');",
    1, '导航断言改查解码后的介绍页')

# 原来那条太宽：引擎的 setMode() 里有一句瞬时提示也含同样字样，属正常反馈。
# 改为直接验「棋盘上方的预览位默认是空的」+「clearPreview 不再写回操作说明」。
sub("  check(!HTML.includes('WASD / 方向键移动 · 点击己方数字单独调整'), 'WASD 说明不再常驻棋盘上方');",
    "  check(HTML.includes('<div id=\"previewHint\" class=\"mini-detail map-keyhint\"></div>'),\n"
    "        '棋盘上方的预览位默认是空的');\n"
    "  check(ENGINE.includes(\"$('previewHint').textContent=''\"),\n"
    "        'clearPreview() 清空预览位，而不是把操作说明写回去');",
    1, 'WASD 断言改为验空预览位与 clearPreview 行为')

p.write_text(t, encoding='utf-8', newline='')
print('test_shell.js 已更新')
