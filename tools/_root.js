// 交付文件名的**单一** JS 来源 —— 与 tools/_root.py 的 PATHS.DELIVERABLE 对应。
//
// 为什么需要它：阶段 1 的路径去绝对化只改了路径前缀，5 个测试脚本仍把文件名
// 写成字面量（path.join(ROOT, '2048小游戏-教程七关.html')）。阶段 3 改名时
// 这种散落就会变成 5 处要同步的隐患 —— 收进这里，改名只改一行。
//
// Python 侧对应物：tools/_root.py 的 PATHS.DELIVERABLE
// ⚠️ 两处必须一起改（本文件与 _root.py）。tools/rename_project.py 会提示这一点。
//
// 用法：
//     const path = require('path');
//     const ROOT = path.resolve(__dirname, '..');
//     const { DELIVERABLE } = require('./_root.js');
//     fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');
module.exports = {
  DELIVERABLE: '尔领死吧-v0.1.0.html',
};
