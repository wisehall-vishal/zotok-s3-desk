const { TableClient } = require("@azure/data-tables");
const fs = require("fs");
const path = require("path");

const WRITABLE = new Set(["notes", "drafts", "flags", "txmeta", "transcripts"]);
const TABLE = "desk";
let table = null;
async function getTable() {
  if (table) return table;
  const conn = process.env.STORAGE_CONNECTION;
  if (!conn) throw Object.assign(new Error("STORAGE_CONNECTION is not set"), { status: 500 });
  table = TableClient.fromConnectionString(conn, TABLE);
  try { await table.createTable(); } catch (e) { if (e.statusCode !== 409) throw e; }
  return table;
}

// Signed-in user from Static Web Apps; only the allowed domain gets data.
function principal(request) {
  const raw = request.headers.get("x-ms-client-principal");
  if (!raw) return null;
  try {
    const p = JSON.parse(Buffer.from(raw, "base64").toString("utf8"));
    return { id: p.userId, email: (p.userDetails || "").toLowerCase() };
  } catch { return null; }
}
function allowed(user) {
  const dom = (process.env.ALLOWED_DOMAIN || "zotok.ai").toLowerCase();
  return !!(user && user.email.endsWith("@" + dom));
}
function guard(request) {
  const u = principal(request);
  if (!u) return { error: { status: 401, jsonBody: { error: "Sign in first." } } };
  if (!allowed(u)) return { error: { status: 403, jsonBody: { error: "This desk is only for ZoTok accounts." } } };
  return { user: u };
}

// Daily snapshot pushed to the repo by the Claude sync.
let deskCache = null, deskMtime = 0;
function desk() {
  const f = path.join(__dirname, "..", "..", "data", "desk.json");
  const st = fs.statSync(f);
  if (!deskCache || st.mtimeMs !== deskMtime) { deskCache = JSON.parse(fs.readFileSync(f, "utf8")); deskMtime = st.mtimeMs; }
  return deskCache;
}

// Table entities: PartitionKey = collection, RowKey = doc id, body JSON split across p0..p9 (<= 30k chars each).
const CHUNK = 30000;
function toEntity(coll, id, data) {
  const s = JSON.stringify(data);
  if (s.length > CHUNK * 10) throw Object.assign(new Error("Document too large"), { status: 413 });
  const e = { partitionKey: coll, rowKey: id, n: 0 };
  for (let i = 0; i * CHUNK < s.length; i++) { e["p" + i] = s.slice(i * CHUNK, (i + 1) * CHUNK); e.n = i + 1; }
  return e;
}
function fromEntity(e) { let s = ""; for (let i = 0; i < (e.n || 0); i++) s += e["p" + i] || ""; return s ? JSON.parse(s) : {}; }
function validId(s) { return typeof s === "string" && /^[A-Za-z0-9_\-.~:@+]{1,200}$/.test(s); }

module.exports = { WRITABLE, getTable, guard, desk, toEntity, fromEntity, validId };
