/* 职业知识卡验证:切职业 tab,点野蛮人,检查等级表/特性/子职。 */
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
await sleep(2500);

const doc = window.document;
const kbNav = [...doc.querySelectorAll('.side-item')].find(el => el.textContent.includes('知识库'));
kbNav.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(400);
const classTab = [...doc.querySelectorAll('.kb-tabs .kb-tab')].find(el => el.textContent.includes('职业'));
console.log('找到职业 tab:', !!classTab);
classTab.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(2500);
const cards = [...doc.querySelectorAll('.kb-race-card')];
console.log('职业卡数:', cards.length);
const barb = cards.find(c => c.textContent.includes('野蛮人'));
console.log('找到野蛮人卡:', !!barb);
barb.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(1500);
const modal = doc.querySelector('.kb-modal');
console.log('弹窗打开:', !!modal);
if (modal) {
  console.log('标题:', modal.querySelector('h2') ? modal.querySelector('h2').textContent.trim() : '无');
  const bandBtns = modal.querySelectorAll('.kb-lv-btn').length;
  const panelHead = modal.querySelector('.kb-lv-panel-head');
  console.log('等级按钮数:', bandBtns);
  console.log('面板默认 Lv1:', panelHead ? panelHead.textContent.trim() : '无');
  // 点击 Lv5 按钮
  const lv5 = [...modal.querySelectorAll('.kb-lv-btn')].find(b => b.textContent.trim() === '5');
  lv5.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(300);
  const panel5 = modal.querySelector('.kb-lv-panel-head').textContent.trim();
  console.log('点击 Lv5 后面板:', panel5);
  console.log('面板含额外攻击:', modal.querySelector('.kb-lv-panel').textContent.includes('额外攻击'));
  console.log('含职业设定折叠:', !!modal.querySelector('.kb-story'));
  console.log('子职卡数:', modal.querySelectorAll('.kb-subclass-card').length);
  const subFeats = modal.querySelectorAll('.kb-sub-feat summary').length;
  console.log('子职能力条目:', subFeats);
  console.log('含狂暴卡:', modal.textContent.includes('狂暴 Rage'));
}
console.log('errors:', errors.length ? errors : '无');
process.exit(0);
