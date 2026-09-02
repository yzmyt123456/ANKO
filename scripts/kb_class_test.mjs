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
  const switches = [...modal.querySelectorAll('.kb-cls-sel')].map(b => b.textContent.trim());
  console.log('切换选项:', switches.join(' | '));
  console.log('面板默认:', modal.querySelector('.kb-lv-panel-head').textContent.trim());
  // 原职业 Lv5
  const lv5 = [...modal.querySelectorAll('.kb-lv-btn')].find(b => b.textContent.trim() === '5');
  lv5.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(250);
  console.log('原职业 Lv5 面板:', modal.querySelector('.kb-lv-panel-head').textContent.trim());
  // 切到狂战士道途
  const berserk = [...modal.querySelectorAll('.kb-cls-sel')].find(b => b.textContent.includes('狂战士'));
  berserk.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(250);
  console.log('切狂战士后默认面板:', modal.querySelector('.kb-lv-panel-head').textContent.trim());
  const lv6 = [...modal.querySelectorAll('.kb-lv-btn')].find(b => b.textContent.trim() === '6');
  lv6.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(250);
  console.log('狂战士 Lv6 面板含无我狂暴:', modal.querySelector('.kb-lv-panel').textContent.includes('无我狂暴'));
  const lv5b = [...modal.querySelectorAll('.kb-lv-btn')].find(b => b.textContent.trim() === '5');
  lv5b.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
  await sleep(250);
  console.log('狂战士 Lv5 提示未获得:', modal.querySelector('.kb-lv-panel').textContent.includes('未获得新能力'));
  console.log('子职卡数:', modal.querySelectorAll('.kb-subclass-card').length);
}
console.log('errors:', errors.length ? errors : '无');
process.exit(0);
