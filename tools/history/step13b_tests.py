"""补充外壳测试：画布尺寸对齐、顶部标签已删、坐标仍保留。"""
import sys
from pathlib import Path

p = Path(r'D:\2048') / 'tools' / 'test_shell.js'
t = p.read_text(encoding='utf-8')

OLD = """console.log('\\n=== 棋盘尺寸不再用魔法数字 ===');
{
  check(HTML.includes('max-height:calc(100dvh - var(--board-chrome,230px))'),
        '棋盘高度交给浏览器按可用空间算（开销是单个可调变量）');
  check(HTML.includes('.board canvas{width:auto;height:auto'), 'canvas 等比缩放（不再拉伸）');
}"""

NEW = """console.log('\\n=== 棋盘尺寸不再用魔法数字 ===');
{
  check(HTML.includes('max-height:calc(100dvh - var(--board-chrome,230px))'),
        '棋盘高度交给浏览器按可用空间算（开销是单个可调变量）');
  check(HTML.includes('.board canvas{width:auto;height:auto'), 'canvas 等比缩放（不再拉伸）');
}

console.log('\\n=== 画布：去掉顶部标签与下方留空，坐标保留 ===');
{
  check(HTML.includes('id="canvas" width="860" height="860"'), '画布改为 860×860（下方不再留白）');
  check(!ENGINE.includes('EXPEDITION SECTOR'), '顶部左侧「100 × 100」标签已删');
  check(!ENGINE.includes('CORE-CENTERED VIEW'), '顶部右侧「25 × 25」标签已删');
  check(!ENGINE.includes('886'), '引擎里不再有任何 886（坐标映射全部跟进）');
  check(ENGINE.includes('text(cam.c+c+1') && ENGINE.includes('text(cam.r+c+1'),
        '棋盘四周的行列坐标仍然保留');
  check(ENGINE.includes("preview?'") === false, '画布不再自绘模式文字（顶栏 #modeLabel 已在显示）');
}"""

c = t.count(OLD)
if c != 1:
    sys.exit('锚点命中 %d 次（预期 1）' % c)
p.write_text(t.replace(OLD, NEW, 1), encoding='utf-8', newline='')
print('test_shell.js 已补充画布断言')
