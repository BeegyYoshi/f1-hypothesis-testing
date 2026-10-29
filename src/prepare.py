"""Data preparation for the hypothesis tests (report point 2).

Input:  data/f1_race_results.csv  (from build_dataset.py) + data/raw/formula_one_pitstop.csv
Output: data/f1_clean.csv          one row per driver per race, hybrid era, ready for tests A-F
        data/pit_stops_clean.csv   one row per pit stop, with the race-median-adjusted time
Run:    python src/prepare.py
"""
import pandas as pd

# fixed before looking at any test result (see plan doc)
TOP_TEAMS = ["mercedes", "red_bull", "ferrari", "mclaren"]  # most points 2014+
STREET = ["monaco", "marina_bay", "baku", "jeddah", "vegas", "miami"]
PIT_CEILING_S = 60.0  # no normal stop takes this long anywhere: red-flag stoppage
PIT_CUTOFF_S = 10.0  # a stop this far above its race median is a repair or penalty, not a service

log = []
def step(name, frame):
    log.append((name, len(frame)))
    return frame

df = step("raw table (1950-2026)", pd.read_csv("data/f1_race_results.csv"))

# 1. duplicates: a driver may appear once per race
df = step("drop exact duplicate rows", df.drop_duplicates(subset=df.columns.drop("entry_id")))
df = step("drop repeated (year, round, driver)", df.drop_duplicates(["year", "round", "driver"]))

# 2. scope: hybrid era only
df = step("keep hybrid era (2014+)", df[df.year >= 2014])

# 3. 2021 Belgian GP: no green-flag lap, result = grid order, no pit stops -> not a race outcome
df = step("drop 2021 Belgian GP (no racing laps)", df[~((df.year == 2021) & (df["round"] == 12))])

# 4. pit-lane starts: grid 0 is not a starting position
df = step("drop pit-lane starts (grid = 0)", df[df.grid > 0])

# 5. missing values
na_before = df.isna().sum()
df["pit_stops"] = df.pit_stops.fillna(0).astype(int)  # every remaining race has pit data, so no record = no stop
# race_time_s (lapped/retired), fastest_lap_rank (no timed lap), mean_pit_s (no stop) stay NaN:
# they are missing by design, and imputing them would invent race results

# 6. encoding: types and the group labels the tests use
df["date"] = pd.to_datetime(df.date)
df["is_classified"] = df.is_classified.eq("t") & df.detail.ne("Disqualified")  # 3 DSQs are flagged classified in the source
df["top_team"] = df.constructor.isin(TOP_TEAMS)
df["street"] = df.circuit.isin(STREET)
df["finish_cat"] = "retired"
df.loc[df.is_classified, "finish_cat"] = "no_points"
df.loc[df.is_classified & (df.position <= 10), "finish_cat"] = "points"
df.loc[df.is_classified & (df.position <= 3), "finish_cat"] = "podium"
df["winner"] = df.position.eq(1) & df.is_classified

# 7. pit-stop outliers, per stop: duration minus that race's median stop (all stops of the race)
pit = pd.read_csv("data/raw/formula_one_pitstop.csv", usecols=["session_entry_id", "duration", "number"])
pit["duration_s"] = pd.to_timedelta(pit.duration).dt.total_seconds()
pit = pit.merge(df[["entry_id", "year", "round", "constructor", "top_team", "winner"]],
                left_on="session_entry_id", right_on="entry_id").drop(columns=["session_entry_id", "duration"])
pit_before = pit.copy()
# in red-flag races most "stops" are cars parked in the pit lane, which drags the race median to 900+ s,
# so first drop anything no normal stop can take (slowest pit lane ~30 s), then take the median
pit = pit[pit.duration_s <= PIT_CEILING_S]
n_ceiling = len(pit)
pit["race_median_s"] = pit.groupby(["year", "round"]).duration_s.transform("median")
pit["delta_s"] = pit.duration_s - pit.race_median_s
pit = pit[pit.delta_s <= PIT_CUTOFF_S]

agg = pit.groupby("entry_id").agg(mean_pit_s=("duration_s", "mean"), pit_delta_s=("delta_s", "mean"))
df = df.drop(columns="mean_pit_s").merge(agg, on="entry_id", how="left")

assert not df.duplicated(["year", "round", "driver"]).any() and (df.grid > 0).all()
assert pit.delta_s.max() <= PIT_CUTOFF_S and df.pit_stops.notna().all()
df.to_csv("data/f1_clean.csv", index=False)
pit.to_csv("data/pit_stops_clean.csv", index=False)

# --- report numbers ---
print("ROW LOG")
for name, n in log:
    print(f"  {n:>6,}  {name}")
print(f"\nfinal: {len(df):,} rows x {df.shape[1]} cols, {df[['year', 'round']].drop_duplicates().shape[0]} races, "
      f"{df.year.min()}-{df.year.max()}")
print("\nMISSING (after scope filters, before handling):", na_before[na_before > 0].to_dict())
print("MISSING (after):", df.isna().sum()[df.isna().sum() > 0].to_dict())
print(f"\nPIT STOPS: {len(pit_before):,} -> {n_ceiling:,} after > {PIT_CEILING_S:.0f} s ceiling "
      f"-> {len(pit):,} after delta > {PIT_CUTOFF_S:.0f} s cutoff")
for label, p in [("before", pit_before), ("after", pit)]:
    print(f"  {label}: duration mean {p.duration_s.mean():.2f} s, median {p.duration_s.median():.2f}, "
          f"max {p.duration_s.max():.1f}, sd {p.duration_s.std():.2f}, skew {p.duration_s.skew():.2f}")
med = pit.groupby(["year", "round"]).race_median_s.first()
print(f"  race medians after: {med.min():.1f}-{med.max():.1f} s; delta sd {pit.delta_s.std():.2f} s")
print(f"  driver-races with a pit_delta_s value: {df.pit_delta_s.notna().sum():,}")
print("\nGROUPS")
print("  top team rows:", df.top_team.sum(), "| rest:", (~df.top_team).sum())
print("  street races:", df[df.street][["year", "round"]].drop_duplicates().shape[0],
      "| permanent races:", df[~df.street][["year", "round"]].drop_duplicates().shape[0])
print("  finish_cat:", df.finish_cat.value_counts().to_dict())
print("  races with a classified winner:", df.winner.sum())
