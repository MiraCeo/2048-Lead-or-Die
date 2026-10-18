// 交付文件名的**单一** JS 来源 —— 与 tools/_root.py 的 PATHS.DELIVERABLE 对应。
//
// 为什么需要它：阶段 1 的路径去绝对化只改了路径前缀，5 个测试脚本仍把文件名
// 写成字面量。收进这里，改名只改一行。
//
// ⚠️ 自 v0.2 起的发布纪律：交付物是**稳定文件名** `尔领死吧.html`，
//    永远指向最新构建。带版本号的副本在 releases/ 下，那由 build.py --release 生成，
//    测试只关心最新的那个，所以这里不需要版本号。
//
// Python 侧对应物：tools/_root.py 的 PATHS.DELIVERABLE
// 两处必须一起改。tools/check_doc_links.py / check_branding.py 会提示。
//
// 用法：
//     const path = require('path');
//     const ROOT = path.resolve(__dirname, '..');
//     const { DELIVERABLE } = require('./_root.js');
//     fs.readFileSync(path.join(ROOT, DELIVERABLE), 'utf8');
module.exports = {
  DELIVERABLE: '尔领死吧.html',
};
