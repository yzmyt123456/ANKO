/* 施法资源回归(页内仪表盘):战士-奥法骑士子职施法表。 */
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
window.eval(fs.readFileSync(path.join(root, 'anko/static/js/api.js'), 'utf-8') + ';\n' + fs.readFileSync(path.join(root, 'anko/static/js/app.js'), 'utf-8'));
await sleep(2200);
const doc = window.document;
const click = el => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const kbNav = [...doc.querySelectorAll('.side-item')].find(el => el.textContent.includes('知识库'));
click(kbNav);
await sleep(300);
const classTab = [...doc.querySelectorAll('.kb-tabs .kb-tab')].find(el => el.textContent.includes('职业'));
click(classTab);
await sleep(2600);
const frame = doc.querySelector('.cls-frame');
const navFighter = [...(frame ? frame.querySelectorAll('.pf-cls') : [])].find(b =>
  (b.querySelector('.cls-nav-zh') || { textContent: '' }).textContent.trim() === '战士');
if (navFighter) { click(navFighter); await sleep(1800); }
const f2 = doc.querySelector('.cls-frame');
console.log('战士页:', !!f2 && f2.querySelector('.cls-title').textContent.includes('战士'));
const subCards = f2 ? [...f2.querySelectorAll('.kb-subclass-card')] : [];
console.log('子职名:', subCards.map(c => (c.querySelector('.kb-subclass-name') || { textContent: '?' }).textContent.trim()).join(' | '));
const ek = subCards.find(c => c.textContent.includes('奥法骑士'));
const champion = subCards.find(c => c.textContent.includes('勇士'));
console.log('奥法骑士有施法资源折叠:', !!ek && !!ek.querySelector('.kb-spell-table'));
if (ek) {
  const cell = [...ek.querySelectorAll('.kb-sg-lv')];
  console.log('奥法骑士网格行数:', cell.length);
  console.log('原书施法表图:', (ek.querySelector('.kb-spell-table img') || { getAttribute: () => '无' }).getAttribute('src'));
}
console.log('勇士无施法资源折叠:', champion ? !champion.querySelector('.kb-spell-table') : '?');
// 法师:进度表应出现蓝色"环位数字"圆与青色"戏法/法术"圆
const navWiz = [...f2.querySelectorAll('.pf-cls')].find(b =>
  (b.querySelector('.cls-nav-zh') || { textContent: '' }).textContent.trim() === '法师');
click(navWiz);
await sleep(1500);
const wf = doc.querySelector('.cls-frame');
const sd = wf.querySelectorAll('.pf-lanes .pf-node.kind-spell');
console.log('法师蓝色环位圆点数:', sd.length, '| 首个圆内容:', sd[0] ? sd[0].textContent.trim() : '');
console.log('法师青色法术圆点数:', wf.querySelectorAll('.pf-lanes .pf-node.kind-known').length);
console.log('errors:', errors.length ? errors : '无');
process.exit(0);

