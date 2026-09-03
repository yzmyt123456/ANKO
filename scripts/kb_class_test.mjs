/* 职业页回归:知识库-职业 tab 直接呈现仪表盘;切野蛮人→狂战士道途→等级面板。 */
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
console.log('职业 tab 页内仪表盘(无弹窗):', !!frame);
console.log('无外层卡片网格:', !doc.querySelector('.kb-class-page .kb-race-grid'));
if (!frame) { console.log('errors:', errors.length ? errors : '无'); process.exit(0); }
console.log('职业导航数:', frame.querySelectorAll('.cls-nav-item').length);
console.log('右上属性卡行:', frame.querySelectorAll('.pf-stat-row').length);
console.log('右侧本职基础卡:', frame.querySelectorAll('.pf-side-card').length);
const barbNav = [...frame.querySelectorAll('.cls-nav-item')].find(b => b.textContent.includes('野蛮人'));
if (barbNav) { click(barbNav); await sleep(1600); }
const title = frame.querySelector('.cls-title');
console.log('当前职业:', title ? title.textContent.trim() : '无');
const lvBtn = num => [...frame.querySelectorAll('.kb-lv-btn')].find(b =>
  (b.querySelector('.cls-lv-num') || { textContent: '' }).textContent.trim() === String(num));
lvBtn(5).dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(250);
console.log('野蛮人 Lv5 面板:', frame.querySelector('.kb-lv-panel-head').textContent.trim());
const berserk = [...frame.querySelectorAll('.pf-sub')].find(b => b.textContent.includes('狂战士'));
click(berserk);
await sleep(300);
console.log('狂战士面板:', frame.querySelector('.kb-lv-panel-head').textContent.trim());
lvBtn(6).dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(250);
console.log('狂战士 Lv6 含无我狂暴:', frame.querySelector('.kb-lv-panel').textContent.includes('无我狂暴'));
// 子职表连续性:狂战士 Lv4 无专属能力时回显主职"属性值提升"
lvBtn(4).dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(250);
console.log('狂战士 Lv4 回显主职ASI:', frame.querySelector('.kb-lv-panel').textContent.includes('属性值提升'));
// 图腾武者道途:子职施法识别(兽语术仪式)
const totem = [...frame.querySelectorAll('.pf-sub')].find(b => b.textContent.includes('图腾'));
click(totem);
await sleep(300);
console.log('图腾头部子职施法:', frame.querySelector('.pf-stat').textContent.includes('动物交谈术'));
console.log('子职卡数:', frame.querySelectorAll('.kb-subclass-card').length);
console.log('errors:', errors.length ? errors : '无');
process.exit(0);
