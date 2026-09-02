/* 种族知识卡验证:切到种族 tab,点人类,检查故事/特质/细分渲染。 */
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
window.addEventListener('error', e => errors.push('window error: ' + (e.message || e.error)));
const origErr = window.console.error;
window.console.error = (...a) => errors.push('console.error: ' + a.join(' '));
window.eval(fs.readFileSync(path.join(root, 'anko/static/vendor/vue.global.prod.js'), 'utf-8'));
window.eval(fs.readFileSync(path.join(root, 'anko/static/js/api.js'), 'utf-8') + ';\n' + fs.readFileSync(path.join(root, 'anko/static/js/app.js'), 'utf-8'));
await sleep(2500);

// 直接测试 raceParts 逻辑
const racePartsCheck = content => {
  const out = { story: '', intro: '' };
  const map = { 故事: 'story', 简介: 'intro' };
  let cur = null;
  for (const line of String(content || '').split('\n')) {
    const m = line.match(/^§(故事|简介)$/);
    if (m) { cur = map[m[1]]; continue; }
    if (cur && out[cur] !== undefined) out[cur] += (out[cur] ? '\n' : '') + line;
  }
  return out;
};

const doc = window.document;
const kbNav = [...doc.querySelectorAll('.side-item')].find(el => el.textContent.includes('知识库'));
kbNav.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(400);
const raceTab = [...doc.querySelectorAll('.kb-tabs .kb-tab')].find(el => el.textContent.includes('种族'));
console.log('找到种族 tab:', !!raceTab);
raceTab.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(2500);
const cards = [...doc.querySelectorAll('.kb-race-card')];
console.log('种族卡数:', cards.length, '| 有总览块:', !!doc.querySelector('.kb-race-guide'));
const human = cards.find(c => c.textContent.includes('人类'));
console.log('找到人类卡:', !!human);
human.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
await sleep(1500);
const modal = doc.querySelector('.kb-modal');
console.log('弹窗打开:', !!modal);
if (modal) {
  console.log('标题:', modal.querySelector('h2') ? modal.querySelector('h2').textContent.trim() : '无');
  const blocks = [...modal.querySelectorAll('.kb-race-block')];
  const lastBlock = blocks[blocks.length - 1];
  console.log('内容块数:', blocks.length, '| 最后一块含故事折叠:', !!(lastBlock && lastBlock.querySelector('.kb-story')));
  console.log('故事折叠块存在:', !!modal.querySelector('.kb-story'));
  const traits = [...modal.querySelectorAll('.kb-trait-title')].map(e => e.textContent.trim());
  console.log('特质卡:', traits.join(' | '));
  const subs = [...modal.querySelectorAll('.kb-race-sub summary')].map(e => e.textContent.trim().slice(0, 20));
  console.log('细分卡数:', subs.length, '示例:', subs.slice(0, 4).join(' | '));
  const modalText = modal.textContent;
  console.log('含大族谱:', modalText.includes('大族谱'), '含人类特质:', modalText.includes('人类特质'));
}
console.log('errors:', errors.length ? errors : '无');
process.exit(0);
