"""
Probability each team plays in each Round-of-32 fixture (date + kickoff time).
=============================================================================
Every R32 slot has a fixed date/time/venue, so P(team plays at a given date &
kickoff) = P(team finishes in the group position that feeds that slot).

  - 1st / 2nd place  -> a single fixed slot (and date/time).
  - 3rd place        -> the slot depends on which group winner hosts the third,
                        so the probability is spread (via FIFA's 495-combination
                        table) across the eligible host slots.

Exact (no Monte Carlo). Uses opta_positions.csv + assignment_table.json.
Run:  python kickoff_probabilities.py   ->  kickoff_probabilities.csv
"""

import csv, json, datetime
from collections import defaultdict
from itertools import combinations

QUAL = {'France':1,'Argentina':1,'Spain':1,'England':1,'Germany':1,'Brazil':1,'Portugal':1,'Netherlands':1,
'Norway':1,'USA':1,'Colombia':1,'Mexico':1,'Switzerland':1,'Morocco':1,'Japan':1,'Canada':1,
'Egypt':1,'Ecuador':1,'Australia':1,'Sweden':1,'Bosnia':1,"Cote d'Ivoire":1,'South Africa':1,
'Belgium':.9027,'Croatia':.8710,'Ghana':.9995,'Austria':.8660,'Paraguay':.9978,'Algeria':.7227,
'Senegal':.9411,'Iran':.4840,'South Korea':.3605,'Cabo Verde':.6309,'Congo DR':.4159,'Saudi Arabia':.3394,
'Uruguay':.3772,'New Zealand':.0776,'Scotland':.0125,'Iraq':0,'Uzbekistan':.0012,
'Czechia':0,'Qatar':0,'Haiti':0,'Turkiye':0,'Tunisia':0,'Jordan':0,'Panama':0,'Curacao':0}

# R32 match number -> (month, day, kickoff, venue)
SCHED_RAW = {73:(6,28,'12:00 pm (UTC-07)','Inglewood'),74:(6,29,'4:30 pm (UTC-04)','Foxborough'),
75:(6,29,'7:00 pm (UTC-06)','Guadalupe'),76:(6,29,'12:00 pm (UTC-05)','Houston'),
77:(6,30,'5:00 pm (UTC-04)','East Rutherford'),78:(6,30,'12:00 pm (UTC-05)','Arlington'),
79:(6,30,'7:00 pm (UTC-06)','Mexico City'),80:(7,1,'12:00 pm (UTC-04)','Atlanta'),
81:(7,1,'5:00 pm (UTC-07)','Santa Clara'),82:(7,1,'1:00 pm (UTC-07)','Seattle'),
83:(7,2,'7:00 pm (UTC-04)','Toronto'),84:(7,2,'12:00 pm (UTC-07)','Inglewood'),
85:(7,2,'8:00 pm (UTC-07)','Vancouver'),86:(7,3,'6:00 pm (UTC-04)','Miami Gardens'),
87:(7,3,'8:30 pm (UTC-05)','Kansas City'),88:(7,3,'1:00 pm (UTC-05)','Arlington')}
SCHED = {n: (datetime.date(2026, mo, dy).strftime('%a') + ' ' + str(dy) + ' '
            + datetime.date(2026, mo, dy).strftime('%B'), tm, ve)
         for n, (mo, dy, tm, ve) in SCHED_RAW.items()}

# group + finishing position -> R32 slot
POS1 = {'A':79,'B':85,'C':76,'D':81,'E':74,'F':75,'G':82,'H':84,'I':77,'J':86,'K':87,'L':80}
POS2 = {'A':73,'B':73,'C':75,'D':88,'E':78,'F':76,'G':88,'H':86,'I':78,'J':84,'K':83,'L':83}
HOSTMATCH = {'E':74,'I':77,'A':79,'L':80,'D':81,'G':82,'B':85,'K':87}   # winner group -> host slot
GROUPS = list('ABCDEFGHIJKL')

# Completed-group thirds, ranked best->worst (see opponent_matrix_exact.py).
# Advancing subset of these must be a top-down prefix; [] disables pruning.
LOCKED_THIRDS_ORDER = ['F', 'E', 'B', 'D', 'I', 'A', 'C']  # Swe, Ecu, Bos, Par, Sen, Kor, Sco

def _locked_ok(S):
    out = False
    for g in LOCKED_THIRDS_ORDER:
        if g in S:
            if out:
                return False
        else:
            out = True
    return True


def main():
    rows = list(csv.reader(open('opta_positions.csv')))[1:]
    P, ti = {}, defaultdict(list)
    for g, t, a, b, c, d in rows:
        P[t] = [float(a)/100, float(b)/100, float(c)/100, float(d)/100]; ti[g].append(t)
    group_of = {t: g for g, ts in ti.items() for t in ts}
    q3 = {t: max(0.0, QUAL[t]-P[t][0]-P[t][1]) for t in P}       # P(advance as a third)
    A = {g: sum(q3[t] for t in ti[g]) for g in ti}

    # exact joint over which 8 thirds qualify (independent Bernoulli, conditioned on 8)
    tbl = {''.join(sorted(r['advancing'])): r['assign']
           for r in json.load(open('assignment_table.json')).values()}
    combos, Z = [], 0.0
    for eight in combinations(GROUPS, 8):
        S = set(eight); w = 1.0
        for g in GROUPS:
            w *= A[g] if g in S else (1 - A[g])
        if w == 0:
            continue
        if not _locked_ok(S):
            continue
        combos.append((S, w, tbl[''.join(sorted(eight))])); Z += w
    PY = {g: sum(w for S, w, _ in combos if g in S) for g in GROUPS}
    # host_of[Y][X] = P(winner of group X hosts group Y's third | Y advances)
    host_of = {Y: defaultdict(float) for Y in GROUPS}
    for S, w, amap in combos:
        inv = {amap['1'+X][1]: X for X in HOSTMATCH}
        for Y in S:
            host_of[Y][inv[Y]] += w / PY[Y]

    # per-team probability of each R32 slot
    out = []
    for t in P:
        g = group_of[t]
        mp = defaultdict(float)
        mp[POS1[g]] += P[t][0]                       # win group
        mp[POS2[g]] += P[t][1]                       # runner-up
        for X, ph in host_of[g].items():             # advance as third
            mp[HOSTMATCH[X]] += q3[t] * ph
        for n, pr in sorted(mp.items(), key=lambda x: SCHED[x[0]][0:1] and x[0]):
            if pr >= 0.0005:
                dt, tm, ve = SCHED[n]
                out.append([t, g, n, dt, tm, ve, round(pr, 4)])
        elim = round(1 - QUAL[t], 4)
        if elim >= 0.0005:
            out.append([t, g, '', 'Eliminated in groups', '', '', elim])

    out.sort(key=lambda r: (r[0], r[2] if r[2] != '' else 999))
    with open('kickoff_probabilities.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['team', 'group', 'match', 'date', 'kickoff_time', 'venue', 'probability'])
        w.writerows(out)
    print(f"{len(out)} rows -> kickoff_probabilities.csv\n")
    print("Sample - England (P it plays each fixture):")
    print(f"{'date':16}{'kickoff':18}{'venue':16}{'P':>7}")
    for r in out:
        if r[0] == 'England':
            print(f"{r[3]:16}{r[4]:18}{r[5]:16}{r[6]*100:6.1f}%")


if __name__ == '__main__':
    main()
