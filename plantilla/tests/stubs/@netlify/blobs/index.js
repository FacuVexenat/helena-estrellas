const m = globalThis.__mem || (globalThis.__mem = new Map());
export const getStore = () => ({
  async get(k, o) { const v = m.get(k); if (v == null) return null; return o && o.type === "json" ? JSON.parse(v) : v; },
  async set(k, v) { m.set(k, String(v)); }, async setJSON(k, v) { m.set(k, JSON.stringify(v)); } });
