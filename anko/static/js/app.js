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
    this.loadAll();
    this.loadTemplates();
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
    dndStatKeys: ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'],
    dndStatLabels: { strength: '力量', dexterity: '敏捷', constitution: '体质', intelligence: '智力', wisdom: '感知', charisma: '魅力' },

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
