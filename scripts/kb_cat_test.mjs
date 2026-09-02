/* 知识库分类浏览验证:切到规则页,点"种族"分类,点开条目详情。 */
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
// 切到知识库(默认自动进入玩家手册,分类行应出现)
// 直接 fetch 验证 API
const directCats = await fetch('http://127.0.0.1:8000/api/rules/categories?book=DND_5E_玩家手册CN').then(r => r.json());
console.log('直连分类数:', Array.isArray(directCats) ? directCats.length : JSON.stringify(directCats).slice(0, 80));
const directKnow = await fetch('http://127.0.0.1:8000/api/rules/knowledge?book=DND_5E_玩家手册CN&limit=5').then(r => r.json());
console.log('直连知识条数:', Array.isArray(directKnow) ? directKnow.length : JSON.stringify(directKnow).slice(0, 80));

const kbNav = [...doc.querySelectorAll('.side-item')].find(el => el.textContent.includes('知识库'));
kbNav.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(400);
const kbTabs = [...doc.querySelectorAll('.kb-tab')];
const ruleTab = kbTabs.find(el => el.textContent.includes('规则'));
ruleTab.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(2500);

const sel = doc.querySelector('.kb-book-select');
console.log('书籍下拉:', sel ? '存在' : '无', sel ? sel.value : '');
const viewHtml = doc.querySelector('.view') ? doc.querySelector('.view').innerHTML.slice(0, 500).replace(/\s+/g, ' ') : '无view';
console.log('规则区前500:', viewHtml);

const cats = [...doc.querySelectorAll('.kb-filters .small-tab')].map(el => el.textContent.trim());
console.log('初始分类按钮:', cats.join(' | ') || '(空)');

// 等待分类按钮出现(最多 10 秒)
let raceBtn = null;
for (let i = 0; i < 10; i++) {
  await sleep(1000);
  raceBtn = [...doc.querySelectorAll('.kb-filters .small-tab')].find(el => el.textContent.trim() === '种族');
  if (raceBtn) break;
}
console.log('找到种族按钮:', !!raceBtn);
const allSmall = [...doc.querySelectorAll('.kb-tab')].map(el => el.textContent.trim());
console.log('kb-tab 全部:', allSmall.join(' | ') || '(空)');
if (!raceBtn) {
  const kb = doc.querySelector('.kb-kno-list, .view');
  console.log('知识库区前400:', kb ? kb.innerHTML.slice(0, 400).replace(/\s+/g, ' ') : '无');
}
raceBtn = raceBtn || ([...doc.querySelectorAll('.kb-tab')].find(el => el.textContent.trim() === '种族'));
if (raceBtn) {
  raceBtn.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(1500);
  const cards = [...doc.querySelectorAll('.kb-kno-card')];
  console.log('种族卡片数:', cards.length);
  if (cards.length) {
    console.log('首卡:', cards[0].textContent.trim().slice(0, 40));
    cards[0].dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    await sleep(1200);
    const modal = doc.querySelector('.kb-modal');
    console.log('详情弹窗打开:', !!modal, modal ? '含内容:' + (modal.textContent.length > 200) : '');
  }
}
console.log('errors:', errors.length ? errors : '无');
process.exit(0);
