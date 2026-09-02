/* 知识库渲染测试:jsdom 加载页面,切换到知识库,点击词条,检查白屏/错误。
 * 用法: node scripts/kb_render_test.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const root = process.cwd();
const require = createRequire(path.join(root, 'scripts', 'vendor', 'package.json'));
const { JSDOM } = require('jsdom');

const html = fs.readFileSync(path.join(root, 'anko', 'static', 'index.html'), 'utf-8');
const dom = new JSDOM(html, {
  url: 'http://127.0.0.1:8000/',
  runScripts: 'outside-only',
  pretendToBeVisual: true,
});
const { window } = dom;
window.fetch = (url, opts) => {
  const full = String(url).startsWith('http') ? url : 'http://127.0.0.1:8000' + url;
  return fetch(full, opts);
};
const sleep = ms => new Promise(r => setTimeout(r, ms));

const errors = [];
window.addEventListener('error', e => errors.push('window error: ' + (e.message || e.error)));
window.console.error = (...a) => { errors.push('console.error: ' + a.join(' ')); };

window.eval(fs.readFileSync(path.join(root, 'anko/static/vendor/vue.global.prod.js'), 'utf-8'));
const apiSrc = fs.readFileSync(path.join(root, 'anko/static/js/api.js'), 'utf-8');
const appSrc = fs.readFileSync(path.join(root, 'anko/static/js/app.js'), 'utf-8');
const fetches = [];
const origFetch = window.fetch;
window.fetch = (url, opts) => {
  fetches.push(String(url));
  return origFetch(url, opts);
};
window.eval(apiSrc + '\n;\n' + appSrc);

await sleep(2500);
console.log('fetch 请求:', fetches.filter(u => u.includes('/rules')).join(' | '));

const doc = window.document;
const navItems = [...doc.querySelectorAll('.side-item')];
const kbNav = navItems.find(el => el.textContent.includes('知识库'));
console.log('找到知识库导航:', !!kbNav);
if (!kbNav) { console.log('errors:', errors); process.exit(1); }
kbNav.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(800);

const appEl = doc.querySelector('#app');
console.log('切换知识库后 #app 有内容:', appEl.innerHTML.length > 500);
const chips = doc.querySelectorAll('.kb-chip');
console.log('法术词条数:', chips.length);
const kbGroups = doc.querySelectorAll('.kb-group');
console.log('分组数:', kbGroups.length);
const kbEmpty = doc.querySelector('.kb .inline-empty, .view .inline-empty');
console.log('空提示:', kbEmpty ? kbEmpty.textContent : '无');
// 输出知识库区域片段
const kbSection = doc.querySelector('.view');
if (kbSection) console.log('知识库区前300:', kbSection.innerHTML.slice(0, 300).replace(/\s+/g, ' '));
if (!chips.length) {
  console.log('errors:', errors);
  console.log('#app 前 200:', appEl.innerHTML.slice(0, 200).replace(/\s+/g, ' '));
  process.exit(1);
}

// 点击第一个法术词条
chips[0].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(600);
const modal = doc.querySelector('.kb-modal');
console.log('词条详情弹窗打开:', !!modal);
if (modal) {
  console.log('弹窗含名称:', !!modal.querySelector('h2'));
  console.log('相关词条区:', !!modal.querySelector('.kb-related'));
}
console.log('errors:', errors.length ? errors : '无');
// 独立验证 API
const direct = await fetch('http://127.0.0.1:8000/api/rules/spells?limit=500');
const data = await direct.json();
console.log('直接请求 spells 数量:', Array.isArray(data) ? data.length : data);
process.exit(errors.length ? 1 : 0);
