// Adapter: gives the desk page the same db / sample / downloads / user calls it has inside Claude,
// backed by this site's Azure API. Collections refresh every 60 s and right after your own writes.
(function(){
  const api = async (url, opts) => {
    const r = await fetch(url, Object.assign({ credentials: "same-origin", headers: { "content-type": "application/json" } }, opts));
    if (r.status === 401){ location.href = "/.auth/login/aad?post_login_redirect_uri=" + encodeURIComponent(location.pathname); throw { code: "unauthenticated" }; }
    if (r.status === 403){ const j = await r.json().catch(() => ({})); throw { code: "revoked", message: j.error || "Not allowed" }; }
    if (r.status === 204) return null;
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw { code: j.code || (r.status === 429 ? "rate_limited" : "upstream_error"), message: j.error || ("HTTP " + r.status) };
    return j;
  };
  const listeners = {};           // collection -> [fn]
  const snap = docs => ({ docs: docs.map(d => ({ id: d.id, exists: true, data: () => d.data })), size: docs.length, empty: !docs.length });
  async function refresh(c){
    const ls = listeners[c]; if (!ls || !ls.length) return;
    try { const j = await api("/api/data?c=" + encodeURIComponent(c)); ls.forEach(l => l.next(c === "meta" ? j.docs : snap(j.docs))); }
    catch(e){ ls.forEach(l => l.error && l.error(e)); }
  }
  setInterval(() => Object.keys(listeners).forEach(c => { if (c !== "meetings" && c !== "meta") refresh(c); }), 60000);
  setInterval(() => { refresh("meetings"); refresh("meta"); }, 15 * 60000);
  function docRef(path){
    const [c, id] = path.split("/");
    return {
      id, path,
      get: async () => { const j = await api(`/api/doc/${c}/${encodeURIComponent(id)}`); return { id, exists: !!j.exists, data: () => j.data }; },
      set: async (data) => { await api(`/api/doc/${c}/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(data) }); refresh(c); },
      update: async (data) => { await api(`/api/doc/${c}/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(data) }); refresh(c); },
      delete: async () => { await api(`/api/doc/${c}/${encodeURIComponent(id)}`, { method: "DELETE" }); refresh(c); },
      onSnapshot(next, error){
        const l = { next: docs => { const arr = Array.isArray(docs) ? docs : (docs && docs.docs || []).map(x => ({ id: x.id, data: x.data() })); const d = arr.find(x => x.id === id); next({ id, exists: !!d, data: () => d && d.data }); }, error };
        (listeners[c] ||= []).push(l); refresh(c); return () => { listeners[c] = listeners[c].filter(x => x !== l); };
      }
    };
  }
  const db = {
    doc: docRef,
    collection(c){
      return {
        path: c,
        doc: (id) => docRef(c + "/" + id),
        add: async (data) => { const j = await api(`/api/doc/${c}`, { method: "POST", body: JSON.stringify(data) }); refresh(c); return { id: j.id }; },
        onSnapshot(next, error){ const l = { next, error }; (listeners[c] ||= []).push(l); refresh(c); return () => { listeners[c] = listeners[c].filter(x => x !== l); }; }
      };
    }
  };
  const sample = async (prompt, opts) => {
    const j = await api("/api/generate", { method: "POST", body: JSON.stringify({ prompt }), signal: opts && opts.signal });
    if (opts && opts.onText) opts.onText({ text: j.text, delta: j.text });
    return { text: j.text, truncated: !!j.truncated, modelTierApplied: "default" };
  };
  const downloads = {
    save: async ({ filename, data }) => {
      const blob = data instanceof Blob ? data : new Blob([data]);
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = filename;
      document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1500);
      return {};
    }
  };
  let usersP = null;
  const usersInfo = () => (usersP ||= api("/api/users").catch(() => ({ me: null, users: {} })));
  const nameFromEmail = e => e ? e.split("@")[0].split(/[._]/).map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(" ") : "Someone";
  const user = {
    id: async () => (await usersInfo()).me?.id || null,
    profiles: async (ids) => { usersP = null; const u = (await usersInfo()).users || {}; return Object.fromEntries(ids.map(id => [id, { id, name: nameFromEmail(u[id]) }])); }
  };
  const caps = { db, sample, downloads, user };
  window.claude = { use: async (n) => caps[n] || null };
})();
