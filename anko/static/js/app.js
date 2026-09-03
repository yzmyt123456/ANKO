/* ============================================================
 * 安科创作平台 前端逻辑(Vue 3)
 * ============================================================ */
const { createApp } = Vue;

const PAGE_META = {
  home: ['首页', '平台概览与快捷入口'],
  characters: ['人物卡', '管理你的角色与属性'],
  stories: ['剧情', '创作与管理安科故事线'],
  maids: ['骰娘', '召唤与定制你的专属骰娘'],
  rolls: ['掷骰台', '让命运之骰为你发声'],
  knowledge: ['知识库', '本地 DND 规则:法术 / 怪物 / 规则 / 地图'],
  settings: ['设置', 'AI 助手等系统配置'],
};

// 职业规则元信息:主属性 / 施法类型(9 环全施法、半施法至5环、战系无表)/ 施法关键属性
const CLASS_META = {
  '野蛮人': { main: '力量 · 体质', cast: 'none', ab: '', note: '纯战系;道途不提供法术' },
  '吟游诗人': { main: '魅力', cast: 'full9', ab: '魅力', note: '9 环全施法者' },
  '牧师': { main: '感知', cast: 'full9', ab: '感知', note: '9 环全施法者' },
  '德鲁伊': { main: '感知', cast: 'full9', ab: '感知', note: '9 环全施法者' },
  '战士': { main: '力量 或 敏捷', cast: 'none', ab: '', note: '纯战系;奥法骑士子职可施法(1/3)' },
  '武僧': { main: '敏捷 · 感知', cast: 'none', ab: '', note: '纯战系;武艺/气非法术' },
  '圣武士': { main: '力量 · 魅力', cast: 'half5', ab: '魅力', note: '半施法者(法术至 5 环)' },
  '游侠': { main: '敏捷 · 感知', cast: 'half5', ab: '感知', note: '半施法者(法术至 5 环)' },
  '游荡者': { main: '敏捷', cast: 'none', ab: '', note: '纯战系;秘法骗子子职可施法(1/3)' },
  '术士': { main: '魅力', cast: 'full9', ab: '魅力', note: '9 环全施法者' },
  '邪术师': { main: '魅力', cast: 'full9', ab: '魅力', note: '9 环全施法者(法术位至5环+秘法秘仪至9环)' },
  '法师': { main: '智力', cast: 'full9', ab: '智力', note: '9 环全施法者' },
};
// 战系职业中获得 1/3 施法的子职业(至 4 环)
const SUBCAST_META = {
  '奥法骑士': { cast: '1/3', ab: '智力', ring: '法术至 4 环' },
  '秘法骗子': { cast: '1/3', ab: '智力', ring: '法术至 4 环' },
  '诡术师': { cast: '1/3', ab: '智力', ring: '法术至 4 环' },
};

createApp({
  data() {
    return {
      view: 'home',
      tabs: [
        { id: 'home', icon: '🏠', label: '首页' },
        { id: 'characters', icon: '📇', label: '人物卡', badge: 'characters' },
        { id: 'stories', icon: '📖', label: '剧情', badge: 'stories' },
        { id: 'maids', icon: '🧝', label: '骰娘', badge: 'maids' },
        { id: 'rolls', icon: '🎲', label: '掷骰台' },
        { id: 'knowledge', icon: '📚', label: '知识库' },
        { id: 'settings', icon: '⚙️', label: '设置' },
      ],

      // 人物卡
      characters: [],
      templates: [],
      charForm: { name: '', title: '', avatar: '', bio: '', template: 'default', stats: {}, attrRows: [], tagsText: '' },
      charModal: { open: false, editing: false },
      charDetail: null,
      checkResult: null,
      checkLoading: false,
      // AI 快速建档
      aiText: '',
      aiLoading: false,
      aiDraft: null,
      aiError: '',
      // DND 词条词典
      glossary: [],
      // DND 六属性键与中文名(响应式,供模板渲染)
      dndStatKeys: ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'],
      dndStatLabels: { strength: '力量', dexterity: '敏捷', constitution: '体质', intelligence: '智力', wisdom: '感知', charisma: '魅力' },

      // 剧情
      stories: [],
      storyForm: { title: '', description: '', tagsText: '', maid_id: null },
      storyModal: { open: false },
      currentStory: null,
      entries: [],
      entryForm: { chapter: '', content: '', character_ids: [] },

      // 骰娘
      maids: [],
      maidForm: { name: '', personality: '', greeting: '', default_expression: '1d100', settings: { threshold: 50, crit_success: 95, crit_fail: 5 }, modifierAdd: 0 },
      maidModal: { open: false, editing: false },

      // 掷骰
      quickDice: ['1d100', 'd20', '2d6', '1d6', '4d6'],
      rollExpr: '1d100',
      rollMaidId: null,
      rollSave: true,
      rollResult: null,
      rollHistory: [],

      // 全局
      toast: '',
      toastType: 'success',
      _toastTimer: null,

      // AI 配置
      aiConfig: { enabled: false, base_url: '', model: '', timeout: 120, api_key_masked: '', has_api_key: false },
      aiApiKey: '',
      aiTestResult: null,
      aiTestLoading: false,

      // AI 生成角色
      genCharModal: { open: false },
      genHint: '',
      genTemplate: 'dnd5e',
      genLoading: false,
      genDraft: null,
      genError: '',
      genText: '',
      genPartial: '',
      genController: null,
      genProcess: '',

      // 知识库
      kbTab: 'spells',
      kbQuery: '',
      kbSpells: [],
      kbMonsters: [],
      kbKnowledge: [],
      kbRaces: [],
      kbRacePage: null,
      kbRaceResults: [],
      kbClasses: [],
      kbClsPage: null,
      kbClsLv: 1,
      kbClsView: 'base',
      clsChoice: {},
      kbMaps: [],
      kbBooks: [],
      kbBook: '',
      kbCategory: '',
      kbCategories: [],
      kbLevel: '',
      kbSchool: '',
      kbLoading: false,
      kbDetail: null,
    };
  },

  computed: {
    stats() {
      return {
        characters: this.characters.length,
        stories: this.stories.length,
        maids: this.maids.length,
        rolls: this.rollHistory.length,
      };
    },
    dndTemplate() {
      return this.templateById('dnd5e') || { groups: [], checks: [] };
    },
    kbTabLabel() {
      return ({ spells: '法术', races: '种族', classes: '职业', monsters: '怪物', knowledge: '规则', maps: '地图' })[this.kbTab] || '';
    },
    kbLevels() {
      return ['', '戏法', '1 环', '2 环', '3 环', '4 环', '5 环', '6 环', '7 环', '8 环', '9 环'];
    },
    kbCatOrder() {
      // 玩家手册分类按章节顺序展示
      const order = ['创建角色', '种族', '职业', '背景', '装备', '自定义选项',
        '属性值应用', '冒险', '战斗', '施法', '状态', '诸神', '位面', '生物资料', '导言', '附录'];
      return [...this.kbCategories].sort((a, b) => {
        const ia = order.indexOf(a), ib = order.indexOf(b);
        return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
      });
    },
    pageTitle() {
      if (this.view === 'storyDetail') return this.currentStory ? this.currentStory.title : '剧情详情';
      return (PAGE_META[this.view] || ['', ''])[0];
    },
    pageDesc() {
      if (this.view === 'storyDetail') return '撰写与回顾这条故事线的每一段剧情';
      return (PAGE_META[this.view] || ['', ''])[1];
    },
  },

  mounted() {
    // 支持 ?view=knowledge 等深链接(便于验证与分享)
    try {
      const v = new URLSearchParams(window.location.search).get('view');
      if (v && PAGE_META[v]) this.view = v;
    } catch (e) { /* 忽略 */ }
    this.loadAll();
    this.loadTemplates();
    this.loadGlossary();
    this.loadAiConfig();
    this.loadKnowledge();
    // 词条点击事件委托:本地词条打开内部详情
    document.addEventListener('click', (e) => {
      const a = e.target.closest('.term-link');
      if (a) {
        e.preventDefault();
        this.openLocalTerm(a.dataset.term, a.dataset.type);
      }
    });
  },

  methods: {
    /* ---------------- 通用 ---------------- */
    switchView(view) {
      this.view = view;
      if (view === 'stories') this.currentStory = null;
      window.scrollTo({ top: 0 });
    },

    itemCount(key) {
      const counts = {
        characters: this.characters.length,
        stories: this.stories.length,
        maids: this.maids.length,
      };
      return counts[key] || 0;
    },

    showToast(msg, type = 'success') {
      this.toast = msg;
      this.toastType = type;
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => { this.toast = ''; }, 2600);
    },

    fmtTime(iso) {
      if (!iso) return '';
      const d = new Date(iso);
      const p = n => String(n).padStart(2, '0');
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    },

    truncate(s, n) {
      s = String(s || '');
      return s.length > n ? s.slice(0, n) + '…' : s;
    },

    avatarColor(name) {
      const colors = ['#6d5ae0', '#3b82f6', '#2e9e6b', '#f59e0b', '#e05263', '#0891b2', '#7c3aed', '#db2777'];
      let h = 0;
      for (const ch of String(name)) h = (h * 31 + ch.codePointAt(0)) % 997;
      return { background: colors[h % colors.length] };
    },

    async loadAll() {
      await Promise.all([
        this.loadCharacters(),
        this.loadStories(),
        this.loadMaids(),
        this.loadRollHistory(),
      ]);
    },

    /* ---------------- 人物卡模板 ---------------- */
    async loadTemplates() {
      try {
        this.templates = await API.get('/templates');
        // 预加载 dnd5e 模板详情(鉴定项)
        const dnd = this.templates.find(t => t.id === 'dnd5e');
        if (dnd) {
          const detail = await API.get('/templates/dnd5e');
          this.templates = this.templates.map(t => (t.id === 'dnd5e' ? detail : t));
        }
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    templateById(id) {
      return this.templates.find(t => t.id === id) || null;
    },

    dndStatLabel(key) { return this.dndStatLabels[key] || key; },

    dndModifier(score) {
      const n = parseInt(score, 10);
      if (Number.isNaN(n)) return 0;
      return Math.floor((n - 10) / 2);
    },

    fmtMod(m) {
      return m > 0 ? `+${m}` : String(m);
    },

    setCharTemplate(tid) {
      this.charForm.template = tid;
      this.checkResult = null;
      // 初始化模板字段
      const tpl = this.templateById(tid);
      const stats = {};
      if (tpl) {
        for (const g of tpl.groups) {
          for (const f of g.fields) {
            if (f.key === 'attributes') continue;
            stats[f.key] = f.type === 'dnd_score' || f.type === 'number' ? 0 : '';
          }
        }
      }
      this.charForm.stats = stats;
    },

    dndSkillChecks() {
      const tpl = this.templateById('dnd5e');
      return tpl ? tpl.checks.filter(c => c.kind === 'skill') : [];
    },

    dndSaveChecks() {
      const tpl = this.templateById('dnd5e');
      return tpl ? tpl.checks.filter(c => c.kind === 'save') : [];
    },

    hasValue(v) {
      return v !== null && v !== undefined && String(v).trim() !== '';
    },

    async dndCheck(key, kind) {
      if (!this.charDetail) return;
      this.checkLoading = true;
      this.checkResult = null;
      try {
        this.checkResult = await API.post(`/characters/${this.charDetail.id}/checks`, { kind, key });
      } catch (e) {
        this.showToast(e.message, 'error');
      } finally {
        this.checkLoading = false;
      }
    },

    /* ---------------- DND 词条词典 ---------------- */
    async loadGlossary() {
      try {
        this.glossary = await API.get('/glossary');
      } catch (e) { /* 词典加载失败不阻塞页面 */ }
    },

    _escHtml(s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    },

    _escRegex(s) {
      return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    },

    linkify(text) {
      if (!text) return '';
      let s = this._escHtml(text);
      const glossary = this.glossary || [];
      if (!glossary.length) return s;
      const sorted = [...glossary].sort((a, b) => b.name.length - a.name.length);
      const placeholders = [];
      let counter = 0;
      for (const e of sorted) {
        const re = new RegExp(this._escRegex(e.name), 'g');
        s = s.replace(re, () => {
          const token = `\u0000WK${counter++}\u0000`;
          placeholders.push({ token, entry: e });
          return token;
        });
      }
      for (const p of placeholders) {
        const e = p.entry;
        if (e.local) {
          // 本地知识库收录:点击打开内部详情
          s = s.replace(p.token,
            `<a class="wiki-link term-link" href="#" data-term="${this._escHtml(e.name)}" data-type="${this._escHtml(e.local_type || '')}">${e.name}</a>`);
        } else {
          s = s.replace(p.token,
            `<a class="wiki-link" href="${e.url}" target="_blank" rel="noopener">${e.name}</a>`);
        }
      }
      return s;
    },

    dndStatWiki(key) {
      const label = this.dndStatLabel(key);
      const e = (this.glossary || []).find(x => x.name === label);
      return e ? e.url : '';
    },

    /* ---------------- 人物卡 ---------------- */
    async loadCharacters() {
      try {
        this.characters = await API.get('/characters');
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    attrsToRows(attributes) {
      return Object.entries(attributes || {}).map(([key, value]) => ({ key, value: String(value) }));
    },

    rowsToAttrs(rows) {
      const attrs = {};
      for (const row of rows) {
        const k = (row.key || '').trim();
        if (k) attrs[k] = row.value;
      }
      return attrs;
    },

    topAttrs(c, n) {
      return Object.fromEntries(Object.entries(c.attributes || {}).slice(0, n));
    },

    openCharModal(c) {
      this.charModal.open = true;
      this.charModal.editing = !!c;
      this.charModal.editingId = c ? c.id : null;
      this.checkResult = null;
      // 重置 AI 面板
      this.aiText = '';
      this.aiDraft = null;
      this.aiError = '';
      if (c) {
        this.charForm = {
          name: c.name,
          title: c.title || '',
          avatar: c.avatar || '',
          bio: c.bio || '',
          template: c.template || 'default',
          stats: { ...(c.stats || {}) },
          attrRows: this.attrsToRows(c.attributes),
          tagsText: (c.tags || []).join(', '),
        };
      } else {
        this.charForm = { name: '', title: '', avatar: '', bio: '', template: 'default', stats: {}, attrRows: [], tagsText: '' };
        this.setCharTemplate('default');
      }
    },

    closeCharModal() { this.charModal.open = false; },

    /* ---------------- 知识库 ---------------- */
    async loadKnowledge() {
      this.kbLoading = true;
      try {
        const [spells, monsters, maps, books] = await Promise.all([
          API.get('/rules/spells?limit=500'),
          API.get('/rules/monsters?limit=500'),
          API.get('/rules/maps'),
          API.get('/rules/books'),
        ]);
        this.kbSpells = spells;
        this.kbMonsters = monsters;
        this.kbMaps = maps;
        this.kbBooks = books;
        this.kbTab = 'spells';
      } catch (e) { this.showToast(e.message, 'error'); } finally {
        this.kbLoading = false;
      }
    },

    kbSwitch(tab) {
      this.kbTab = tab;
      this.kbQuery = '';
      this.kbLevel = '';
      this.kbSchool = '';
      this.kbCategory = '';
      if (tab === 'knowledge' && !this.kbKnowledge.length) this.loadKbKnowledge();
      if (tab === 'races') {
        // 种族页直接进入仪表盘(左侧可切换 9 大种族),默认打开首个
        const boot = async () => {
          if (!this.kbRaces.parents || !this.kbRaces.parents.length) await this.loadKbRaces();
          if (!this.kbRacePage && this.kbRaces.parents && this.kbRaces.parents.length) {
            await this.openKbRace(this.kbRaces.parents[0]);
          }
        };
        boot();
      }
      if (tab === 'classes') {
        // 职业页直接进入仪表盘(内置 12 职业导航),默认打开首个职业
        const boot = async () => {
          if (!this.kbClasses.length) await this.loadKbClasses();
          if (!this.kbClsPage && this.kbClasses.length) await this.openKbClass(this.kbClasses[0]);
        };
        boot();
      }
    },

    async loadKbClasses() {
      // 玩家手册职业 → 职业知识卡列表
      try {
        if (!this.kbBooks.length) {
          this.kbBooks = await API.get('/rules/books');
        }
        const book = this.kbBooks.includes('DND_5E_玩家手册CN') ? 'DND_5E_玩家手册CN' : '';
        const q = book ? `&book=${encodeURIComponent(book)}` : '';
        this.kbClasses = await API.get(`/rules/knowledge?category=${encodeURIComponent('职业')}&kind=class${q}&limit=30`);
      } catch (e) { /* 静默 */ }
    },

    async openKbClass(k) {
      // 职业改为页内仪表盘展示(知识库-职业 tab),左侧导航切换即调用本方法
      this.kbTab = 'classes';
      this.kbClsLv = 1;
      this.kbClsView = 'base';
      this.clsChoice = {};
      try {
        const data = await API.get(`/rules/knowledge/${k.id}`);
        this.kbClsPage = data;
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    classZh(t) {
      // '野蛮人 Barbarian' → 野蛮人
      return String(t || '').split(' ')[0].trim();
    },
    clsMeta(data) {
      return CLASS_META[this.classZh(data.title)] || {};
    },
    castLabel(data) {
      const m = this.clsMeta(data);
      if (!m.cast) return '';
      if (m.cast === 'full9') return '9 环施法者';
      if (m.cast === 'half5') return '半施法(至 5 环)';
      return '战系(无施法)';
    },
    subCastTag(title) {
      const t = this.classZh(title);
      for (const key of Object.keys(SUBCAST_META)) {
        if (t.includes(key) || key.includes(t)) {
          const m = SUBCAST_META[key];
          return `施法 1/3 · ${m.ab}`;
        }
      }
      return '';
    },
    classTableImg(data) {
      const c = (data && data.children || []).find(x => x.kind === 'class_levels');
      return c ? c.image : '';
    },
    classLevelRows(data) {
      const lv = (data && data.children || []).find(c => c.kind === 'class_levels');
      if (!lv) return [];
      try {
        const parsed = JSON.parse(lv.content);
        const arr = Array.isArray(parsed) ? parsed : (parsed.levels || []);
        return arr.filter(r => r.lv >= 1 && r.lv <= 20);
      } catch (e) { return []; }
    },
    classBases(data) {
      return (data && data.children || []).filter(c => c.kind === 'class_base');
    },
    classFeats(data) {
      // 核心职业特性(排除创建/快速建卡引导卡,引导卡单独展示)
      return (data && data.children || []).filter(
        c => c.kind === 'class_feature'
          && !(c.title.includes('创建') || c.title === '快速建卡 Quick Build' || c.title === '快速建卡')
      );
    },
    classGuide(data) {
      // 创建该职业:创建职业(起源构思)+ 快速建卡(属性/背景/装备建议)
      return (data && data.children || []).filter(
        c => c.kind === 'class_feature'
          && (c.title.includes('创建') || c.title.includes('快速建卡'))
      );
    },
    sortedClassFeats(data) {
      const lvOf = c => this.classFeatLv(c, data);
      const list = this.classFeats(data).slice();
      list.sort((a, b) => {
        const la = lvOf(a), lb = lvOf(b);
        if (la == null && lb == null) return 0;
        if (la == null) return 1;
        if (lb == null) return -1;
        return la - lb;
      });
      return list;
    },
    classSubs(data) {
      return (data && data.children || []).filter(c => c.kind === 'subclass');
    },
    classFeatLv(feat, data) {
      // 特性等级:表匹配 → 正文'第 N 级'
      if (!feat) return null;
      const zh = this.classZh(feat.title);
      const rows = this.classLevelRows(data);
      for (const r of rows) {
        for (const f of String(r.feats || '').split(/[，,、/]/)) {
          if (f.trim() === zh) return r.lv;
        }
      }
      const m = String(feat.content || '').match(/第\s*(\d{1,2})\s*级/);
      return m ? +m[1] : null;
    },
    subFeatLv(c, children) {
      // 子职业能力等级:文本'第 N 级'优先;无标注(如狂野魔法浪涌)向后取首个已定级兄弟的最小级
      const m = String(c && c.content || '').match(/第\s*(\d{1,2})\s*级/);
      if (m) return +m[1];
      const arr = children || [];
      const i = arr.indexOf(c);
      const later = arr.slice(i + 1).map(x => {
        const mm = String(x && x.content || '').match(/第\s*(\d{1,2})\s*级/);
        return mm ? +mm[1] : null;
      }).filter(n => n != null);
      return later.length ? Math.min(...later) : null;
    },
    classViews(data) {
      // 视图切换:原职业 + 各子职业
      const out = [{ id: 'base', name: this.classZh(data.title), sub: false }];
      for (const s of this.classSubs(data)) {
        out.push({ id: 's' + s.id, name: this.classZh(s.title), sub: true });
      }
      return out;
    },
    classViewName(data) {
      const v = this.classViews(data).find(x => x.id === this.kbClsView);
      return v ? v.name : this.classZh(data.title);
    },
    classViewFeats(data, viewId, lv) {
      // 返回所选(职业/子职)在 lv 级获得的能力
      if (viewId === 'base') {
        const names = this.classLevelRowFeats(lv, data);
        const isSubLevel = names.some(n => /^选择/.test(n) || /特性$/.test(n));
        return {
          names,
          cards: this.classLevelFeats(lv, data),
          isSubLevel,
        };
      }
      const s = this.classSubs(data).find(x => 's' + x.id === viewId);
      const cards = (s && s.children || []).filter(c => this.subFeatLv(c, s.children) === lv);
      if (cards.length) {
        return { names: cards.map(c => this.classZh(c.title)), cards };
      }
      // 子职在该级没有专属能力时,回显主职该级成长(如属性值提升),使 1-20 表连续
      return this.classViewFeats(data, 'base', lv);
    },
    classNextSubLv(data, viewId, lv) {
      const s = this.classSubs(data).find(x => 's' + x.id === viewId);
      if (!s) return null;
      const lvs = (s.children || [])
        .map(c => this.subFeatLv(c, s.children))
        .filter(n => n && n > lv);
      return lvs.length ? Math.min(...lvs) : null;
    },
    classSubChoices(data, lv) {
      // 各子职业在该等级提供的能力(用于职业视图'选择XX/XX特性'占位级)
      return this.classSubs(data)
        .map(s => ({
          s,
          cards: (s.children || []).filter(c => this.subFeatLv(c, s.children) === lv),
        }))
        .filter(o => o.cards.length);
    },
    classLevelList() {
      return Array.from({ length: 20 }, (_, i) => i + 1);
    },
    classRowFeatsTitle(lv, data) {
      const r = this.classLevelRows(data).find(x => x.lv === lv);
      if (!r) return `Lv${lv}`;
      return `Lv${lv} 熟练${r.prof || ''}：${r.feats}`;
    },
    classRowProf(lv, data) {
      const r = this.classLevelRows(data).find(x => x.lv === lv);
      return r ? (r.prof || '') : '';
    },
    classRowResParts(lv, data) {
      const r = this.classLevelRows(data).find(x => x.lv === lv);
      if (!r || !r.res) return [];
      return Object.entries(r.res).map(([k, v]) => (v === null ? `${k} —` : `${k} ${v}`));
    },
    classSpellCols(data) {
      const rows = this.classLevelRows(data).filter(r => r.res && Object.keys(r.res).length);
      const cols = [];
      for (const r of rows) {
        for (const k of Object.keys(r.res)) {
          if (!cols.includes(k)) cols.push(k);
        }
      }
      return cols;
    },
    classSpellLevels(data) {
      return this.classLevelRows(data)
        .filter(r => r.res && Object.keys(r.res).length)
        .map(r => r.lv);
    },
    classSpellVal(data, lv, col) {
      const r = this.classLevelRows(data).find(x => x.lv === lv);
      if (!r || !r.res || !(col in r.res)) return '';
      return r.res[col] === null ? '—' : r.res[col];
    },
    classRowChips(lv, data) {
      return this.classViewFeats(data, this.kbClsView, lv).names.slice(0, 3);
    },
    classResMini(lv, data) {
      // 等级格内的小法术徽:key→短标签,title→完整说明(仿 PF 每级圆形图标)
      const r = this.classLevelRows(data).find(x => x.lv === lv);
      if (!r || !r.res) return [];
      const short = k => k
        .replace('已知戏法', '戏法').replace('已知法术', '法术')
        .replace('已知祈唤', '祈唤').replace('法术位环阶', '环阶');
      const full = (k, v) => `${k} ${v === null ? '—' : v}`;
      const items = [];
      let overflow = false;
      for (const [k, v] of Object.entries(r.res)) {
        if (v === null || v === 0) continue;
        if (items.length >= 6) { overflow = true; break; }
        items.push({ s: short(k) + v, t: full(k, v) });
      }
      if (overflow) items.push({ s: '+…', t: '展开施法资源查看全部' });
      return items;
    },
    clsCastKind(data) {
      const cols = this.classSpellCols(data);
      if (!cols.length) return '';
      if (cols.includes('术法点')) return '自发施法';
      if (cols.includes('法术位')) return '契约魔法';
      if (cols.includes('已知法术')) return '自发施法';
      return '准备施法';
    },
    clsCastLevel(data) {
      const cast = this.clsMeta(data).cast;
      if (cast === 'full9') return '9 环';
      if (cast === 'half5') return '5 环';
      return '—';
    },
    pfTreeClasses(data) {
      // 树排序:当前职业置顶(便于展示其变体),其余职业随后
      if (!data || !this.kbClasses.length) return this.kbClasses || [];
      return [data, ...this.kbClasses.filter(c => c.id !== data.id)];
    },
    pfPickSub(s) {
      this.kbClsView = 's' + s.id;
      this.clsChoice = {};
    },
    clsActiveRes(data) {
      // 施法资源数据源:选中子职且其带独立施法表(奥法骑士/诡术师)→用子职表;否则用主职表
      if (this.kbClsView !== 'base') {
        const s = this.classSubs(data).find(x => 's' + x.id === this.kbClsView);
        if (s && this.classLevelRows(s).some(r => r.res)) return s;
      }
      return data;
    },
    clsSubCast(s) {
      const t = this.classZh(s.title);
      for (const key of Object.keys(SUBCAST_META)) {
        if (t.includes(key) || key.includes(t)) return SUBCAST_META[key];
      }
      return null;
    },
    clsMartialLabel(data) {
      if (this.kbClsView === 'base') return '战系(主职)';
      const s = this.classSubs(data).find(x => 's' + x.id === this.kbClsView);
      if (!s) return '战系(主职)';
      const zh = this.classZh(s.title);
      return zh.includes('图腾') || this.clsSubCast(s) ? '子职施法' : '战系(子职)';
    },
    clsMartialNote(data) {
      if (this.kbClsView === 'base') return '主职无施法';
      const s = this.classSubs(data).find(x => 's' + x.id === this.kbClsView);
      if (!s) return '主职无施法';
      const zh = this.classZh(s.title);
      if (zh.includes('图腾')) return '动物交谈术·野兽感知(仪式施法)';
      const m = this.clsSubCast(s);
      if (m) return `施法 ${m.cast} · ${m.ab} · ${m.ring}`;
      return '该子职无额外法术';
    },
    clsCastText(data) {
      const c = this.clsMeta(data).cast;
      if (c === 'full9') return '9 环施法者';
      if (c === 'half5') return '半施法(至5环)';
      return '纯战系';
    },
    clsHitDie(data) {
      for (const b of this.classBases(data)) {
        if (b.title.includes('生命')) {
          const m = String(b.content || '').match(/\d+\s*d\s*\d+/);
          if (m) return m[0].replace(/\s+/g, '');
        }
      }
      return '—';
    },
    clsCurrentIntro(data) {
      if (this.kbClsView !== 'base') {
        const s = this.classSubs(data).find(x => 's' + x.id === this.kbClsView);
        if (s && s.content) return s.content.trim();
      }
      return '';
    },
    clsReflow(text) {
      // 合并 PDF 抽取时保留的"软折行"(中文字间不留空格),段落间仍保留空行
      if (!text) return text;
      const re = /[\u4e00-\u9fff，。；：！？、…—·（）0-9A-Za-z]/;
      return text
        .split(/\n\s*\n+/)
        .map(para => {
          const lines = para.split(/\n+/).map(s => s.trim());
          let out = lines[0] || '';
          for (const ln of lines.slice(1)) {
            const prev = out.slice(-1);
            const next = ln.slice(0, 1);
            out += (re.test(prev) && re.test(next)) ? ln : ' ' + ln;
          }
          return out;
        })
        .join('\n\n');
    },
    subFeatures(sub) {
      return (sub && sub.children || []).filter(x => x.kind !== 'class_levels');
    },
    classLevelRowFeats(lv, data) {
      const row = this.classLevelRows(data).find(r => r.lv === lv);
      if (!row) return [];
      return String(row.feats || '').split(/[，,、/]/).map(s => s.trim()).filter(Boolean);
    },
    classLevelFeats(lv, data) {
      // 某等级获得的特性卡(表名匹配)
      const row = this.classLevelRows(data).find(r => r.lv === lv);
      if (!row) return [];
      const feats = this.classFeats(data);
      const names = String(row.feats || '').split(/[，,、/]/).map(s => s.trim()).filter(Boolean);
      return names
        .map(n => feats.find(f => {
          const zh = this.classZh(f.title);
          return n === zh || n.includes(zh) || zh.includes(n);
        }))
        .filter(Boolean)
        .slice(0, 6);
    },

    async loadKbRaces() {
      // 玩家手册种族 → 分层知识卡列表(仅父卡)
      try {
        if (!this.kbBooks.length) {
          this.kbBooks = await API.get('/rules/books');
        }
        const book = this.kbBooks.includes('DND_5E_玩家手册CN') ? 'DND_5E_玩家手册CN' : '';
        const q = book ? `&book=${encodeURIComponent(book)}` : '';
        const parents = await API.get(`/rules/knowledge?category=${encodeURIComponent('种族')}&kind=race${q}&limit=50`);
        this.kbRaces = { parents };
      } catch (e) { /* 静默 */ }
    },

    async openKbRace(r) {
      // 种族改为页内仪表盘展示(知识库-种族 tab),左侧导航切换即调用本方法
      this.kbTab = 'races';
      try {
        const data = await API.get(`/rules/knowledge/${r.id}`);
        this.kbRacePage = data;
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    nice(content) {
      // 合并 PDF 硬换行(28字/行)为自然段落;保留空行分段,让文本随容器折行
      if (!content) return '';
      return String(content).replace(/\r/g, '')
        .split(/\n{2,}/)
        .map(p => p.replace(/\s*\n\s*/g, ''))
        .join('\n\n')
        .trim();
    },
    isLongContent(c) {
      return (c || '').length > 700;
    },
    contentChars(c) {
      return Math.round((c || '').length);
    },
    previewLong(c) {
      return this.nice(c).slice(0, 220) + '…';
    },
    featOptions(content) {
      // 能力文本内“多选一段”(如图腾精魄的熊/鹰/狼)拆成选项卡
      // 排除 d100 随机表等表格式内容(走整表折叠)
      if (String(content || '').match(/\d{2}~\d{2}/g)) {
        if ((String(content).match(/\d{2}~\d{2}/g) || []).length >= 3) return null;
      }
      const lines = String(content || '').split('\n').map(s => s.trim()).filter(Boolean);
      const idx = [];
      lines.forEach((l, i) => {
        if (/^[\u4e00-\u9fff·]{1,8}\s+[A-Za-z][A-Za-z'’\- ]*?。/.test(l)) idx.push(i);
      });
      if (idx.length < 2) return null;
      const intro = lines.slice(0, idx[0]).join('');
      const options = idx.map((s, i) => {
        const e = idx[i + 1] || lines.length;
        const text = lines.slice(s, e).join('');
        const head = (text.split('。')[0] || '').trim();
        return { name: (head.match(/^[\u4e00-\u9fff·]+/) || [''])[0], text };
      });
      return { intro, options };
    },
    raceParts(content) {
      // 解析父卡 content:§故事 / §简介
      const out = { story: '', intro: '' };
      const map = { 故事: 'story', 简介: 'intro' };
      let cur = null;
      for (const line of String(content || '').split('\n')) {
        const m = line.match(/^§(故事|简介)$/);
        if (m) { cur = map[m[1]]; continue; }
        if (cur && out[cur] !== undefined) out[cur] += (out[cur] ? '\n' : '') + line;
      }
      return out;
    },
    raceTraits(children) {
      // 每条特质独立的知识卡(kind=trait),直接展开为字段
      if (!children) return [];
      return children.filter(c => c.kind === 'trait');
    },
    raceSubs(children) {
      // 亚种与文化细分 → 下级知识卡
      if (!children) return [];
      return children.filter(c => c.kind !== 'trait');
    },

    async loadKbKnowledge() {
      // 规则库浏览:默认选玩家手册(含分类)
      try {
        if (!this.kbBooks.length) {
          this.kbBooks = await API.get('/rules/books');
        }
        if (!this.kbBook) {
          this.kbBook = this.kbBooks.includes('DND_5E_玩家手册CN')
            ? 'DND_5E_玩家手册CN'
            : (this.kbBooks[0] || '');
          if (!this.kbBook) return;
        }
        await this.browseBook();
      } catch (e) { /* 静默 */ }
    },

    async kbSearch() {
      const q = this.kbQuery.trim();
      if (!q) return;
      this.kbLoading = true;
      try {
        if (this.kbTab === 'spells') {
          this.kbSpells = await API.get(`/rules/spells?q=${encodeURIComponent(q)}&limit=200`);
        } else if (this.kbTab === 'monsters') {
          this.kbMonsters = await API.get(`/rules/monsters?q=${encodeURIComponent(q)}&limit=200`);
        } else if (this.kbTab === 'races') {
          this.kbRaceResults = await API.get(`/rules/search?q=${encodeURIComponent(q)}&category=${encodeURIComponent('种族')}&limit=40`);
        } else if (this.kbTab === 'knowledge') {
          const bookParam = this.kbBook ? `&book=${encodeURIComponent(this.kbBook)}` : '';
          const catParam = this.kbCategory ? `&category=${encodeURIComponent(this.kbCategory)}` : '';
          this.kbKnowledge = await API.get(`/rules/search?q=${encodeURIComponent(q)}${bookParam}${catParam}&limit=30`);
        }
      } catch (e) { this.showToast(e.message, 'error'); } finally {
        this.kbLoading = false;
      }
    },

    async browseBook() {
      // 按书籍浏览:带分类的书(玩家手册)同时加载分类列表
      this.kbCategory = '';
      this.kbCategories = [];
      if (!this.kbBook) { this.kbKnowledge = []; return; }
      this.kbLoading = true;
      try {
        const [cats, items] = await Promise.all([
          API.get(`/rules/categories?book=${encodeURIComponent(this.kbBook)}`),
          API.get(`/rules/knowledge?book=${encodeURIComponent(this.kbBook)}&limit=200`),
        ]);
        this.kbCategories = cats;
        this.kbKnowledge = items;
      } catch (e) { this.showToast(e.message, 'error'); } finally {
        this.kbLoading = false;
      }
    },

    async browseCategory(cat) {
      this.kbCategory = cat;
      if (!this.kbBook) return;
      this.kbLoading = true;
      try {
        const base = `/rules/knowledge?book=${encodeURIComponent(this.kbBook)}`;
        const url = cat
          ? `${base}&category=${encodeURIComponent(cat)}&limit=200`
          : `${base}&limit=200`;
        this.kbKnowledge = await API.get(url);
      } catch (e) { this.showToast(e.message, 'error'); } finally {
        this.kbLoading = false;
      }
    },

    async openKbKnowledge(k) {
      if (k.kind === 'race') { this.openKbRace(k); return; }
      if (k.content) {
        this.kbDetail = { type: 'knowledge', data: [k] };
        return;
      }
      try {
        const full = await API.get(`/rules/knowledge/${k.id}`);
        if (full.kind === 'race') { this.kbDetail = { type: 'race', data: full }; return; }
        this.kbDetail = { type: 'knowledge', data: [full] };
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    async openLocalTerm(name, type) {
      if (type === 'spell') {
        const data = await API.get(`/rules/spells/${encodeURIComponent(name)}`);
        this.kbDetail = { type: 'spell', data };
      } else if (type === 'monster') {
        const data = await API.get(`/rules/monsters/${encodeURIComponent(name)}`);
        this.kbDetail = { type: 'monster', data };
      } else {
        const data = await API.get(`/rules/search?q=${encodeURIComponent(name)}&limit=3`);
        if (data.length && data[0].kind === 'race') {
          const full = await API.get(`/rules/knowledge/${data[0].id}`);
          this.kbDetail = { type: 'race', data: full };
        } else {
          this.kbDetail = { type: 'knowledge', data };
        }
      }
    },

    openKbItem(item) {
      if (item.level !== undefined) {
        this.kbDetail = { type: 'spell', data: item };
      } else {
        this.kbDetail = { type: 'monster', data: item };
      }
    },

    kbSpellsGrouped() {
      // 按环阶分组(可选过滤:环阶 / 学派)
      const groups = {};
      for (const s of this.kbSpells) {
        if (this.kbLevel && ((s.level === 0 ? '戏法' : `${s.level} 环`) !== this.kbLevel)) continue;
        if (this.kbSchool && s.school !== this.kbSchool) continue;
        const key = s.level === 0 ? '戏法' : `${s.level} 环`;
        (groups[key] = groups[key] || []).push(s);
      }
      return Object.entries(groups).sort((a, b) => {
        const n = k => (k === '戏法' ? 0 : parseInt(k));
        return n(a[0]) - n(b[0]);
      });
    },

    kbMonsterTypes() {
      // 怪物类型列表(去重)
      const types = new Set();
      for (const m of this.kbMonsters) {
        const t = (m.meta || '').split(/[,，]/)[0].trim();
        if (t) types.add(t);
      }
      return [...types].sort();
    },

    // Wiki 交叉链接:相关词条
    relatedSpells(spell) {
      return this.kbSpells
        .filter(s => s.school === spell.school && s.name !== spell.name)
        .slice(0, 6);
    },
    relatedMonsters(mon) {
      const type = (mon.meta || '').split(/[,，]/)[0].trim();
      if (!type) return [];
      return this.kbMonsters
        .filter(x => x.meta && x.meta.split(/[,，]/)[0].trim() === type && x.name !== mon.name)
        .slice(0, 6);
    },
    spellSchoolList() {
      const schools = new Set(this.kbSpells.map(s => s.school).filter(Boolean));
      return [...schools].sort();
    },
    componentsExplain(comp) {
      // 法术成分标注含义:V=言语 S=姿势 M=材料
      if (!comp) return '';
      const map = { V: '言语', S: '姿势', M: '材料' };
      const mat = (comp.match(/[（(]([^）)]*)[）)]/) || [])[1] || '';
      const body = comp.replace(/[（(][^）)]*[）)]/, '');
      let out = body.replace(/[VSM]/g, ch => ch + '(' + (map[ch] || ch) + ')');
      if (mat) out += '(' + mat + ')';
      return out;
    },
    kbMonstersGrouped(type) {
      return this.kbMonsters.filter(m => (m.meta || '').split(/[,，]/)[0].trim() === type);
    },

    /* ---------------- AI 配置 ---------------- */
    async loadAiConfig() {
      try {
        this.aiConfig = await API.get('/ai/config');
      } catch (e) { /* 静默 */ }
    },

    async saveAiConfig() {
      try {
        const body = {
          enabled: !!this.aiConfig.enabled,
          base_url: (this.aiConfig.base_url || '').trim(),
          model: (this.aiConfig.model || '').trim(),
          timeout: Number(this.aiConfig.timeout) || 30,
        };
        if (this.aiApiKey.trim()) body.api_key = this.aiApiKey.trim();
        this.aiConfig = await API.put('/ai/config', body);
        this.aiApiKey = '';
        this.showToast('AI 配置已保存 ✅');
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    async testAi() {
      this.aiTestLoading = true;
      this.aiTestResult = null;
      try {
        // 携带表单当前填写(未保存)的配置直接测试
        const body = {
          enabled: !!this.aiConfig.enabled,
          base_url: (this.aiConfig.base_url || '').trim(),
          model: (this.aiConfig.model || '').trim(),
          timeout: Number(this.aiConfig.timeout) || 30,
        };
        if (this.aiApiKey.trim()) body.api_key = this.aiApiKey.trim();
        this.aiTestResult = await API.post('/ai/test', body);
      } catch (e) {
        this.aiTestResult = { ok: false, error: e.message };
      } finally {
        this.aiTestLoading = false;
      }
    },

    /* ---------------- AI 快速建档 ---------------- */
    attrsPreview(attrs) {
      return Object.entries(attrs).map(([k, v]) => `${k} ${v}`).join(' · ');
    },

    async aiParse() {
      if (!this.aiText.trim()) { this.showToast('请先粘贴角色描述文本', 'error'); return; }
      this.aiLoading = true;
      this.aiError = '';
      this.aiDraft = null;
      try {
        this.aiDraft = await API.post('/ai/parse-character', {
          text: this.aiText.trim(),
          template: this.charForm.template,
        });
      } catch (e) {
        this.aiError = e.message;
      } finally {
        this.aiLoading = false;
      }
    },

    aiApply() {
      if (!this.aiDraft) return;
      const d = this.aiDraft;
      if (d.name) this.charForm.name = d.name;
      if (d.title) this.charForm.title = d.title;
      if (d.bio) this.charForm.bio = d.bio;
      if (d.template === 'dnd5e' && d.stats) {
        this.charForm.template = 'dnd5e';
        // 合并 AI 解析的 stats
        const merged = { ...this.charForm.stats };
        for (const [k, v] of Object.entries(d.stats)) {
          if (v !== '' && v !== 0 && v !== null && v !== undefined) merged[k] = v;
        }
        this.charForm.stats = merged;
      } else if (Object.keys(d.attributes || {}).length) {
        this.charForm.attrRows = this.attrsToRows(d.attributes);
      }
      if (d.tags.length) {
        this.charForm.tagsText = d.tags.join(', ');
      }
      this.aiDraft = null;
      this.showToast('已填入表单,请检查后保存 ✅');
    },

    openCharDetail(c) {
      this.charDetail = c;
      this.checkResult = null;
    },

    async saveChar() {
      const body = {
        name: this.charForm.name.trim(),
        title: this.charForm.title.trim() || null,
        avatar: this.charForm.avatar.trim() || null,
        bio: this.charForm.bio.trim() || null,
        template: this.charForm.template || 'default',
        attributes: this.rowsToAttrs(this.charForm.attrRows),
        tags: this.charForm.tagsText.split(/[,，]/).map(s => s.trim()).filter(Boolean),
      };
      if (body.template === 'dnd5e') {
        body.stats = { ...this.charForm.stats };
      }
      try {
        if (this.charModal.editing) {
          await API.put(`/characters/${this.charModal.editingId}`, body);
          this.showToast('人物卡已更新 ✅');
        } else {
          await API.post('/characters', body);
          this.showToast('人物卡创建成功 ✨');
        }
        this.closeCharModal();
        this.charDetail = null;
        await this.loadCharacters();
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    async deleteChar(c) {
      if (!confirm(`确定删除人物卡「${c.name}」吗?`)) return;
      try {
        await API.del(`/characters/${c.id}`);
        if (this.charDetail && this.charDetail.id === c.id) this.charDetail = null;
        this.showToast('已删除');
        await this.loadCharacters();
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    /* ---------------- AI 生成角色(骰点创建法) ---------------- */
    openGenCharModal() {
      if (!this.currentStory) { this.showToast('请先打开一个故事线', 'error'); return; }
      this.genCharModal.open = true;
      this.genHint = '';
      this.genDraft = null;
      this.genError = '';
      this.genText = '';
      this.genPartial = '';
      this.genProcess = '';
    },

    closeGenCharModal() {
      if (this.genController) { this.genController.abort(); this.genController = null; }
      this.genCharModal.open = false;
    },

    buildStoryContext() {
      // 组装故事上下文:标题 + 简介 + 最近剧情
      const parts = [];
      if (this.currentStory) {
        parts.push(`故事标题:${this.currentStory.title}`);
        if (this.currentStory.description) {
          parts.push(`故事简介:${this.currentStory.description}`);
        }
      }
      if (this.entries.length) {
        const recent = this.entries.slice(-3).map(e => e.content).join('\n');
        parts.push(`已写剧情(节选):\n${recent.slice(0, 1200)}`);
      }
      return parts.join('\n\n');
    },

    async generateChar() {
      // 若从断点继续,不清空已显示文本;否则清空
      if (!this.genPartial) {
        this.genText = '';
      }
      this.genLoading = true;
      this.genError = '';
      this.genDraft = null;
      this.genController = new AbortController();
      const prevLen = this.genText.length; // 已有文本长度(断点续传时)
      try {
        const resp = await fetch('/api/ai/generate-character/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            story_context: this.buildStoryContext(),
            hint: this.genHint.trim(),
            template: this.genTemplate,
            partial: this.genPartial || '',
          }),
          signal: this.genController.signal,
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error((err.detail && (typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))) || ('HTTP ' + resp.status));
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const events = buf.split('\n\n');
          buf = events.pop();
          for (const ev of events) {
            if (!ev.startsWith('data:')) continue;
            let obj;
            try { obj = JSON.parse(ev.slice(5).trim()); } catch (e) { continue; }
            if (obj.type === 'delta') {
              // 只追加新增的部分(断点续传时 AI 可能补全而非重写)
              this.genText += obj.text;
            } else if (obj.type === 'done') {
              this.genDraft = obj.draft;
              this.genProcess = obj.process || '';
              this.genPartial = '';
            } else if (obj.type === 'error') {
              this.genError = obj.message;
            }
          }
          if (this.$refs.genTextBox) this.$refs.genTextBox.scrollTop = this.$refs.genTextBox.scrollHeight;
        }
      } catch (e) {
        if (e.name === 'AbortError') {
          // 用户主动停止:保留当前文本作为断点
          this.genPartial = this.genText.slice(prevLen); // 本轮新生成的
        } else {
          this.genError = e.message;
        }
      } finally {
        this.genLoading = false;
        this.genController = null;
      }
    },

    stopGenChar() {
      if (this.genController) this.genController.abort();
    },

    resetGenChar() {
      this.genPartial = '';
      this.genText = '';
      this.genDraft = null;
      this.genError = '';
      this.genProcess = '';
    },

    async copyGenProcess() {
      const text = this.genProcess || this.genText;
      if (!text) return;
      try {
        await navigator.clipboard.writeText(text);
        this.showToast('创建过程已复制 📋');
      } catch (e) {
        // 降级:选中文本
        this.showToast('复制失败,可手动选择文本', 'error');
      }
    },

    renderProcess(text) {
      // 把过程文本中的 **选中项** 渲染为加粗(先转义再替换)
      if (!text) return '';
      let s = this._escHtml(text);
      s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      return s;
    },

    async saveGeneratedChar() {
      if (!this.genDraft) return;
      try {
        const body = {
          name: this.genDraft.name,
          title: this.genDraft.title || null,
          bio: this.genDraft.bio || null,
          template: this.genDraft.template || 'default',
          stats: this.genDraft.stats || {},
          attributes: this.genDraft.attributes || {},
          tags: this.genDraft.tags || [],
          extra: {},
        };
        if (this.genProcess) body.extra.creation_log = this.genProcess;
        const created = await API.post('/characters', body);
        // 自动加入当前剧情条目的登场人物
        if (!this.entryForm.character_ids.includes(created.id)) {
          this.entryForm.character_ids.push(created.id);
        }
        await this.loadCharacters();
        this.closeGenCharModal();
        this.showToast(`角色「${created.name}」已创建并登场 🎉`);
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    /* ---------------- 剧情 ---------------- */
    async loadStories() {
      try {
        this.stories = await API.get('/stories');
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    openStoryModal() { this.storyModal.open = true; },
    closeStoryModal() { this.storyModal.open = false; },

    async createStory() {
      const body = {
        title: this.storyForm.title.trim(),
        description: this.storyForm.description.trim() || null,
        tags: this.storyForm.tagsText.split(/[,，]/).map(s => s.trim()).filter(Boolean),
        maid_id: this.storyForm.maid_id,
      };
      try {
        const story = await API.post('/stories', body);
        this.storyForm = { title: '', description: '', tagsText: '', maid_id: null };
        this.closeStoryModal();
        this.showToast('故事线创建成功 📖');
        await this.loadStories();
        this.openStory(story);
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    async openStory(s) {
      this.currentStory = s;
      this.view = 'storyDetail';
      this.entryForm = { chapter: '', content: '', character_ids: [] };
      window.scrollTo({ top: 0 });
      try {
        this.entries = await API.get(`/stories/${s.id}/entries`);
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    charName(id) {
      const c = this.characters.find(x => x.id === id);
      return c ? c.name : `人物#${id}`;
    },

    toggleEntryChar(id) {
      const idx = this.entryForm.character_ids.indexOf(id);
      if (idx >= 0) this.entryForm.character_ids.splice(idx, 1);
      else this.entryForm.character_ids.push(id);
    },

    async addEntry() {
      const body = {
        chapter: this.entryForm.chapter.trim() || null,
        content: this.entryForm.content,
        character_ids: this.entryForm.character_ids,
      };
      try {
        await API.post(`/stories/${this.currentStory.id}/entries`, body);
        this.entryForm = { chapter: '', content: '', character_ids: [] };
        this.showToast('剧情已保存 ✍️');
        this.entries = await API.get(`/stories/${this.currentStory.id}/entries`);
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    /* ---------------- 骰娘 ---------------- */
    async loadMaids() {
      try {
        this.maids = await API.get('/maids');
        if (this.rollMaidId === null && this.maids.length) {
          this.rollMaidId = this.maids[0].id;
        }
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    openMaidModal(m) {
      this.maidModal.open = true;
      this.maidModal.editing = !!m;
      this.maidModal.editingId = m ? m.id : null;
      this.maidForm = m
        ? {
            name: m.name,
            personality: m.personality || '',
            greeting: m.greeting || '',
            default_expression: m.default_expression || '1d100',
            settings: {
              threshold: m.settings.threshold ?? 50,
              crit_success: m.settings.crit_success ?? 95,
              crit_fail: m.settings.crit_fail ?? 5,
            },
            modifierAdd: 0,
          }
        : { name: '', personality: '', greeting: '', default_expression: '1d100', settings: { threshold: 50, crit_success: 95, crit_fail: 5 }, modifierAdd: 0 };
      if (m) {
        for (const mod of m.settings.modifiers || []) {
          if (mod.type === 'add') this.maidForm.modifierAdd = mod.value || 0;
        }
      }
    },

    closeMaidModal() { this.maidModal.open = false; },

    async saveMaid() {
      const settings = {
        threshold: this.maidForm.settings.threshold ?? 50,
        crit_success: this.maidForm.settings.crit_success ?? 95,
        crit_fail: this.maidForm.settings.crit_fail ?? 5,
      };
      if (this.maidForm.modifierAdd) {
        settings.modifiers = [{ type: 'add', value: this.maidForm.modifierAdd }];
      }
      const body = {
        name: this.maidForm.name.trim(),
        personality: this.maidForm.personality.trim() || null,
        greeting: this.maidForm.greeting.trim() || null,
        default_expression: this.maidForm.default_expression.trim() || '1d100',
        settings,
      };
      try {
        if (this.maidModal.editing) {
          await API.put(`/maids/${this.maidModal.editingId}`, body);
          this.showToast('骰娘已更新 ✅');
        } else {
          await API.post('/maids', body);
          this.showToast('骰娘召唤成功 🧝');
        }
        this.closeMaidModal();
        await this.loadMaids();
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    async deleteMaid(m) {
      if (!confirm(`确定删除骰娘「${m.name}」吗?`)) return;
      try {
        await API.del(`/maids/${m.id}`);
        this.showToast('已删除');
        await this.loadMaids();
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    /* ---------------- 掷骰 ---------------- */
    async loadRollHistory() {
      try {
        this.rollHistory = await API.get('/rolls');
      } catch (e) { this.showToast(e.message, 'error'); }
    },

    rollWithMaid(m) {
      this.rollMaidId = m.id;
      this.rollExpr = m.default_expression || '1d100';
      this.rollResult = null;
      this.switchView('rolls');
    },

    quickRoll(expr) {
      this.rollExpr = expr;
      this.doRoll();
    },

    async doRoll() {
      if (!this.rollExpr.trim()) { this.showToast('请输入骰子表达式', 'error'); return; }
      try {
        const resp = await API.post('/rolls', {
          expression: this.rollExpr.trim(),
          maid_id: this.rollMaidId,
          save: this.rollSave,
        });
        this.rollResult = { ...resp.record, description: resp.description };
        if (this.rollSave) await this.loadRollHistory();
      } catch (e) { this.showToast(e.message, 'error'); }
    },
  },
}).mount('#app');
