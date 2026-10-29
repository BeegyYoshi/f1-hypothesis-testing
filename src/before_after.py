"""Before-and-after observations of the data preparation (report point 3).

Before = the 2014+ rows of data/f1_race_results.csv with the raw pit stops.
After  = data/f1_clean.csv and data/pit_stops_clean.csv from prepare.py.
Run:    python src/before_after.py   (after build_dataset.py and prepare.py)
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

raw = pd.read_csv("data/f1_race_results.csv")
before = raw[raw.year >= 2014].copy()
after = pd.read_csv("data/f1_clean.csv")

pit_b = pd.read_csv("data/raw/formula_one_pitstop.csv", usecols=["session_entry_id", "duration"])
pit_b["duration_s"] = pd.to_timedelta(pit_b.duration).dt.total_seconds()
pit_b = pit_b.merge(before[["entry_id", "year", "round", "constructor", "position", "is_classified"]],
                    left_on="session_entry_id", right_on="entry_id")
pit_b["delta_s"] = pit_b.duration_s - pit_b.groupby(["year", "round"]).duration_s.transform("median")
pit_a = pd.read_csv("data/pit_stops_clean.csv")

races = lambda d: d[["year", "round"]].drop_duplicates().shape[0]
print("SHAPE")
print(f"  before: {len(before):,} rows x {before.shape[1]} cols, {races(before)} races")
print(f"  after:  {len(after):,} rows x {after.shape[1]} cols, {races(after)} races")
print("  new columns:", sorted(set(after.columns) - set(before.columns)))

print("\nTYPES (before -> after)")
for c in ["date", "is_classified", "grid", "pit_stops"]:
    print(f"  {c}: {before[c].dtype} -> {pd.read_csv('data/f1_clean.csv', parse_dates=['date'])[c].dtype}")

print("\nMISSING CELLS (before -> after)")
for c in sorted(set(before.columns[before.isna().any()]) | set(after.columns[after.isna().any()])):
    b = before[c].isna().sum() if c in before else "-"
    print(f"  {c}: {b} -> {after[c].isna().sum()}")
print(f"  total: {before.isna().sum().sum():,} -> {after.isna().sum().sum():,}")

print("\nGRID AND FINISH")
for label, d in [("before", before.assign(cls=before.is_classified.eq("t"))), ("after", after.assign(cls=after.is_classified))]:
    f = d[d.cls]
    rho = stats.spearmanr(f.grid, f.position).statistic
    r = stats.pearsonr(f.grid, f.position).statistic
    pole = d[d.grid == 1]
    print(f"  {label}: grid {d.grid.min():.0f}-{d.grid.max():.0f}, mean grid {d.grid.mean():.2f}; "
          f"classified finishers {len(f):,}: Pearson r {r:.3f}, Spearman rho {rho:.3f}; "
          f"pole-sitter win rate {(pole.position.eq(1) & pole.cls).mean():.3f} ({len(pole)} poles)")

print("\nFINISH CATEGORIES (is_classified as given -> DSQ corrected)")
b_cls = before.is_classified.eq("t")
b_cat = np.select([b_cls & (before.position <= 3), b_cls & (before.position <= 10), b_cls], ["podium", "points", "no_points"], "retired")
print("  before:", pd.Series(b_cat).value_counts().to_dict())
print("  after: ", after.finish_cat.value_counts().to_dict())

print("\nPIT STOPS (per stop)")
for label, p in [("before", pit_b), ("after", pit_a)]:
    s = p.duration_s
    print(f"  {label}: n {len(p):,}, mean {s.mean():.2f}, median {s.median():.2f}, sd {s.std():.2f}, "
          f"min {s.min():.1f}, max {s.max():.1f}, skew {s.skew():.2f}, kurtosis {s.kurt():.1f}, "
          f"stops > 60 s {(s > 60).sum()}")

print("\nPIT DELTA BY GROUP (mean of per-stop delta, s; what Test D will compare)")
top = ["mercedes", "red_bull", "ferrari", "mclaren"]
pit_b["top_team"] = pit_b.constructor.isin(top)
pit_b["winner"] = pit_b.position.eq(1) & pit_b.is_classified.eq("t")
for label, p in [("before", pit_b), ("after", pit_a)]:
    g = p.groupby("top_team").delta_s.agg(["mean", "std"])
    w = p.groupby("winner").delta_s.mean()
    print(f"  {label}: top teams mean {g.loc[True, 'mean']:.2f} (sd {g.loc[True, 'std']:.2f}), "
          f"rest mean {g.loc[False, 'mean']:.2f} (sd {g.loc[False, 'std']:.2f}); "
          f"winners {w.loc[True]:.2f} vs non-winners {w.loc[False]:.2f}")

# figure: per-stop durations before vs after, shared log axis so the red-flag cluster stays visible
fig, axes = plt.subplots(2, 1, figsize=(7, 4.2), sharex=True, sharey=True, constrained_layout=True)
bins = np.logspace(np.log10(10), np.log10(3200), 70)
for ax, p, title, color in [(axes[0], pit_b, f"Before cleaning: {len(pit_b):,} stops", "#eb6834"),
                            (axes[1], pit_a, f"After cleaning: {len(pit_a):,} stops", "#2a78d6")]:
    ax.hist(p.duration_s, bins=bins, color=color, edgecolor="#fcfcfb", linewidth=0.5)
    ax.set_yscale("log")
    ax.set_facecolor("#fcfcfb")
    ax.axvline(60, color="#52514e", linewidth=1, linestyle="--")
    ax.set_title(title, loc="left", fontsize=10, color="#0b0b0b")
    ax.set_ylabel("Stops (log scale)", fontsize=9, color="#52514e")
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.tick_params(colors="#52514e", labelsize=8)
axes[0].annotate("red-flag stoppages\n(cars parked in pit lane)", xy=(1500, 20), xytext=(250, 300),
                 fontsize=8, color="#52514e", arrowprops=dict(arrowstyle="->", color="#52514e", lw=0.8))
axes[0].text(63, 1500, "60 s ceiling", fontsize=8, color="#52514e")
axes[1].set_xscale("log")
axes[1].set_xticks([10, 20, 30, 60, 100, 300, 1000, 3000], labels=["10", "20", "30", "60", "100", "300", "1000", "3000"])
axes[1].set_xlabel("Pit-lane time per stop (seconds, log scale)", fontsize=9, color="#52514e")
fig.savefig("report/figures/pit_before_after.png", dpi=200, facecolor="#fcfcfb")
print("\nsaved report/figures/pit_before_after.png")
