/* 学派筛选功能验证:点击"塑能"按钮后检查分组过滤。 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const root = process.cwd();
const require = createRequire(path.join(root, 'scripts', 'vendor', 'package.json'));
const { JSDOM } = require('jsdom');

const html = fs.readFileSync(path.join(root, 'anko', 'static', 'index.html'), 'utf-8');
const dom = new JSDOM(html, { url: 'http://127.0.0.1:8000/', runScripts: 'outside-only', pretendToBeVisual: true });
const { window } = dom;
window.fetch = (url, opts) => fetch(String(url).startsWith('http') ? url : 'http://127.0.0.1:8000' + url, opts);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const errors = [];
window.addEventListener('error', e => errors.push('error: ' + (e.message || e.error)));
window.eval(fs.readFileSync(path.join(root, 'anko/static/vendor/vue.global.prod.js'), 'utf-8'));
const apiSrc = fs.readFileSync(path.join(root, 'anko/static/js/api.js'), 'utf-8');
const appSrc = fs.readFileSync(path.join(root, 'anko/static/js/app.js'), 'utf-8');
window.eval(apiSrc + '\n;\n' + appSrc);
await sleep(2500);

const doc = window.document;
const kbNav = [...doc.querySelectorAll('.side-item')].find(el => el.textContent.includes('知识库'));
kbNav.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(800);

// 点击"塑能"学派按钮
const schoolButtons = [...doc.querySelectorAll('.kb-filters .small-tab')];
const suButton = schoolButtons.find(b => b.textContent.trim() === '塑能');
console.log('找到塑能按钮:', !!suButton);
suButton.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(400);

const groups = [...doc.querySelectorAll('.kb-group')];
let total = 0;
let bad = [];
for (const g of groups) {
  const cards = [...g.querySelectorAll('.kb-entry')];
  total += cards.length;
  for (const c of cards) {
    if (!c.textContent.includes('塑能')) bad.push(c.textContent.trim().slice(0, 20));
  }
}
console.log('点击塑能后分组数:', groups.length);
console.log('塑能法术总数:', total);
console.log('含非塑能法术:', bad.length ? bad : '无');
console.log('errors:', errors.length ? errors : '无');
process.exit(0);
