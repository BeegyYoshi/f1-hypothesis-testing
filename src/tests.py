"""Hypothesis tests A-F for report point 5, exactly as pre-registered in the plan doc.

Run: python src/tests.py   (after prepare.py)
Prints every reported number; writes data/test_results.csv and report/figures/qq_pit_delta.png.
"""
from itertools import combinations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ALPHA, Z975 = 0.05, stats.norm.ppf(0.975)
rng = np.random.default_rng(2026)
df = pd.read_csv("data/f1_clean.csv")
results = []


def verdict(lo, hi, delta):
    """Plan doc's practical-significance rule on a 95% CI [lo, hi] against threshold delta."""
    if -delta < lo and hi < delta:
        return "negligible"
    if lo > 0 or hi < 0:
        return "matters" if (lo >= delta or hi <= -delta) else "significant, possibly small"
    return "inconclusive"


def report(test, stat, dfree, p, est, lo, hi, effect, delta, scale_lo=None, scale_hi=None):
    """scale_lo/hi: CI of the quantity compared with delta, when it differs from the estimate's CI."""
    v = verdict(scale_lo if scale_lo is not None else lo, scale_hi if scale_hi is not None else hi, delta)
    results.append(dict(test=test, stat=stat, df=dfree, p=p, estimate=est, ci_lo=lo, ci_hi=hi,
                        effect=effect, decision="reject H0" if p < ALPHA else "fail to reject H0", practical=v))


def welch(x, y):
    nx, ny, vx, vy = len(x), len(y), x.var(ddof=1), y.var(ddof=1)
    se = np.sqrt(vx / nx + vy / ny)
    nu = se**4 / ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    diff = x.mean() - y.mean()
    t = diff / se
    p = 2 * stats.t.sf(abs(t), nu)
    half = stats.t.ppf(0.975, nu) * se
    sp = np.sqrt(((nx - 1) * vx + (ny - 1) * vy) / (nx + ny - 2))
    ref = stats.ttest_ind(x, y, equal_var=False)
    assert np.isclose(t, ref.statistic) and np.isclose(p, ref.pvalue)
    return t, nu, p, diff, diff - half, diff + half, diff / sp


# ---------------- Test A: grid vs finish ----------------
print("=" * 70, "\nTEST A: grid position vs finishing position (classified finishers)")
fin = df[df.is_classified].sort_values(["year", "round"])
x, y, n = fin.grid.to_numpy(), fin.position.to_numpy(), len(fin)
r = np.corrcoef(x, y)[0, 1]
t = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
p = 2 * stats.t.sf(abs(t), n - 2)
zf, se = np.arctanh(r), 1 / np.sqrt(n - 3)
lo, hi = np.tanh(zf - Z975 * se), np.tanh(zf + Z975 * se)
assert np.isclose(p, stats.pearsonr(x, y).pvalue)
print(f"n={n}, r={r:.4f}, t={t:.2f}, df={n - 2}, p={p:.3g}, 95% CI r [{lo:.4f}, {hi:.4f}], "
      f"r2={r * r:.4f} [{lo * lo:.4f}, {hi * hi:.4f}]")
report("A", t, n - 2, p, r, lo, hi, r * r, 0.10, lo * lo, hi * hi)
sp = stats.spearmanr(x, y)
print(f"  check Spearman: rho={sp.statistic:.4f}, p={sp.pvalue:.3g}")
lr = stats.linregress(x, y)
print(f"  check slope: {lr.slope:.4f} places per grid slot, 95% CI "
      f"[{lr.slope - stats.t.ppf(.975, n - 2) * lr.stderr:.4f}, {lr.slope + stats.t.ppf(.975, n - 2) * lr.stderr:.4f}], "
      f"intercept {lr.intercept:.3f}")
race = fin.groupby(["year", "round"]).ngroup().to_numpy()
B = 9999
perm_r = np.empty(B)
for b in range(B):  # shuffle finishing positions within each race
    perm_r[b] = np.corrcoef(x, y[np.lexsort((rng.random(n), race))])[0, 1]
print(f"  check within-race permutation ({B}): max |r| under H0 = {np.abs(perm_r).max():.4f}, "
      f"p = {(1 + (np.abs(perm_r) >= abs(r)).sum()) / (B + 1):.5f}")
races_r = fin.groupby(race).apply(lambda d: d.grid.corr(d.position), include_groups=False)
print(f"  per-race Pearson r: mean {races_r.mean():.3f}, sd {races_r.std():.3f}")

# ---------------- Test B: pole win rate by era ----------------
print("=" * 70, "\nTEST B: pole-to-win rate, 2014-2019 vs 2020-2026")
pole = df[df.grid == 1]
assert pole[["year", "round"]].duplicated().sum() == 0
g1, g2 = pole[pole.year <= 2019].winner, pole[pole.year >= 2020].winner
x1, n1, x2, n2 = g1.sum(), len(g1), g2.sum(), len(g2)
p1, p2, pp = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
z = (p1 - p2) / np.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
p = 2 * stats.norm.sf(abs(z))
half = Z975 * np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
h = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
print(f"group1 {x1}/{n1}={p1:.4f}, group2 {x2}/{n2}={p2:.4f}, pooled {pp:.4f}")
print(f"z={z:.4f}, p={p:.4f}, diff p1-p2={p1 - p2:.4f}, 95% CI [{p1 - p2 - half:.4f}, {p1 - p2 + half:.4f}], h={h:.4f}")
print(f"  condition: successes/failures per group {x1}/{n1 - x1}, {x2}/{n2 - x2} (all >= 10)")
report("B", z, None, p, p1 - p2, p1 - p2 - half, p1 - p2 + half, h, 0.10)
tab = np.array([[x1, n1 - x1], [x2, n2 - x2]])
chi = stats.chi2_contingency(tab, correction=False)
print(f"  check chi-square (no Yates): {chi.statistic:.4f} = z^2 {z * z:.4f}, df 1, p={chi.pvalue:.4f}")
print(f"  check Fisher exact: p={stats.fisher_exact(tab).pvalue:.4f}")
print(f"  pole win rate per season: {pole.groupby('year').winner.mean().round(3).to_dict()}")

# ---------------- Test C: top-4 team vs finish category ----------------
print("=" * 70, "\nTEST C: constructor (top 4) vs finish category")
cats = ["podium", "points", "no_points", "retired"]
top = df[df.top_team]
O = pd.crosstab(top.constructor, top.finish_cat)[cats]
chi = stats.chi2_contingency(O, correction=False)
N = O.values.sum()
V = np.sqrt(chi.statistic / (N * (min(O.shape) - 1)))
E = pd.DataFrame(chi.expected_freq, index=O.index, columns=cats)
contrib = (O - E) ** 2 / E
print(O, "\nexpected:\n", E.round(1))
print(f"chi2={chi.statistic:.2f}, df={chi.dof}, p={chi.pvalue:.3g}, N={N}, V={V:.4f}, min expected {E.values.min():.1f}")
cells = contrib.stack().sort_values(ascending=False).head(4)
for (team, cat), c in cells.items():
    print(f"  largest (O-E)^2/E: {team} x {cat}: {c:.1f} (O={O.loc[team, cat]}, E={E.loc[team, cat]:.1f})")
codes_t, codes_c = top.constructor.to_numpy(), top.finish_cat.to_numpy()
Vb = []
for _ in range(2000):  # bootstrap CI for V, resampling driver-races
    i = rng.integers(0, len(top), len(top))
    ob = pd.crosstab(codes_t[i], codes_c[i])
    Vb.append(np.sqrt(stats.chi2_contingency(ob, correction=False).statistic / (len(i) * (min(ob.shape) - 1))))
vlo, vhi = np.percentile(Vb, [2.5, 97.5])
print(f"  bootstrap 95% CI for V: [{vlo:.4f}, {vhi:.4f}]")
report("C", chi.statistic, chi.dof, chi.pvalue, V, vlo, vhi, V, 0.10)
g = stats.chi2_contingency(O, correction=False, lambda_="log-likelihood")
print(f"  check G-test: G={g.statistic:.2f}, df={g.dof}, p={g.pvalue:.3g}")
print("  row %:\n", (O.div(O.sum(1), axis=0) * 100).round(1))

# ---------------- Test D: winners' pit stops (top 4) ----------------
print("=" * 70, "\nTEST D: pit delta, winners vs non-winners (top-4 teams)")
d = df[df.top_team].dropna(subset=["pit_delta_s"])
w, nw = d[d.winner].pit_delta_s, d[~d.winner].pit_delta_s
t, nu, p, diff, lo, hi, cd = welch(w, nw)
print(f"W n={len(w)} mean={w.mean():.4f} sd={w.std():.4f}; N n={len(nw)} mean={nw.mean():.4f} sd={nw.std():.4f}")
print(f"t={t:.3f}, nu={nu:.1f}, p={p:.3g}, diff={diff:.4f}, 95% CI [{lo:.4f}, {hi:.4f}], d={cd:.4f}")
report("D", t, nu, p, diff, lo, hi, cd, 0.3)
mw = stats.mannwhitneyu(w, nw)
print(f"  check Mann-Whitney: U={mw.statistic:.0f}, p={mw.pvalue:.3g}, "
      f"rank-biserial={1 - 2 * mw.statistic / (len(w) * len(nw)):.4f}; medians {w.median():.3f} vs {nw.median():.3f}")
pooled = stats.ttest_ind(w, nw)
print(f"  check pooled t: t={pooled.statistic:.3f}, df={len(w) + len(nw) - 2}, p={pooled.pvalue:.3g}")
print(f"  shape: skew W {w.skew():.2f}, N {nw.skew():.2f}")

# ---------------- Test E: track type ----------------
print("=" * 70, "\nTEST E: per-race grid-finish Fisher z, street vs permanent")
def race_rho(g):
    g = g[g.is_classified]
    return pd.Series({"rho": stats.spearmanr(g.grid, g.position).statistic if len(g) >= 10 else np.nan,
                      "finishers": len(g)})
rr = df.groupby(["year", "round", "circuit", "street"]).apply(race_rho, include_groups=False).reset_index()
print(f"races {len(rr)}, skipped (<10 finishers): {rr.rho.isna().sum()}")
rr = rr.dropna()
rr["z"] = np.arctanh(rr.rho.clip(upper=0.9999))
zs, zp = rr[rr.street].z, rr[~rr.street].z
t, nu, p, diff, lo, hi, cd = welch(zs, zp)
print(f"S n={len(zs)} mean z={zs.mean():.4f} (rho {np.tanh(zs.mean()):.3f}) sd={zs.std():.4f}; "
      f"P n={len(zp)} mean z={zp.mean():.4f} (rho {np.tanh(zp.mean()):.3f}) sd={zp.std():.4f}")
print(f"t={t:.3f}, nu={nu:.1f}, p={p:.4f}, diff={diff:.4f}, 95% CI [{lo:.4f}, {hi:.4f}], d={cd:.4f}")
report("E", t, nu, p, diff, lo, hi, cd, 0.10)
mw = stats.mannwhitneyu(zs, zp)
print(f"  check Mann-Whitney: U={mw.statistic:.0f}, p={mw.pvalue:.4f}, rank-biserial={2 * mw.statistic / (len(zs) * len(zp)) - 1:.4f}")
pooled = stats.ttest_ind(zs, zp)
print(f"  check pooled t: t={pooled.statistic:.3f}, df={len(zs) + len(zp) - 2}, p={pooled.pvalue:.4f}")
circ = rr.groupby(["circuit", "street"]).z.mean().reset_index()
cs, cp = circ[circ.street].z, circ[~circ.street].z
tc, nuc, pc, dc, loc_, hic, _ = welch(cs, cp)
print(f"  check circuit-level ({len(cs)} street, {len(cp)} permanent circuits): diff={dc:.4f}, "
      f"t={tc:.3f}, nu={nuc:.1f}, p={pc:.4f}, CI [{loc_:.4f}, {hic:.4f}]")
print("  street circuits mean rho:", rr[rr.street].groupby("circuit").rho.agg(["mean", "size"]).round(3).to_dict("index"))
print(f"  shape: skew z S {zs.skew():.2f}, P {zp.skew():.2f}")

# ---------------- Test F: pit consistency ----------------
print("=" * 70, "\nTEST F: variance of pit delta, top 4 vs rest")
dd = df.dropna(subset=["pit_delta_s"])
T, R = dd[dd.top_team].pit_delta_s.to_numpy(), dd[~dd.top_team].pit_delta_s.to_numpy()
nT, nR, sT, sR = len(T), len(R), T.std(ddof=1), R.std(ddof=1)
F = sT**2 / sR**2
cdf = stats.f.cdf(F, nT - 1, nR - 1)
p = 2 * min(cdf, 1 - cdf)
rlo, rhi = F / stats.f.ppf(0.975, nT - 1, nR - 1), F / stats.f.ppf(0.025, nT - 1, nR - 1)
diffs = np.array([rng.choice(T, nT).std(ddof=1) - rng.choice(R, nR).std(ddof=1) for _ in range(5000)])
slo, shi = np.percentile(diffs, [2.5, 97.5])
print(f"T n={nT} sd={sT:.4f}; R n={nR} sd={sR:.4f}")
print(f"F={F:.4f}, df=({nT - 1}, {nR - 1}), p={p:.3g}, ratio of variances 95% CI [{rlo:.4f}, {rhi:.4f}], "
      f"SD ratio CI [{np.sqrt(rlo):.4f}, {np.sqrt(rhi):.4f}]")
print(f"  sT - sR = {sT - sR:.4f} s, bootstrap 95% CI [{slo:.4f}, {shi:.4f}]")
report("F", F, (nT - 1, nR - 1), p, F, rlo, rhi, sT - sR, 0.15, slo, shi)
for center in ["mean", "median"]:
    lv = stats.levene(T, R, center=center)
    print(f"  check {'Levene' if center == 'mean' else 'Brown-Forsythe'}: W={lv.statistic:.3f}, df=(1, {nT + nR - 2}), p={lv.pvalue:.3g}")
iqr = lambda a: np.subtract(*np.percentile(a, [75, 25]))
print(f"  IQR T {iqr(T):.3f} vs R {iqr(R):.3f}; MAD T {stats.median_abs_deviation(T):.3f} vs R {stats.median_abs_deviation(R):.3f}")
print(f"  shape: skew T {stats.skew(T):.2f}, R {stats.skew(R):.2f}; excess kurtosis T {stats.kurtosis(T):.2f}, R {stats.kurtosis(R):.2f}")

fig, axes = plt.subplots(1, 2, figsize=(6.4, 3), sharey=True, constrained_layout=True)
for ax, a, name, col in [(axes[0], T, "Top-4 teams", "#2a78d6"), (axes[1], R, "All other teams", "#eb6834")]:
    (osm, osr), (sl, ic, _) = stats.probplot(a)
    ax.scatter(osm, osr, s=6, color=col, alpha=.5, edgecolor="none")
    ax.plot(osm, sl * osm + ic, color="#52514e", linewidth=1)
    ax.set_title(f"{name} (n = {len(a):,})", loc="left", fontsize=9, color="#0b0b0b")
    ax.set_xlabel("Normal quantiles", fontsize=8, color="#52514e")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.set_facecolor("#fcfcfb")
    ax.tick_params(labelsize=7, colors="#52514e")
axes[0].set_ylabel("Pit delta (s)", fontsize=8, color="#52514e")
fig.savefig("report/figures/qq_pit_delta.png", dpi=200, facecolor="#fcfcfb")

# ---------------- Holm ----------------
res = pd.DataFrame(results).set_index("test")
def holm(pvals):
    order = pvals.sort_values()
    m = len(order)
    adj = np.maximum.accumulate([min(1, (m - k) * pv) for k, pv in enumerate(order)])
    return pd.Series(adj, index=order.index)
res["holm_p_all6"] = holm(res.p)
res["holm_reject_all6"] = res.holm_p_all6 < ALPHA
print("=" * 70, "\nSUMMARY (Holm over all 6)")
pd.set_option("display.width", 200)
print(res.drop(columns=["df"]).round(5).to_string())
print("\nHolm-adjusted p for every 5-test subset (row = dropped test):")
rows = {}
for keep in combinations(res.index, 5):
    dropped = (set(res.index) - set(keep)).pop()
    rows[dropped] = holm(res.p[list(keep)])
sub = pd.DataFrame(rows).T.sort_index()
print(sub.map(lambda v: f"{v:.3g}" if pd.notna(v) else "-").to_string())
res.to_csv("data/test_results.csv")
