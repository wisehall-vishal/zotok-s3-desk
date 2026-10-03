import csv, re, difflib
from datetime import datetime, timedelta
from collections import defaultdict

BASE = datetime(1899, 12, 30)
GST = 1.18
STOP = {'pvt','private','ltd','limited','llp','opc','india','inc','co','company','the','and',
        'formerly','hil','hof','m','s','corp','corporation','industries','enterprises','enterprise',
        'products','product','solutions','solution','group','technologies','technology','sales'}

def amt(s):
    s = (s or '').strip().replace(',', '')
    try: return float(s)
    except ValueError: return 0.0

def norm(name):
    n = name.lower()
    n = re.sub(r'\(.*?\)', ' ', n)
    n = re.sub(r'[^a-z0-9 ]', ' ', n)
    toks = [t for t in n.split() if t not in STOP]
    return ' '.join(toks) or re.sub(r'[^a-z0-9]', '', name.lower())

# legal-entity / spelling aliases -> canonical key (proved by matching amounts or obvious spelling)
ALIAS = {
 'rapidue': 'recykal', 'bhagyalaxmi rolling mill': 'polaad steel', 'vikram roller flour mills': 'vrf mills',
 'birlanu': 'birlanu', 'j k cement': 'jk cement', 'ultratech cement': 'ultratech cement', 'ultratech cement s conveyor belt': 'ultratech cement',
 'fairdeals': 'murphy lighting', 'murphy lighting': 'murphy lighting', 'powder p': 'powder pack chem',
 'savex': 'savex', 'krbl': 'krbl', 'orient electric': 'orient', 'orient': 'orient', 'haldiram snacks food': 'haldiram',
 'skf': 'skf', 'hindware': 'hindware', 'hindware home innovation': 'hindware', 'nutree concepts foods': 'nutriconcept',
 'alishan panels': 'alishan ply', 'kirti oil': 'kirti gold', 'paras polymers': 'paras', 'paras': 'paras',
 'frumar agri foods': 'frumar foods', 'mohan food': 'mohan trading', 'mohan trading': 'mohan trading',
 'utility engineers': 'utility engineering', 'ravi hybirdseeds pvt t d': 'ravi hybridseeds', 'ravi hybridseeds': 'ravi hybridseeds',
 'gpc argochemicals': 'gpc agricul', 'mahaveen textiles': 'mahaveer textile', 'new royal food': 'royal food service',
 'new royal food services': 'royal food service', 'gentex agri inputs': 'gentex seeds', 'gentex': 'gentex seeds',
 'vc nutri foods': 'vc nitrifood', 'surana polycot textiles': 'surana', 'anuroop switchgear': 'anuroop switchgear',
 'shree unionn surgicals': 'shree union surgicals', 'ambica trading': 'ambika trading', 'sunita agency': 'sunita agencies',
 'multybyte marketing': 'multibyte', 'mittal': 'mittal', 'kay sons oils': 'kay sons oils', 'suraj garg sons huf': 'suraj garg sons',
 'omsaimaalikh': 'omsaimaalikh', 'yantrayug automobile yantrayug hero hub': 'yantrayug automobile', 'mvd fasteners': 'mvd fastner',
 'kankariya resources': 'kankariya resources', 'pudumjee paper': 'pudumjee paper', 'gayathri wire mill': 'gayathri wire mill',
 'auto spare race': 'auto spare race', 'salisons savitha theatre salisons arcade': 'salisons', 'europa steel': 'europa steel',
 'mehta electric': 'mehta electric', 'riddhi siddhi': 'riddhi siddhi', 'shivkrupa hardware plywood': 'shivkrupa hardware plywood',
 'renuka water': 'renuka water', 'padmavati': 'padmavathi', 'padmavathi': 'padmavathi', 'purshottam kirana bhandar': 'purushottam kirana bhandaar',
 'purushottam kirana bhandaar': 'purushottam kirana bhandaar', 'dynamic sundrop': 'dynamic sundrop', 'devansh marketing': 'devansh marketing',
 'shree sadguru sugandhalaya': 'sadhguru sugandhalaya', 'pm cona': 'pm cona', 'dnv food': 'dnv food',
 'pacific switchgear': 'anuroop switchgear', 'bhagyalakshmi steel': 'polaad steel', 'gate': 'krbl',
 'ravi hybirdseeds lt d': 'ravi hybridseeds', 'ravi hybrid seeds': 'ravi hybridseeds', 'samunnati agri innovations lab': 'samunnati',
 'samunnati': 'samunnati', 'ultratech conveyer belt': 'ultratech cement', 'ultratech rmc': 'ultratech cement',
 'metro tools': 'mumbai metro tools', 'mumbai metro tools': 'mumbai metro tools', 'g r': 'gr', 'r': 'rs',
 'bluepinefoods': 'bluepine', 'refurbicon global': 'refurbicon', 'refurbicon': 'refurbicon',
 'gayathri machinery': 'gayathri wire mill', 'gayatri machinery': 'gayathri wire mill', 'goel rice': 'goel international',
 'goel international': 'goel international', 'gpc agro chemical': 'gpc agricul', 'kiwi party decorations': 'kiwi party',
 'kiwi party': 'kiwi party', 'haldirams': 'haldiram', 'haldiram': 'haldiram', 'unifoods global': 'unifoods',
 'vigour agritech': 'vigour agri', 'vivalicious foods': 'vivalicious', 'ditto': 'ditto',
}

def key(name):
    n = norm(name)
    if n in ALIAS: return ALIAS[n]
    for a, c in ALIAS.items():
        if a and (n.startswith(a) or a.startswith(n)) and min(len(a), len(n)) >= 4: return c
    return n

def fuzzy(k, pool, cutoff=0.82):
    if k in pool: return k
    m = difflib.get_close_matches(k, list(pool), n=1, cutoff=cutoff)
    return m[0] if m else None

def month(d): return d.strftime('%Y-%m')

def load():
    inv = []
    for r in list(csv.reader(open('/home/claude/rev/invoice_register.csv')))[1:]:
        try: d = datetime.strptime(r[0].strip(), '%d-%b-%y')
        except (ValueError, IndexError): continue
        a = amt(r[3])
        inv.append(dict(date=d, m=month(d), cust=r[1].strip(), k=key(r[1]), vch=r[2].strip(), gross=a, net=round(a / GST, 2)))
    rec = []
    for r in list(csv.reader(open('/home/claude/rev/receipt_register.csv')))[1:]:
        try: d = datetime.strptime(r[0].strip(), '%d-%b-%y')
        except (ValueError, IndexError): continue
        a = amt(r[4])
        rec.append(dict(date=d, m=month(d), cust=r[1].strip(), k=key(r[1]), no=r[3].strip(), amt=a, tag=r[5].strip(),
                        suspense=r[1].strip().lower().startswith('suspense')))
    s5 = []
    for r in list(csv.reader(open('/home/claude/rev/s5_2026.csv')))[1:]:
        if len(r) < 13 or not r[2].strip(): continue
        cd = r[4].strip() or r[1].strip()
        try: d = BASE + timedelta(days=int(float(cd)))
        except ValueError: continue
        s5.append(dict(rep=r[0].strip(), cust=r[2].strip(), k=key(r[2]), date=d, m=month(d), cat=r[6].strip(),
                       adv=amt(r[10]), setup=amt(r[11]), mrr=amt(r[12])))
    rows = list(csv.reader(open('/home/claude/rev/i27.csv')))
    hdr = rows[1]
    mcols = [(i, month(BASE + timedelta(days=int(h)))) for i, h in enumerate(hdr) if h.strip().isdigit()]
    i27 = []
    for r in rows[2:]:
        if not r or not r[0].strip(): continue
        sched = {}
        for i, m in mcols:
            v = r[i].strip() if i < len(r) else ''
            sched[m] = amt(v) if v and v.upper() != 'X' else 0.0
        cd = r[4].strip()
        try: cdt = BASE + timedelta(days=int(float(cd)))
        except ValueError: cdt = None
        gl = r[6].strip()
        try: gld = BASE + timedelta(days=int(float(gl)))
        except ValueError: gld = None
        i27.append(dict(cust=r[0].strip(), alias=r[1].strip(), k=key(r[1] or r[0]), k2=key(r[0]), rep=r[2].strip(), am=r[3].strip() or '—',
                        closure=cdt, golive=gld, cmrr=amt(r[5]), mrr=amt(r[8]), target=amt(r[11]), stage=r[16].strip(), sched=sched))
    return inv, rec, s5, i27
