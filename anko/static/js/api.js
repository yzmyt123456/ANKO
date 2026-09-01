/* ============================================================
 * API 封装层:与后端 REST API 交互
 * ============================================================ */
const API = {
  async request(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) opts.body = JSON.stringify(body);

    const resp = await fetch('/api' + path, opts);
    if (resp.status === 204) return null;

    let data = null;
    try { data = await resp.json(); } catch (e) { /* 非 JSON 响应 */ }

    if (!resp.ok) {
      const detail = data && (typeof data.detail === 'string'
        ? data.detail : JSON.stringify(data.detail || resp.status));
      throw new Error(detail || '请求失败: HTTP ' + resp.status);
    }
    return data;
  },

  get(path) { return this.request('GET', path); },
  post(path, body) { return this.request('POST', path, body); },
  put(path, body) { return this.request('PUT', path, body); },
  del(path) { return this.request('DELETE', path); },
};
