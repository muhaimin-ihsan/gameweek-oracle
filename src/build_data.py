"""Builds the compact data file for the GW predictor from the FPL API dumps in this folder."""
import json, math, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(open(os.path.join(HERE, n), encoding="utf8"))

bs = J("bs.json"); fx = J("fixtures.json")
events = bs["events"]
# Results and form come from finished gameweeks only; the forecast is for the next gameweek whose deadline is still open.
cur = max(e["id"] for e in events if e["finished"])
nxt = next(e for e in events if e["is_next"])
NEXT = nxt["id"]
running = [e["id"] for e in events if cur < e["id"] < NEXT]
if running:
    print(f"Note: gameweek {running[0]} is still being played. Its results are left out; run refresh.sh again once it finishes.")
live = {g: {e["id"]: e for e in J(f"live{g}.json")["elements"]} for g in range(1, cur + 1)}
POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
teams = {t["id"]: t for t in bs["teams"]}
els = bs["elements"]

# ---------- team ratings from goals + xG, weighted toward recent weeks ----------
team_xg = defaultdict(lambda: defaultdict(float))  # team -> gw -> xG
for g, L in live.items():
    for p in els:
        s = L.get(p["id"])
        if s and s["stats"]["minutes"] > 0:
            team_xg[p["team"]][g] += float(s["stats"]["expected_goals"])

done = [f for f in fx if f["finished"]]
rows = []
for f in done:
    g = f["event"]; h, a = f["team_h"], f["team_a"]
    rows.append((g, h, a, f["team_h_score"], f["team_a_score"], team_xg[h][g], team_xg[a][g], True))
    rows.append((g, a, h, f["team_a_score"], f["team_h_score"], team_xg[a][g], team_xg[h][g], False))

W = lambda g: 0.88 ** (cur - g)
tot_w = sum(W(r[0]) for r in rows)
lg_for = sum(W(r[0]) * (0.5 * r[3] + 0.5 * r[5]) for r in rows) / tot_w  # league mean per team-game
att, dfn, base_xgf = {}, {}, {}
PRIOR = 2.5  # pseudo-games of an average side
for t in teams:
    rr = [r for r in rows if r[1] == t]
    w = sum(W(r[0]) for r in rr)
    f_ = sum(W(r[0]) * (0.5 * r[3] + 0.5 * r[5]) for r in rr)
    a_ = sum(W(r[0]) * (0.5 * r[4] + 0.5 * r[6]) for r in rr)
    att[t] = (f_ + PRIOR * lg_for) / (w + PRIOR) / lg_for
    dfn[t] = (a_ + PRIOR * lg_for) / (w + PRIOR) / lg_for
    base_xgf[t] = att[t] * lg_for

HOME = 1.12; AWAY = 0.90
def mu(t, o, home): return lg_for * att[t] * dfn[o] * (HOME if home else AWAY)

def pois(l, k): return math.exp(-l) * l ** k / math.factorial(k)
def wdl(lh, la):
    w = d = l = 0.0
    for i in range(11):
        for j in range(11):
            p = pois(lh, i) * pois(la, j)
            if i > j: w += p
            elif i == j: d += p
            else: l += p
    return w, d, l

# ---------- standings + form ----------
tab = {t: dict(p=0, w=0, d=0, l=0, gf=0, ga=0, pts=0, form=[]) for t in teams}
for f in sorted(done, key=lambda f: (f["event"], f["kickoff_time"])):
    h, a, hs, as_ = f["team_h"], f["team_a"], f["team_h_score"], f["team_a_score"]
    for t, gf, ga in ((h, hs, as_), (a, as_, hs)):
        T = tab[t]; T["p"] += 1; T["gf"] += gf; T["ga"] += ga
        if gf > ga: T["w"] += 1; T["pts"] += 3; T["form"].append("W")
        elif gf == ga: T["d"] += 1; T["pts"] += 1; T["form"].append("D")
        else: T["l"] += 1; T["form"].append("L")
order = sorted(teams, key=lambda t: (-tab[t]["pts"], -(tab[t]["gf"] - tab[t]["ga"]), -tab[t]["gf"], teams[t]["name"]))

# ---------- fixtures ----------
def fixt(gw):
    out = []
    for f in fx:
        if f["event"] != gw: continue
        h, a = f["team_h"], f["team_a"]
        o = dict(id=f["id"], h=h, a=a, ko=f["kickoff_time"], hs=f["team_h_score"], as_=f["team_a_score"])
        st = {s["identifier"]: s for s in f["stats"]}
        if f["finished"]:
            gs = st.get("goals_scored", {"h": [], "a": []}); og = st.get("own_goals", {"h": [], "a": []}); asst = st.get("assists", {"h": [], "a": []})
            o["gh"] = [[x["element"], x["value"]] for x in gs["h"]]; o["ga"] = [[x["element"], x["value"]] for x in gs["a"]]
            o["ogh"] = [[x["element"], x["value"]] for x in og["h"]]; o["oga"] = [[x["element"], x["value"]] for x in og["a"]]
            o["ah"] = [[x["element"], x["value"]] for x in asst["h"]]; o["aa"] = [[x["element"], x["value"]] for x in asst["a"]]
            o["xh"] = round(team_xg[h][gw], 2); o["xa"] = round(team_xg[a][gw], 2)
        out.append(o)
    return sorted(out, key=lambda o: o["ko"])

next_fx = fixt(NEXT)
opp = {}  # team -> (opp, home, mu_for, mu_against)
for o in next_fx:
    lh, la = mu(o["h"], o["a"], True), mu(o["a"], o["h"], False)
    w, d, l = wdl(lh, la)
    o.update(mh=round(lh, 2), ma=round(la, 2), pw=round(w, 3), pd=round(d, 3), pl=round(l, 3))
    opp[o["h"]] = (o["a"], True, lh, la); opp[o["a"]] = (o["h"], False, la, lh)

# difficulty 1-5 from opponent strength as seen by each side
def diff(t, o, home):
    # ratio of expected goal difference against this opponent vs an average one
    gd = mu(t, o, home) - mu(o, t, not home)
    return max(1, min(5, round(3 - gd * 1.6)))

upcoming = {}
for t in teams:
    lst = []
    for gw in range(NEXT, NEXT + 4):
        for f in fx:
            if f["event"] == gw and t in (f["team_h"], f["team_a"]):
                home = f["team_h"] == t; o = f["team_a"] if home else f["team_h"]
                lst.append([gw, o, 1 if home else 0, diff(t, o, home)])
    upcoming[t] = lst

# ---------- players ----------
def f_(x): return float(x or 0)
def poisson_tail(m, k):  # P(X >= k)
    return 1 - sum(pois(m, i) for i in range(k))
def e_half_floor(m):  # E[floor(X/2)] for Poisson
    return sum((k // 2) * pois(m, k) for k in range(15))

GPTS = {1: 10, 2: 6, 3: 5, 4: 4}; CSP = {1: 4, 2: 4, 3: 1, 4: 0}
players = []
for p in els:
    t = p["team"]; pos = p["element_type"]
    if pos not in POS: continue
    hist = []
    for g in range(1, cur + 1):
        s = live[g].get(p["id"])
        st = s["stats"] if s else None
        hist.append([st["total_points"], st["minutes"]] if st else [0, 0])
    last3 = hist[-3:]; last5 = hist[-5:]
    rec_min = sum(m for _, m in last3) / 3
    ws = [0.6, 0.8, 1.0]
    rec_pts = sum(w * pt for w, (pt, m) in zip(ws, last3)) / sum(ws)
    played = [h for h in last5 if h[1] > 0]
    pts_per_app = sum(h[0] for h in played) / len(played) if played else 0

    status = p["status"]; ch = p["chance_of_playing_next_round"]
    avail = 1.0 if status == "a" else (ch / 100 if ch is not None else (0.5 if status == "d" else 0.0))
    if status == "a" and ch is not None: avail = ch / 100
    # minutes: recent trend, season fallback for players with tiny samples
    season_mpg = p["minutes"] / cur
    exp_min = (0.7 * rec_min + 0.3 * season_mpg) * avail
    p_play = min(1.0, (sum(1 for _, m in last3 if m > 0) / 3 * 0.75 + (0.25 if p["starts"] > 0 else 0))) * avail if exp_min > 0 else 0
    p60 = min(p_play, max(0.0, (exp_min - 20) / 65))

    mins90 = max(p["minutes"], 1) / 90
    xg90 = f_(p["expected_goals_per_90"]) if p["minutes"] >= 180 else f_(p["expected_goals"]) / max(mins90, 3)
    xa90 = f_(p["expected_assists_per_90"]) if p["minutes"] >= 180 else f_(p["expected_assists"]) / max(mins90, 3)
    # regress finishing: actual goals pull lightly on xG
    g90 = p["goals_scored"] / max(mins90, 2); a90 = p["assists"] / max(mins90, 2)
    xg90 = 0.8 * xg90 + 0.2 * g90; xa90 = 0.8 * xa90 + 0.2 * a90
    dc90 = f_(p["defensive_contribution_per_90"]); sv90 = f_(p["saves_per_90"])
    bon90 = p["bonus"] / max(mins90, 2)

    if t in opp:
        o, home, mf, ma = opp[t]
        afac = mf / base_xgf[t]
        m = exp_min / 90
        xG = xg90 * m * afac; xA = xa90 * m * afac
        cs = math.exp(-ma)
        dc_thr = 10 if pos == 2 else 12
        dcP = poisson_tail(dc90 * min(exp_min, 90) / 90, dc_thr) if pos != 1 and dc90 > 0 else 0
        saves = sv90 * m * (ma / lg_for) if pos == 1 else 0
        model = (p_play * 1 + p60 * 1 + xG * GPTS[pos] + xA * 3 + p60 * cs * CSP[pos]
                 - (p60 * e_half_floor(ma) if pos in (1, 2) else 0)
                 + saves / 3 + dcP * 2 + bon90 * m * math.sqrt(afac if pos > 2 else (0.5 + cs)) - 0.08 * p_play)
        fixture_fac = afac if pos >= 3 else (0.4 * afac + 0.6 * (cs / 0.3))
        form_part = pts_per_app * min(1.6, max(0.5, fixture_fac)) * p_play
        xp = max(0.0, 0.72 * model + 0.28 * form_part)
    else:
        o = None; home = None; xG = xA = cs = dcP = saves = 0; xp = 0; afac = 1

    players.append(dict(
        id=p["id"], n=p["web_name"], fn=(p["first_name"] + " " + p["second_name"]).strip(), t=t, p=pos,
        c=p["now_cost"] / 10, sel=f_(p["selected_by_percent"]), tp=p["total_points"], fm=f_(p["form"]),
        ppg=f_(p["points_per_game"]), min=p["minutes"], g=p["goals_scored"], a=p["assists"], cs=p["clean_sheets"],
        b=p["bonus"], st=status, ch=ch, nw=p["news"], h=hist, rp=round(rec_pts, 2), ppa=round(pts_per_app, 2),
        em=round(exp_min, 1), pp=round(p_play, 3), p60=round(p60, 3), xg=round(xG, 3), xa=round(xA, 3),
        csp=round(cs, 3), dcp=round(dcP, 3), sv=round(saves, 2), bm=round(bon90 * (exp_min / 90), 3),
        xp=round(xp, 2), xg90=round(xg90, 2), xa90=round(xa90, 2),
    ))

# GW performers (last finished GW)
last_fx = fixt(cur)
out = dict(
    gw=cur, next=NEXT, deadline=nxt["deadline_time"], asof="2026-10-28",
    avg={e["id"]: e["average_entry_score"] for e in events if e["finished"]},
    high={e["id"]: e["highest_score"] for e in events if e["finished"]},
    teams=[dict(id=t, n=teams[t]["name"], s=teams[t]["short_name"], att=round(att[t], 3), dfn=round(dfn[t], 3),
                xgf=round(base_xgf[t], 2), **{k: v for k, v in tab[t].items()}, up=upcoming[t]) for t in teams],
    order=order, lg=round(lg_for, 3), last=last_fx, prev=fixt(cur - 1), nextfx=next_fx, players=players,
)
json.dump(out, open(os.path.join(HERE, "data.json"), "w", encoding="utf8"), separators=(",", ":"))
print("players", len(players), "bytes", os.path.getsize(os.path.join(HERE, "data.json")))
print("league goals per team-game", round(lg_for, 2))
for t in order[:20]:
    T = tab[t]; print(teams[t]["short_name"], T["pts"], T["gf"], T["ga"], "".join(T["form"][-5:]), "att", round(att[t], 2), "def", round(dfn[t], 2))
for o in next_fx:
    print(teams[o["h"]]["short_name"], "v", teams[o["a"]]["short_name"], o["mh"], o["ma"], o["pw"], o["pd"], o["pl"])
top = sorted(players, key=lambda x: -x["xp"])[:30]
for x in top: print(POS[x["p"]], ascii(x["n"]), teams[x["t"]]["short_name"], x["c"], x["xp"], x["em"], x["xg"], x["xa"], x["csp"], x["fm"])
