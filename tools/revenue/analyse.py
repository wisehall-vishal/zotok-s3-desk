import json
from collections import defaultdict
from datetime import timedelta
from core import *

inv, rec, s5, i27 = load()
MONTHS = ['2026-01','2026-02','2026-03','2026-04','2026-05','2026-06','2026-07','2026-08','2026-09']
REG = MONTHS[3:]

# ---------- I2-I7 lookup ----------
ibykey = defaultdict(list)
for a in i27:
    for k in {a['k'], a['k2']}: ibykey[k].append(a)
def i27_for(k):
    f = fuzzy(k, ibykey.keys())
    return ibykey.get(f, []) if f else []

# attach AM / rep / category to invoice lines
s5bykey = {s['k']: s for s in s5}
def s5_for(k):
    f = fuzzy(k, s5bykey.keys()); return s5bykey.get(f) if f else None
for x in inv:
    acc = i27_for(x['k']); s = s5_for(x['k'])
    x['am'] = acc[0]['am'] if acc else '(not in I2-I7)'
    x['rep'] = (acc[0]['rep'] if acc else (s['rep'] if s else '—')) or '—'
    x['stage'] = acc[0]['stage'] if acc else '(not in I2-I7)'
    x['cat'] = s['cat'] if s else '—'
    x['in_i27'] = bool(acc)

# new vs recurring: first invoice to that customer within register window, and customer closed in S5 within 60 days before
first = {}
for x in sorted(inv, key=lambda z: z['date']):
    first.setdefault(x['k'], x['date'])
for x in inv:
    s = s5_for(x['k'])
    newclose = s and timedelta(days=-15) <= (x['date'] - s['date']) <= timedelta(days=75)
    x['type'] = 'New (setup + 1st billing)' if (x['date'] == first[x['k']] and newclose) else ('First invoice in FY (old a/c)' if x['date'] == first[x['k']] else 'Recurring / repeat')

# ---------- monthly ----------
mon = {m: dict(inv_gross=0, inv_net=0, n_inv=0, cust=set(), rec=0, rec_id=0, susp=0, n_rec=0, tracker=0, tracker_accts=0,
               new_net=0, rec_net=0, top=[]) for m in MONTHS}
for x in inv:
    if x['m'] in mon:
        M = mon[x['m']]; M['inv_gross'] += x['gross']; M['inv_net'] += x['net']; M['n_inv'] += 1; M['cust'].add(x['k'])
        if x['type'].startswith('New'): M['new_net'] += x['net']
        else: M['rec_net'] += x['net']
for r in rec:
    if r['m'] in mon:
        M = mon[r['m']]; M['rec'] += r['amt']; M['n_rec'] += 1
        if r['suspense']: M['susp'] += r['amt']
        else: M['rec_id'] += r['amt']
for a in i27:
    for m in MONTHS:
        v = a['sched'].get(m, 0)
        if v: mon[m]['tracker'] += v; mon[m]['tracker_accts'] += 1
for m in REG:
    by = defaultdict(float)
    for x in inv:
        if x['m'] == m: by[x['cust']] += x['net']
    tot = sum(by.values()) or 1
    top = sorted(by.items(), key=lambda t: -t[1])
    mon[m]['top'] = top[:5]
    mon[m]['top1_share'] = top[0][1] / tot if top else 0
    mon[m]['top5_share'] = sum(v for _, v in top[:5]) / tot

# ---------- per customer ledger (Apr–Sep window; no opening balances) ----------
led = defaultdict(lambda: dict(name='', inv=0, rec=0, last_inv=None, last_rec=None, am='', rep='', n_inv=0))
for x in inv:
    L = led[x['k']]; L['name'] = L['name'] or x['cust']; L['inv'] += x['gross']; L['n_inv'] += 1
    L['last_inv'] = max(filter(None, [L['last_inv'], x['date']])); L['am'] = x['am']; L['rep'] = x['rep']
for r in rec:
    if r['suspense']: continue
    k = fuzzy(r['k'], led.keys(), 0.86) or r['k']
    L = led[k]; L['name'] = L['name'] or r['cust']; L['rec'] += r['amt']
    L['last_rec'] = max(filter(None, [L['last_rec'], r['date']]))
ASOF = datetime(2026, 9, 30)
for k, L in led.items():
    L['bal'] = round(L['inv'] - L['rec'], 2)
    L['age'] = (ASOF - L['last_inv']).days if (L['bal'] > 1000 and L['last_inv']) else None

def same(a, b):
    if a == b or fuzzy(a, {b}, 0.8): return True
    if min(len(a), len(b)) >= 5 and (a.startswith(b) or b.startswith(a)): return True
    ta, tb = a.split(), b.split()
    return bool(ta and tb and ta[0] == tb[0] and len(ta[0]) >= 5)

# ---------- triangulation 1: S5 advance (Apr–Sep closures) vs receipt register ----------
susp = [r for r in rec if r['suspense']]
tri_s5 = []
for s in s5:
    if s['date'] < datetime(2026, 4, 1): continue
    rk = [r for r in rec if not r['suspense'] and same(s['k'], r['k'])
          and timedelta(days=-45) <= (r['date'] - s['date']) <= timedelta(days=60)]
    got = sum(r['amt'] for r in rk)
    cand = [r for r in susp if s['adv'] and abs(r['amt'] - s['adv']) < 1 and timedelta(days=-20) <= (r['date'] - s['date']) <= timedelta(days=45)]
    invk = [x for x in inv if same(s['k'], x['k'])]
    inv_after = [x for x in invk if timedelta(days=-45) <= (x['date'] - s['date']) <= timedelta(days=60)]
    if s['adv'] == 0 and not rk: status = 'No advance in S5, none received'
    elif rk and abs(got - s['adv']) <= max(1500, 0.03 * s['adv']): status = 'Matched'
    elif rk: status = 'Amount differs'
    elif cand: status = 'Likely in Suspense'
    else: status = 'Not in receipts'
    tri_s5.append(dict(cust=s['cust'], rep=s['rep'], cat=s['cat'], closed=s['date'].strftime('%d-%b'), s5_adv=s['adv'],
                       received=got, rec_dates=', '.join(r['date'].strftime('%d-%b') for r in rk),
                       invoiced=sum(x['gross'] for x in inv_after), status=status,
                       suspense_hint=', '.join(f"{r['date'].strftime('%d-%b')} ₹{r['amt']:,.0f}" for r in cand),
                       in_i27=bool(i27_for(s['k']))))

# ---------- triangulation 2: I2-I7 schedule vs invoice register, Apr–Sep ----------
tri_i = []
invby = defaultdict(float)
for x in inv: invby[(x['k'], x['m'])] += x['net']
invkeys = {x['k'] for x in inv}
grp = defaultdict(lambda: dict(names=[], am=set(), stage=set(), sched=defaultdict(float)))
for a in i27:
    kk = a['k'] if fuzzy(a['k'], invkeys) else a['k2']
    kk = fuzzy(kk, invkeys) or kk
    g = grp[kk]; g['names'].append(a['cust']); g['am'].add(a['am']); g['stage'].add(a['stage'][:4])
    for m in REG: g['sched'][m] += a['sched'].get(m, 0)
for kk, g in grp.items():
    for m in REG:
        t = g['sched'][m]; b = invby.get((kk, m), 0)
        if t or b:
            tri_i.append(dict(cust=' + '.join(sorted(set(g['names']))), am='/'.join(sorted(g['am'])), stage='/'.join(sorted(g['stage'])),
                              m=m, tracker=t, invoiced=round(b), diff=round(b - t)))
# receipts from customers with no invoice in the register window (advance taken, no tax invoice)
rec_no_inv = defaultdict(float)
for r in rec:
    if r['suspense'] or r['amt'] < 100: continue
    if not fuzzy(r['k'], invkeys, 0.86): rec_no_inv[r['cust']] += r['amt']
inv_not_in_i27 = sorted({x['cust'] for x in inv if not x['in_i27']})

# ---------- by AM / rep / category ----------
by_am = defaultdict(lambda: defaultdict(float)); by_rep = defaultdict(lambda: defaultdict(float)); by_cat = defaultdict(lambda: defaultdict(float))
for x in inv:
    by_am[x['am']][x['m']] += x['net']; by_rep[x['rep']][x['m']] += x['net']; by_cat[x['cat']][x['m']] += x['net']
trk_am = defaultdict(lambda: defaultdict(float))
for a in i27:
    for m in MONTHS: trk_am[a['am']][m] += a['sched'].get(m, 0)

out = dict(
    months={m: {k: (round(v, 2) if isinstance(v, float) else (len(v) if isinstance(v, set) else v)) for k, v in M.items()} for m, M in mon.items()},
    tri_s5=tri_s5, tri_i=tri_i, inv_not_in_i27=inv_not_in_i27, rec_no_inv=dict(rec_no_inv),
    ledger=sorted([dict(k=k, **{kk: (vv.strftime('%d-%b-%y') if hasattr(vv, 'strftime') else vv) for kk, vv in L.items()}) for k, L in led.items()], key=lambda z: -z['bal']),
    by_am={k: dict(v) for k, v in by_am.items()}, by_rep={k: dict(v) for k, v in by_rep.items()},
    by_cat={k: dict(v) for k, v in by_cat.items()}, trk_am={k: dict(v) for k, v in trk_am.items()},
    suspense=[dict(date=r['date'].strftime('%d-%b'), amt=r['amt']) for r in susp],
    inv_lines=[dict(date=x['date'].strftime('%Y-%m-%d'), m=x['m'], cust=x['cust'], vch=x['vch'], gross=x['gross'], net=x['net'],
                    am=x['am'], rep=x['rep'], cat=x['cat'], type=x['type'], stage=x['stage']) for x in inv],
    rec_lines=[dict(date=r['date'].strftime('%Y-%m-%d'), m=r['m'], cust=r['cust'], amt=r['amt'], tag=r['tag'], suspense=r['suspense']) for r in rec],
)
json.dump(out, open('/home/claude/rev/results.json', 'w'), default=str, indent=1)

# ---------- print summary ----------
print('MONTH   tracker(I2-I7)  accts | invoiced ex-GST  #inv cust | collected  susp | coll% of inv(gross) | new_net  top1%')
for m in MONTHS:
    M = out['months'][m]
    ci = f"{M['rec']/M['inv_gross']*100:5.0f}%" if M['inv_gross'] else '   — '
    print(f"{m}  {M['tracker']:12,.0f} {M['tracker_accts']:4d} | {M['inv_net']:12,.0f} {M['n_inv']:4d} {M['cust']:3d} | {M['rec']:10,.0f} {M['susp']:7,.0f} | {ci} | {M['new_net']:10,.0f} {M.get('top1_share',0)*100:4.0f}%")
from collections import Counter
print('\nS5 Apr-Sep closures vs receipts:', Counter(t['status'] for t in tri_s5))
for t in tri_s5:
    if t['status'] not in ('Matched', 'No advance in S5, none received'):
        print(f"  {t['status']:22s} {t['cust'][:30]:30s} {t['rep']:12s} adv {t['s5_adv']:>9,.0f} rec {t['received']:>9,.0f} {t['rec_dates']} {t['suspense_hint']}")
print('\nNo advance in S5 & none received:', [t['cust'] for t in tri_s5 if t['status'].startswith('No adv')])
print('\nInvoiced but not in I2-I7:', inv_not_in_i27)
gaps = [t for t in tri_i if abs(t['diff']) > 2000]
print('\nI2-I7 vs invoice gaps >2k:', len(gaps), 'of', len(tri_i))
tr_no_inv = sum(t['tracker'] for t in tri_i if t['tracker'] and not t['invoiced'])
inv_no_tr = sum(t['invoiced'] for t in tri_i if t['invoiced'] and not t['tracker'])
print(f"  tracker says billed, no invoice: ₹{tr_no_inv:,.0f} ({sum(1 for t in tri_i if t['tracker'] and not t['invoiced'])} acct-months)")
print(f"  invoiced, tracker blank: ₹{inv_no_tr:,.0f} ({sum(1 for t in tri_i if t['invoiced'] and not t['tracker'])} acct-months)")
print('\nTop open balances (Apr-Sep window, gross):')
for L in out['ledger'][:15]: print(f"  {L['name'][:38]:38s} inv {L['inv']:>11,.0f} rec {L['rec']:>11,.0f} bal {L['bal']:>11,.0f} age {L['age']} AM {L['am']}")
print('\nCredits (received > invoiced in window):')
for L in sorted(out['ledger'], key=lambda z: z['bal'])[:8]: print(f"  {L['name'][:38]:38s} bal {L['bal']:>11,.0f}")
print('\nSuspense total', sum(s['amt'] for s in out['suspense']), len(out['suspense']))
