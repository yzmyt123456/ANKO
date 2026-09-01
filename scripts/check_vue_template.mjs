/* Vue 模板编译校验:用 @vue/compiler-dom 检查 index.html 的 #app 模板语法。
 * 用法: node scripts/check_vue_template.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const root = process.cwd();
const htmlPath = path.join(root, 'anko', 'static', 'index.html');
const html = fs.readFileSync(htmlPath, 'utf-8');

// 提取 #app 内的模板(从 <div id="app"> 到 <script src=)
const start = html.indexOf('<div id="app">');
const end = html.indexOf('<script src="/static/vendor/vue.global.prod.js">');
if (start < 0 || end < 0) {
  console.error('❌ 找不到 #app 模板边界');
  process.exit(1);
}
const template = html.slice(start, end);

const require = createRequire(import.meta.url);
const { compile } = require(path.join(root, 'scripts', 'vendor', 'node_modules', '@vue', 'compiler-dom'));

try {
  const result = compile(template, { mode: 'module' });
  if (result.errors && result.errors.length) {
    console.error('❌ 模板编译错误:');
    for (const e of result.errors) console.error('  -', e.message || e);
    process.exit(1);
  }
  console.log(`✅ Vue 模板编译通过(生成 ${result.code.length} 字节渲染代码)`);
} catch (e) {
  console.error('❌ 模板编译异常:', e.message);
  process.exit(1);
}
