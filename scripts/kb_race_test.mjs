/* 种族页回归:知识库-种族 tab 直接呈现种族仪表盘(左侧 9 种族切换)。 */
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
const raceTab = [...doc.querySelectorAll('.kb-tabs .kb-tab')].find(el => el.textContent.includes('种族'));
click(raceTab);
await sleep(2600);
const frame = doc.querySelector('.cls-frame');
console.log('种族 tab 页内仪表盘(无弹窗):', !!frame);
console.log('种族导航数:', frame ? frame.querySelectorAll('.cls-nav-item').length : 0);
console.log('无外层卡片网格:', !doc.querySelector('.kb-class-page .kb-race-grid'));
if (!frame) { console.log('errors:', errors.length ? errors : '无'); process.exit(0); }
const humanNav = [...frame.querySelectorAll('.cls-nav-item')].find(b => b.textContent.includes('人类'));
if (humanNav) { click(humanNav); await sleep(1600); }
const f2 = doc.querySelector('.cls-frame');
const active = f2.querySelector('.cls-nav-item.on .cls-nav-zh');
console.log('切换到人类:', active ? active.textContent.trim() : '?');
console.log('特质区块:', !!f2.querySelector('.kb-race-block-label'));
console.log('errors:', errors.length ? errors : '无');
process.exit(0);
