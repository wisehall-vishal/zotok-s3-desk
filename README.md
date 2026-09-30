# S3 Follow-up Desk (Azure)

Post-demo follow-up desk for ZoTok salespeople: today's cadence emails (M1–M10), meetings by date, full grow@ threads,
transcripts, notes, "Write with Claude" drafts and branded journey downloads.

- `app/` static site (Azure Static Web Apps). `shim.js` maps the page's data calls to the API.
- `api/` Azure Functions: `/api/data`, `/api/doc/{coll}/{id}`, `/api/users`, `/api/generate`. Notes, drafts, flags and
  uploaded transcripts live in Azure Table Storage (table `desk`).
- `api/data/desk.json` daily snapshot of meetings + email threads, pushed by the Claude "S3 Follow-up Desk — daily sync"
  task each morning (07:10 IST). Every push redeploys the site.
- Access: Microsoft sign-in required for every route; the API only serves `@zotok.ai` accounts (`ALLOWED_DOMAIN`).

Deploy: `powershell -ExecutionPolicy Bypass -File scripts/deploy.ps1 -Repo https://github.com/<owner>/zotok-s3-desk`
App settings: `STORAGE_CONNECTION`, `ALLOWED_DOMAIN`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`.
