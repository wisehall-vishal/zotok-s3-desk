# Revenue triangulation (books vs funnel)

Used by the daily scheduled run (Part B, step B5b) and on demand.

1. Put the four CSVs in `/home/claude/rev/` with these names (read from SharePoint `00_Zono Relevant/MIS/Dec26 Bridge/CSV`):
   - `invoice_register.csv`  ← Raw Invoice Register.csv (as-is)
   - `receipt_register.csv`  ← Raw Receipt Register.csv (as-is)
   - `s5_2026.csv`           ← Raw S5 Closure Data.csv (as-is; pre-2026 rows are fine)
   - `i27.csv`               ← RAW I2-I7 MRR Data.csv (as-is)
2. `cd tools/revenue && python3 analyse.py` → prints the summary and writes `/home/claude/rev/results.json`
3. `python3 build.py` → `/home/claude/rev/ZoTok_MoM_Revenue_Jan-Sep26.xlsx` (set `REV_OUT` to change), then recalc with the xlsx skill's `recalc.py`.

Name matching: normalised key + the `ALIAS` dict in `core.py` (legal entity ↔ brand, e.g. Rapidue = Recykal,
Bhagyalaxmi Rolling Mill = Polaad, Vikram Roller Flour Mills = VRF, India Gate = KRBL). Add new aliases there
only when an exact advance/receipt amount confirms them.
