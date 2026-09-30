const { app } = require("@azure/functions");
const { WRITABLE, getTable, guard, desk, fromEntity, toEntity, validId } = require("../lib/common");

// GET /api/data?c=meetings|meta|notes|drafts|flags|txmeta  -> {docs:[{id, data}]}
app.http("data", {
  methods: ["GET"], authLevel: "anonymous", route: "data",
  handler: async (request) => {
    const g = guard(request); if (g.error) return g.error;
    const c = request.query.get("c");
    if (c === "meetings") return { jsonBody: { docs: desk().meetings.map(m => ({ id: m.id, data: m })) } };
    if (c === "meta") return { jsonBody: { docs: [{ id: "sync", data: desk().meta || {} }] } };
    if (c === "briefs") return { jsonBody: { docs: Object.entries(desk().briefs || {}).map(([id, data]) => ({ id, data })) } };
    if (!WRITABLE.has(c) || c === "transcripts") return { status: 400, jsonBody: { error: "Unknown collection" } };
    const t = await getTable(); const docs = [];
    for await (const e of t.listEntities({ queryOptions: { filter: `PartitionKey eq '${c}'` } })) docs.push({ id: e.rowKey, data: fromEntity(e) });
    return { jsonBody: { docs } };
  }
});

// GET/PUT/DELETE /api/doc/{coll}/{id} ; POST /api/doc/{coll} (add with new id)
app.http("doc", {
  methods: ["GET", "PUT", "DELETE", "POST"], authLevel: "anonymous", route: "doc/{coll}/{id?}",
  handler: async (request) => {
    const g = guard(request); if (g.error) return g.error;
    const coll = request.params.coll; let id = request.params.id;
    if (!WRITABLE.has(coll)) return { status: 403, jsonBody: { error: "Read-only collection" } };
    const t = await getTable();
    if (request.method === "GET") {
      if (!validId(id)) return { status: 400, jsonBody: { error: "Bad id" } };
      try { const e = await t.getEntity(coll, id); return { jsonBody: { exists: true, data: fromEntity(e) } }; }
      catch (e) { if (e.statusCode === 404) return { jsonBody: { exists: false } }; throw e; }
    }
    if (request.method === "DELETE") {
      if (!validId(id)) return { status: 400, jsonBody: { error: "Bad id" } };
      try { await t.deleteEntity(coll, id); } catch (e) { if (e.statusCode !== 404) throw e; }
      return { status: 204 };
    }
    let body; try { body = await request.json(); } catch { return { status: 400, jsonBody: { error: "JSON body required" } }; }
    if (!body || typeof body !== "object" || Array.isArray(body)) return { status: 400, jsonBody: { error: "Object body required" } };
    if (request.method === "POST") id = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    if (!validId(id)) return { status: 400, jsonBody: { error: "Bad id" } };
    body.by = g.user.id; body.byEmail = g.user.email;
    try { await t.upsertEntity(toEntity(coll, id, body), "Replace"); }
    catch (e) { return { status: e.status || 500, jsonBody: { error: e.message } }; }
    await t.upsertEntity(toEntity("users", validId(g.user.id) ? g.user.id : "unknown", { email: g.user.email }), "Replace").catch(() => {});
    return { jsonBody: { id } };
  }
});

// GET /api/users -> {id: email}
app.http("users", {
  methods: ["GET"], authLevel: "anonymous", route: "users",
  handler: async (request) => {
    const g = guard(request); if (g.error) return g.error;
    const t = await getTable(); const out = {};
    for await (const e of t.listEntities({ queryOptions: { filter: "PartitionKey eq 'users'" } })) out[e.rowKey] = fromEntity(e).email;
    return { jsonBody: { me: g.user, users: out } };
  }
});
