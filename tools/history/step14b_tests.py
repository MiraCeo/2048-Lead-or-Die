"""补充外壳测试：科技面板拆成「侧栏入口 + 按需面板」。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_shell.js'
t = p.read_text(encoding='utf-8')

OLD = """  for (const id of ['canvas', 'minimap', 'previewHint', 'feedback', 'inspect', 'log',
                    'tech', 'techTree', 'convertScore', 'fleets', 'gameOver']) {"""
NEW = """  for (const id of ['canvas', 'minimap', 'previewHint', 'feedback', 'inspect', 'log',
                    'tech', 'techTree', 'convertScore', 'fleets', 'gameOver',
                    'openTech', 'closeTech', 'techDialog']) {"""
c = t.count(OLD)
if c != 1:
    sys.exit('唯一性列表锚点命中 %d 次（预期 1）' % c)
t = t.replace(OLD, NEW, 1)
print('已改：唯一性列表加入科技面板相关 id')

OLD2 = """console.log('\\n=== 核心从血量配色中排除 ===');"""
NEW2 = """console.log('\\n=== 科技面板：侧栏只留入口，详情在按需面板 ===');
{
  check(HTML.includes('<strong id="tech"></strong><span class="mini-detail">科技点</span></div>'
                      '<button id="openTech">打开科技树</button>'),
        '侧栏只剩「余额 + 打开科技树」');
  check(HTML.includes('id="techDialog"'), '按需面板在场');
  check(HTML.includes('class="panel-dialog"'), '按需面板有独立样式');
  check(ENGINE.includes("row.className='tech-row'"),
        '列表改为行式渲染（名称/效果/按钮分开，不再挤进一个按钮标签）');
  const guards = (ENGINE.match(/\\$\\('techDialog'\\)\\.open/g) || []).length;
  check(guards >= 2, '面板打开时棋盘输入被拦住（鼠标与键盘各一处）', `guard=${guards}`);
  check(ENGINE.includes("$('openTech').onclick") && ENGINE.includes("$('closeTech').onclick"),
        '打开/关闭已接线');
}

console.log('\\n=== 核心从血量配色中排除 ===');"""
c2 = t.count(OLD2)
if c2 != 1:
    sys.exit('章节锚点命中 %d 次（预期 1）' % c2)
t = t.replace(OLD2, NEW2, 1)
print('已改：加入科技面板断言')

p.write_text(t, encoding='utf-8', newline='')
print('test_shell.js 已更新')
