"""EDA plots for report point 4, one per planned test, each with the number behind its takeaway.

Run: python src/eda.py   (after prepare.py). Figures go to report/figures/eda_*.png
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

df = pd.read_csv("data/f1_clean.csv")
pit = pd.read_csv("data/pit_stops_clean.csv")

# reference palette (dataviz skill): categorical slots 1-2, blue ramp for ordered outcomes, text inks
BLUE, ORANGE = "#2a78d6", "#eb6834"
RAMP = ["#104281", "#2a78d6", "#86b6ef"]  # podium, points, no points (dark = better)
GRAY, INK, INK2, SURFACE = "#c3c2b7", "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE})

def save(fig, ax, name, title):
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    fig.savefig(f"report/figures/eda_{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

fin = df[df.is_classified]

# 1. grid vs finish (Test A)
g = fin.groupby("grid").position.agg(["mean", lambda s: s.quantile(.25), lambda s: s.quantile(.75), "size"])
g.columns = ["mean", "q1", "q3", "n"]
g = g[g.n >= 30]
fig, ax = plt.subplots(figsize=(6, 3.4))
ax.fill_between(g.index, g.q1, g.q3, color=BLUE, alpha=.18, linewidth=0, label="middle 50% of finishes")
ax.plot(g.index, g["mean"], color=BLUE, linewidth=2, marker="o", markersize=4, label="mean finish")
ax.plot([1, g.index.max()], [1, g.index.max()], color=INK2, linewidth=1, linestyle="--", label="finish = grid")
ax.set(xlabel="Starting grid position", ylabel="Finishing position", xticks=range(1, int(g.index.max()) + 1, 2))
ax.invert_yaxis()
ax.legend(frameon=False, fontsize=8, labelcolor=INK2)
save(fig, ax, "grid_finish", "Mean finishing position by grid slot, classified finishers 2014–2026")
r = stats.pearsonr(fin.grid, fin.position).statistic
print(f"[1] n={len(fin)}, r={r:.3f}, r2={r * r:.3f}; P1 starters mean finish {g.loc[1, 'mean']:.2f}, "
      f"P10 {g.loc[10, 'mean']:.2f}, P20 {g.loc[20, 'mean']:.2f}" if 20 in g.index else "")

# 2. pole win rate by season (Test B)
poles = df[df.grid == 1].assign(won=lambda d: d.winner)
yr = poles.groupby("year").won.agg(["mean", "size"])
fig, ax = plt.subplots(figsize=(6, 3.2))
era1 = yr.index <= 2019
for mask, lo, hi, col, lab in [(era1, 2013.6, 2019.4, BLUE, "2014–2019"), (~era1, 2019.6, 2026.4, ORANGE, "2020–2026")]:
    m = poles[poles.year.isin(yr.index[mask])].won.mean()
    ax.bar(yr.index[mask], yr["mean"][mask], color=col, width=.7, label=f"{lab} (era mean {m:.0%}, black line)")
    ax.hlines(m, lo, hi, color=INK, linewidth=1)
ax.set(ylabel="Share of races won from pole", ylim=(0, 1), xticks=yr.index)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.tick_params(axis="x", labelsize=7)
ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper left", ncol=1)
save(fig, ax, "pole_win", "Pole-to-win rate by season (2026 partial)")
e1, e2 = poles[poles.year <= 2019].won, poles[poles.year >= 2020].won
print(f"[2] 2014-19 {e1.mean():.3f} ({e1.sum()}/{len(e1)}), 2020+ {e2.mean():.3f} ({e2.sum()}/{len(e2)})")

# 3. finish category by constructor (Test C)
teams = ["mercedes", "red_bull", "ferrari", "mclaren"]
names = {"mercedes": "Mercedes", "red_bull": "Red Bull", "ferrari": "Ferrari", "mclaren": "McLaren", "rest": "All other teams"}
cats = ["podium", "points", "no_points", "retired"]
labels = ["Podium (P1–3)", "Points (P4–10)", "No points", "Retired"]
grp = df.assign(team=df.constructor.where(df.top_team, "rest"))
tab = pd.crosstab(grp.team, grp.finish_cat, normalize="index")[cats].loc[teams + ["rest"]]
fig, ax = plt.subplots(figsize=(6, 2.9))
left = np.zeros(len(tab))
for cat, lab, col in zip(cats, labels, RAMP + [GRAY]):
    ax.barh([names[t] for t in tab.index], tab[cat], left=left, color=col, edgecolor=SURFACE, linewidth=2, label=lab)
    for i, v in enumerate(tab[cat]):
        if v >= .08:
            ax.text(left[i] + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=7.5,
                    color="white" if col in RAMP[:2] else INK)
    left += tab[cat].values
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.legend(frameon=False, fontsize=8, labelcolor=INK2, ncol=4, loc="upper left", bbox_to_anchor=(0, -.12))
save(fig, ax, "finish_cat", "How each team's race entries end, 2014–2026")
print("[3]", (tab * 100).round(1).to_dict("index"))

# 4. per-race grid-finish correlation, street vs permanent (Test E)
def race_rho(d):
    d = d[d.is_classified]
    return stats.spearmanr(d.grid, d.position).statistic if len(d) >= 10 else np.nan
rr = df.groupby(["year", "round", "street"]).apply(race_rho, include_groups=False).dropna().rename("rho").reset_index()
fig, ax = plt.subplots(figsize=(6, 2.8))
rng = np.random.default_rng(0)
for i, (flag, lab, col) in enumerate([(False, "Permanent", BLUE), (True, "Street", ORANGE)]):
    v = rr[rr.street == flag].rho
    ax.scatter(v, i + rng.uniform(-.18, .18, len(v)), s=12, color=col, alpha=.6, edgecolor="none")
    ax.vlines(v.median(), i - .3, i + .3, color=INK, linewidth=2)
    ax.text(v.median(), i + .36, f"median {v.median():.2f} (n = {len(v)})", ha="center", fontsize=8, color=INK)
ax.set(yticks=[0, 1], yticklabels=["Permanent", "Street"], xlabel="Spearman ρ between grid and finish, one dot per race",
       ylim=(-.5, 1.6))
save(fig, ax, "track_type", "How well the grid predicts each race's result, by track type")
print("[4]", rr.groupby("street").rho.describe().round(3).to_dict("index"))

# 5. pit delta per driver-race (Tests D and F)
d = df.dropna(subset=["pit_delta_s"])
groups = [("Top-4 winners", d[d.top_team & d.winner].pit_delta_s, BLUE),
          ("Top-4 non-winners", d[d.top_team & ~d.winner].pit_delta_s, BLUE),
          ("All other teams", d[~d.top_team].pit_delta_s, ORANGE)]
fig, ax = plt.subplots(figsize=(6, 2.9))
bp = ax.boxplot([g for _, g, _ in groups], orientation="horizontal", widths=.5, patch_artist=True, showfliers=True,
                flierprops=dict(marker="o", markersize=2.5, markerfacecolor=GRAY, markeredgecolor="none"),
                medianprops=dict(color=INK, linewidth=1.5), whiskerprops=dict(color=INK2), capprops=dict(color=INK2))
for box, (_, _, col) in zip(bp["boxes"], groups):
    box.set(facecolor=col, alpha=.35, edgecolor=col)
ax.axvline(0, color=INK2, linewidth=1, linestyle="--")
ax.set_yticks(range(1, 4), [f"{n}\n(n = {len(g):,}, SD {g.std():.2f} s)" for n, g, _ in groups], fontsize=8)
ax.invert_yaxis()
ax.set_xlabel("Driver's mean pit time minus race median (s)  ← faster | slower →")
save(fig, ax, "pit_delta", "Pit-stop time relative to the race median, per driver-race")
for n, g, _ in groups:
    print(f"[5] {n}: n={len(g)}, mean {g.mean():.2f}, median {g.median():.2f}, sd {g.std():.2f}")
