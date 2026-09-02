/* 真实渲染测试:用 jsdom 加载页面,模拟点击人物卡,检查详情弹窗内容。
 * 用法: node scripts/render_test.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const root = process.cwd();
const require = createRequire(
  path.join(root, 'scripts', 'vendor', 'package.json')
);
const { JSDOM } = require('jsdom');

const html = fs.readFileSync(path.join(root, 'anko', 'static', 'index.html'), 'utf-8');
const dom = new JSDOM(html, {
  url: 'http://127.0.0.1:8000/',
  runScripts: 'outside-only',
  pretendToBeVisual: true,
});
const { window } = dom;

// 提供 fetch(相对路径拼到本地服务器)
window.fetch = (url, opts) => {
  const full = String(url).startsWith('http') ? url : 'http://127.0.0.1:8000' + url;
  return fetch(full, opts);
};

const sleep = ms => new Promise(r => setTimeout(r, ms));

// 执行脚本
window.eval(fs.readFileSync(path.join(root, 'anko/static/vendor/vue.global.prod.js'), 'utf-8'));
console.log('Vue 已加载:', typeof window.Vue !== 'undefined');
window.eval(fs.readFileSync(path.join(root, 'anko/static/js/api.js'), 'utf-8'));
console.log('API 已加载:', typeof window.API !== 'undefined');

// 捕获错误
const errors = [];
window.addEventListener('error', e => errors.push('window error: ' + e.message));
window.console.error = (...a) => { errors.push('console.error: ' + a.join(' ')); };
// 追踪 fetch
const fetches = [];
const origFetch = window.fetch;
window.fetch = (url, opts) => {
  fetches.push(String(url));
  return origFetch(url, opts);
};

// 拼接执行 api.js + app.js(同一作用域,const 可见,等同浏览器全局脚本)
const apiSrc = fs.readFileSync(path.join(root, 'anko/static/js/api.js'), 'utf-8');
const appSrc = fs.readFileSync(path.join(root, 'anko/static/js/app.js'), 'utf-8');
window.eval(apiSrc + '\n;\n' + appSrc);
console.log('app.js 已执行');

// 等待数据加载
await sleep(2000);

console.log('errors:', errors.length ? errors : '无');
console.log('fetch 请求:', fetches.length ? fetches : '无');
const appEl = window.document.querySelector('#app');
console.log('#app 内容前300字符:', appEl.innerHTML.slice(0, 300).replace(/\s+/g, ' '));

const doc = window.document;

// 切换到"人物卡"页面
const navItems = [...doc.querySelectorAll('.side-item')];
const charNav = navItems.find(el => el.textContent.includes('人物卡'));
if (charNav) {
  charNav.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(600);
}
console.log('当前视图已切换到人物卡:', !!doc.querySelector('.c-card') || doc.querySelector('.empty-state') !== null);

const cards = doc.querySelectorAll('.c-card');
console.log('人物卡卡片数:', cards.length);
console.log('卡片六属性元素 .stat-mini 数量:', doc.querySelectorAll('.c-card .stat-mini').length);
if (cards.length) {
  console.log('卡片含"力量":', cards[0].textContent.includes('力量'));
  console.log('卡片含"敏捷":', cards[0].textContent.includes('敏捷'));
}

if (cards.length === 0) {
  console.log('❌ 没有人物卡卡片');
  process.exit(1);
}

// 模拟点击第一张卡
cards[0].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(500);

const modal = doc.querySelector('.char-detail-modal');
console.log('详情弹窗已打开:', !!modal);
if (modal) {
  const text = modal.textContent;
  for (const kw of ['力量', '敏捷', '体质', '智力', '感知', '魅力', '技能鉴定', '豁免鉴定', '阵营', 'HP']) {
    console.log(`  弹窗含「${kw}」:`, text.includes(kw));
  }
} else {
  console.log('❌ 弹窗未打开!');
}

// 尝试触发一次属性鉴定
const statCell = doc.querySelector('.dnd-stat-cell');
if (statCell) {
  statCell.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(600);
  const checkResult = doc.querySelector('.check-result');
  console.log('鉴定结果区出现:', !!checkResult);
  if (checkResult) console.log('  鉴定内容:', checkResult.textContent.slice(0, 60));
}
process.exit(0);
