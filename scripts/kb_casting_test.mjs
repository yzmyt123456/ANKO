/* 施法资源 UI 回归(战士-奥法骑士子职施法表) */
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
await sleep(2200);

const cards = [...doc.querySelectorAll('.kb-race-card')];
const card = cards.find(c => (c.querySelector('.kb-race-name') || { textContent: '' }).textContent.trim() === '战士');
console.log('匹配卡:', card ? (card.querySelector('.kb-race-name') || {}).textContent.trim() : '无');
click(card);
await sleep(2000);

const m2 = doc.querySelector('.kb-modal');
console.log('战士弹窗:', !!m2);
if (m2) {
  const subCards = [...m2.querySelectorAll('.kb-subclass-card')];
  console.log('子职卡数:', subCards.length);
  console.log('子职名:', subCards.map(c => (c.querySelector('.kb-subclass-name') || { textContent: '?' }).textContent.trim()).join(' | '));
  const ek = subCards.find(c => c.textContent.includes('奥法骑士'));
  const champion = subCards.find(c => c.textContent.includes('勇士'));
  console.log('奥法骑士有施法资源折叠:', !!ek);
  if (ek) {
    console.log('奥法骑士有施法资源折叠:', !!ek.querySelector('.kb-spell-table'));
    const grid = ek.querySelector('.kb-spell-grid');
    const cell = grid ? [...ek.querySelectorAll('.kb-sg-lv')] : [];
    console.log('奥法骑士网格行数:', cell.length);
    const img = ek.querySelector('.kb-spell-table img');
    console.log('原书施法表图:', img ? img.getAttribute('src') : '无');
  }
  console.log('勇士无施法资源折叠:', champion ? !champion.querySelector('.kb-spell-table') : '?');
  const rawJson = [...m2.querySelectorAll('.kb-sub-feat summary')].some(s => s.textContent.includes('施法资源表'));
  console.log('能力列表未出现 JSON 施法资源表:', !rawJson);
}
console.log('errors:', errors.length ? errors : '无');
process.exit(0);
