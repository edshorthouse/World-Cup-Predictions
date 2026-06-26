"""
EXACT England / full-bracket Round-of-32 opponent matrix (2026 FIFA World Cup)
=============================================================================
No Monte Carlo. Every value is computed directly from Opta's published
marginals, except the third-place ASSIGNMENT, which is an exact sum over the
495 combinations in FIFA's official table (assignment_table.json).

For every group / team / finishing position:
  - prob_of_position                         (exact Opta marginal)
  - each possible R32 opponent               (traced through the bracket)
  - prob_of_opponent | that position         (exact)

Only dependency: assignment_table.json in the same folder (no numpy needed).
Run in PyCharm -> writes opponent_matrix_exact.csv
"""

import os, json, csv
from collections import defaultdict
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
THRESHOLD = 0.0005    # drop opponent branches below 0.05%; set 0 to keep all

# group, team, P1, P2, P3, P4  (percent) -- decoded Opta Supercomputer
POSITIONS = [
    ('A','Mexico',100,0,0,0),('A','South Africa',0,100,0,0),('A','South Korea',0,0,100,0),('A','Czechia',0,0,0,100),
    ('B','Switzerland',100,0,0,0),('B','Canada',0,100,0,0),('B','Bosnia',0,0,100,0),('B','Qatar',0,0,0,100),
    ('C','Brazil',100,0,0,0),('C','Morocco',0,100,0,0),('C','Scotland',0,0,100,0),('C','Haiti',0,0,0,100),
    ('D','USA',100,0,0,0),('D','Australia',0,100,0,0),('D','Paraguay',0,0,100,0),('D','Turkiye',0,0,0,100),
    ('E','Germany',100,0,0,0),('E',"Cote d'Ivoire",0,100,0,0),('E','Ecuador',0,0,100,0),('E','Curacao',0,0,0,100),
    ('F','Netherlands',100,0,0,0),('F','Japan',0,100,0,0),('F','Sweden',0,0,100,0),('F','Tunisia',0,0,0,100),
    ('G','Egypt',61.23,17.54,21.23,0),('G','Belgium',27.41,59.31,7.42,5.86),('G','Iran',11.36,17.99,67.71,2.94),('G','New Zealand',0,5.16,3.64,91.20),
    ('H','Spain',84.74,9.65,5.61,0),('H','Cabo Verde',2.70,53.33,19.42,24.56),('H','Uruguay',12.56,7.50,69.38,10.56),('H','Saudi Arabia',0,29.53,5.59,64.88),
    ('I','France',79.94,20.06,0,0),('I','Norway',20.06,79.94,0,0),('I','Senegal',0,0,91.20,8.80),('I','Iraq',0,0,8.80,91.20),
    ('J','Argentina',100,0,0,0),('J','Austria',0,73.10,26.90,0),('J','Algeria',0,26.90,73.10,0),('J','Jordan',0,0,0,100),
    ('K','Colombia',49.47,50.53,0,0),('K','Portugal',50.53,49.24,0.21,0),('K','Congo DR',0,0.22,69.05,30.72),('K','Uzbekistan',0,0,30.72,69.28),
    ('L','England',84.61,15.06,0.33,0),('L','Ghana',4.83,38.87,56.30,0),('L','Croatia',10.56,46.07,43.37,0),('L','Panama',0,0,0,100),
]
QUAL = {'France':1,'Argentina':1,'Spain':1,'England':1,'Germany':1,'Brazil':1,'Portugal':1,'Netherlands':1,
'Norway':1,'USA':1,'Colombia':1,'Mexico':1,'Switzerland':1,'Morocco':1,'Japan':1,'Canada':1,
'Egypt':1,'Ecuador':1,'Australia':1,'Sweden':1,'Bosnia':1,"Cote d'Ivoire":1,'South Africa':1,
'Belgium':.9216,'Croatia':.8907,'Ghana':.9996,'Austria':.9036,'Paraguay':.9985,'Algeria':.7465,
'Senegal':.569,'Iran':.55,'South Korea':.5324,'Cabo Verde':.6395,'Congo DR':.4116,'Saudi Arabia':.3459,
'Uruguay':.3641,'New Zealand':.07,'Scotland':.0524,'Iraq':.0028,'Uzbekistan':.002,
'Czechia':0,'Qatar':0,'Haiti':0,'Turkiye':0,'Tunisia':0,'Jordan':0,'Panama':0,'Curacao':0}

GROUPS = list('ABCDEFGHIJKL')
POS_LABELS = ['1st','2nd','3rd','4th']

# Completed-group third-placed teams, ranked best->worst on the live leaderboard.
# Their order is now FIXED, so the advancing subset of them must be a top-down
# prefix (e.g. Scotland cannot qualify unless Korea does). This rules out
# impossible qualifier combinations the independent model would otherwise allow.
# UPDATE each refresh from Opta's "Ranking of third-placed teams" (completed
# groups only, best to worst by points/GD/GF); set to [] to disable pruning.
LOCKED_THIRDS_ORDER = ['F', 'E', 'B', 'D', 'A', 'C']  # Swe, Ecu, Bos, Par, Kor, Sco

def _locked_ok(S):
    out = False
    for g in LOCKED_THIRDS_ORDER:
        if g in S:
            if out:
                return False
        else:
            out = True
    return True

WINNER_FIXED = {'C':('2','F'),'F':('2','C'),'H':('2','J'),'J':('2','H')}
HOST_WINNERS = set('ABDEGIKL')
RUNNERUP_OPP = {'A':('2','B'),'B':('2','A'),'C':('1','F'),'F':('1','C'),'E':('2','I'),'I':('2','E'),
                'D':('2','G'),'G':('2','D'),'H':('1','J'),'J':('1','H'),'K':('2','L'),'L':('2','K')}


def main():
    pos = {t:[a/100,b/100,c/100,d/100] for g,t,a,b,c,d in POSITIONS}
    teams_in = defaultdict(list)
    for g,t,*_ in POSITIONS:
        teams_in[g].append(t)
    P = {(t,POS_LABELS[i]): pos[t][i] for t in pos for i in range(4)}

    # q3 = P(team is the advancing 3rd) ;  A_g = P(group's 3rd advances) = sum q3
    q3 = {t: max(0.0, QUAL[t]-pos[t][0]-pos[t][1]) for t in pos}
    A = {g: sum(q3[t] for t in teams_in[g]) for g in GROUPS}
    adv_if_third = {t: (q3[t]/pos[t][2] if pos[t][2] > 1e-9 else 0.0) for t in pos}

    # FIFA 495-combination table:  advancing-set -> {'1X':'3Y'}
    table = {''.join(sorted(r['advancing'])): r['assign']
             for r in json.load(open(os.path.join(HERE,'assignment_table.json'))).values()}

    # ---- exact joint over which 8 thirds qualify -------------------------
    # model: independent Bernoulli(A_g) conditioned on exactly 8 advancing.
    combos = []          # (set_of_8, weight, assign_map)
    Z = 0.0
    n_possible = n_pruned = 0
    for eight in combinations(GROUPS, 8):
        S = set(eight)
        w = 1.0
        for g in GROUPS:
            w *= A[g] if g in S else (1 - A[g])
        if w == 0:
            continue
        n_possible += 1
        if not _locked_ok(S):     # ordering of already-decided thirds is fixed
            n_pruned += 1
            continue
        key = ''.join(sorted(eight))
        combos.append((S, w, table[key]))
        Z += w
    combos = [(S, w/Z, amap) for S, w, amap in combos]
    print(f"locked-third pruning: {n_pruned}/{n_possible} possible combos ruled out")

    # marginal P(group g advances) under this joint
    PY = {g: sum(w for S, w, _ in combos if g in S) for g in GROUPS}

    # slot-80-style: for each HOST winner group G -> P(opponent team u | G wins)
    host_opp = {G: defaultdict(float) for G in HOST_WINNERS}
    for S, w, amap in combos:
        for G in HOST_WINNERS:
            Y = amap['1'+G][1]                 # third-group assigned to winner of G
            for u in teams_in[Y]:
                if q3[u] > 0:
                    host_opp[G][u] += w * q3[u] / A[Y]   # P(u is Y's advancing 3rd | Y adv)

    # for each third-group Y -> P(hosting winner is group X | Y advances)
    host_of = {Y: defaultdict(float) for Y in GROUPS}
    for S, w, amap in combos:
        inv = {amap['1'+X][1]: X for X in HOST_WINNERS}   # third-group -> winner group
        for Y in S:
            X = inv[Y]
            host_of[Y][X] += w / PY[Y]

    # ---- assemble the long table -----------------------------------------
    out = []
    for g in GROUPS:
        for t in teams_in[g]:
            # 1st place
            p1 = P[(t,'1st')]
            if p1 > 0:
                opp = defaultdict(float)
                if g in WINNER_FIXED:
                    dp, og = WINNER_FIXED[g]
                    for u in teams_in[og]:
                        opp[u] += pos[u][int(dp)-1]
                else:
                    for u, pr in host_opp[g].items():
                        opp[u] += pr
                emit(out, g, t, '1st', p1, opp)
            # 2nd place
            p2 = P[(t,'2nd')]
            if p2 > 0:
                dp, og = RUNNERUP_OPP[g]
                opp = {u: pos[u][int(dp)-1] for u in teams_in[og] if pos[u][int(dp)-1] > 0}
                emit(out, g, t, '2nd', p2, opp)
            # 3rd place
            p3 = P[(t,'3rd')]
            if p3 > 0:
                opp = defaultdict(float)
                adv = adv_if_third[t]
                for X, ph in host_of[g].items():       # winner-group hosting g's 3rd
                    for w_team in teams_in[X]:
                        if pos[w_team][0] > 0:
                            opp[w_team] += adv * ph * pos[w_team][0]
                if adv < 1:
                    opp['Eliminated (not best-8 third)'] += (1 - adv)
                emit(out, g, t, '3rd', p3, opp)
            # 4th place
            p4 = P[(t,'4th')]
            if p4 > 0:
                emit(out, g, t, '4th', p4, {'Eliminated (4th)': 1.0})

    path = os.path.join(HERE, 'opponent_matrix_exact.csv')
    try:
        f = open(path, 'w', newline='', encoding='utf-8')
    except PermissionError:
        import time
        path = os.path.join(HERE, f'opponent_matrix_exact_{int(time.time())}.csv')
        f = open(path, 'w', newline='', encoding='utf-8')
    with f:
        wr = csv.writer(f)
        wr.writerow(['group','team','league_position','prob_of_position',
                     'possible_opponent','prob_of_opponent_given_position',
                     'joint_probability'])
        wr.writerows(out)
    print(f"A_g sum = {sum(A.values()):.4f}   (exact, must be 8)")
    print(f"{len(out)} rows -> {path}\n")
    print("Sample - England:")
    print(f"{'pos':4}{'P(pos)':>9}  {'opponent':30}{'P(opp|pos)':>10}")
    for r in out:
        if r[1] == 'England':
            print(f"{r[2]:4}{r[3]*100:8.2f}%  {r[4]:30}{r[5]*100:8.2f}%")


def emit(out, g, t, p, p_pos, opp):
    tot = sum(opp.values())
    for o, pr in sorted(opp.items(), key=lambda x: -x[1]):
        cond = pr / tot if tot else 0
        if cond >= THRESHOLD:
            out.append([g, t, p, round(p_pos, 4), o, round(cond, 4),
                        round(p_pos * cond, 4)])


if __name__ == '__main__':
    main()
