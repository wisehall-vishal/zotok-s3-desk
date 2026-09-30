const { app } = require("@azure/functions");
const { guard } = require("../lib/common");

// POST /api/generate {prompt} -> {text, truncated}. The Anthropic key stays server-side.
app.http("generate", {
  methods: ["POST"], authLevel: "anonymous", route: "generate",
  handler: async (request, context) => {
    const g = guard(request); if (g.error) return g.error;
    const key = process.env.ANTHROPIC_API_KEY;
    if (!key) return { status: 503, jsonBody: { code: "not_granted", error: "ANTHROPIC_API_KEY is not set" } };
    let body; try { body = await request.json(); } catch { return { status: 400, jsonBody: { error: "JSON body required" } }; }
    const prompt = String(body && body.prompt || "");
    if (!prompt || prompt.length > 250000) return { status: 400, jsonBody: { code: "invalid_request", error: "Prompt missing or too long" } };
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: { "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json" },
      body: JSON.stringify({ model: process.env.ANTHROPIC_MODEL || "claude-sonnet-5-5", max_tokens: 2000, messages: [{ role: "user", content: prompt }] })
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      context.log("anthropic error", r.status, j && j.error && j.error.type);
      return { status: r.status === 429 ? 429 : 502, jsonBody: { code: r.status === 429 ? "rate_limited" : "upstream_error", error: (j.error && j.error.message) || "Claude API error" } };
    }
    const text = (j.content || []).filter(c => c.type === "text").map(c => c.text).join("");
    return { jsonBody: { text, truncated: j.stop_reason === "max_tokens" } };
  }
});
