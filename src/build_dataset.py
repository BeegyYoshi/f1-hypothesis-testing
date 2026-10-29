"""Build the analysis table (one row per driver per Grand Prix) from the Jolpica F1 CSV dump
and check the report's size rule: #instances x #attributes >= 3M after encoding.

Source: https://api.jolpi.ca/data/dumps/download/delayed/?dump_type=csv  (unzipped into data/raw/)
Run:    python src/build_dataset.py
"""
import pandas as pd

RAW = "data/raw/formula_one_"
read = lambda name, **kw: pd.read_csv(RAW + name + ".csv", **kw)

session = read("session")
races = session[session.type == "R"][["id", "round_id", "scheduled_laps"]].rename(columns={"id": "session_id"})
entries = read("sessionentry").merge(races, on="session_id")

rnd = read("round")[["id", "circuit_id", "date", "name", "number", "season_id"]].rename(
    columns={"id": "round_id", "name": "race_name", "number": "round"})
season = read("season")[["id", "year"]].rename(columns={"id": "season_id"})
circuit = read("circuit")[["id", "reference", "country", "latitude", "longitude", "altitude"]].rename(
    columns={"id": "circuit_id", "reference": "circuit", "country": "circuit_country"})
round_entry = read("roundentry")[["id", "team_driver_id", "car_number"]].rename(columns={"id": "round_entry_id"})
team_driver = read("teamdriver")[["id", "driver_id", "team_id"]].rename(columns={"id": "team_driver_id"})
driver = read("driver")[["id", "reference", "nationality", "date_of_birth"]].rename(
    columns={"id": "driver_id", "reference": "driver", "nationality": "driver_nationality"})
team = read("team")[["id", "reference", "nationality"]].rename(
    columns={"id": "team_id", "reference": "constructor", "nationality": "constructor_nationality"})

# pit-stop aggregates per driver-race (pit data exists from 2011 on)
pit = read("pitstop")
pit["duration_s"] = pd.to_timedelta(pit.duration, errors="coerce").dt.total_seconds()
pit = pit.groupby("session_entry_id").agg(pit_stops=("id", "size"), mean_pit_s=("duration_s", "mean")).reset_index()

df = (entries
      .merge(rnd, on="round_id").merge(season, on="season_id").merge(circuit, on="circuit_id")
      .merge(round_entry, on="round_entry_id").merge(team_driver, on="team_driver_id")
      .merge(driver, on="driver_id").merge(team, on="team_id")
      .merge(pit, left_on="id", right_on="session_entry_id", how="left"))

df["race_time_s"] = pd.to_timedelta(df.time, errors="coerce").dt.total_seconds()
df["driver_age"] = (pd.to_datetime(df.date) - pd.to_datetime(df.date_of_birth)).dt.days / 365.25
df = df.rename(columns={"id": "entry_id"})[["entry_id", "year", "round", "race_name", "date", "circuit", "circuit_country", "latitude", "longitude", "altitude",
         "driver", "driver_nationality", "driver_age", "constructor", "constructor_nationality", "car_number",
         "grid", "position", "is_classified", "points", "laps_completed", "scheduled_laps", "detail",
         "fastest_lap_rank", "race_time_s", "pit_stops", "mean_pit_s"]]
df.to_csv("data/f1_race_results.csv", index=False)

# encoding: one-hot every text column; numbers and dates stay single columns (date -> ordinal)
cat_cols = ["race_name", "circuit", "circuit_country", "driver", "driver_nationality",
            "constructor", "constructor_nationality", "detail"]
enc = pd.get_dummies(df.drop(columns="entry_id").assign(date=pd.to_datetime(df.date).map(pd.Timestamp.toordinal),
                               is_classified=df.is_classified.eq("t")), columns=cat_cols)
num_cols = df.shape[1] - len(cat_cols) - 1  # entry_id is a row key, not an attribute
assert enc.shape[1] == num_cols + df[cat_cols].nunique().sum()

n, p_raw, p_enc = len(df), df.shape[1] - 1, enc.shape[1]
print(f"years {df.year.min()}-{df.year.max()}, races {df[['year', 'round']].drop_duplicates().shape[0]}")
print(f"raw table: {n:,} rows x {p_raw} columns = {n * p_raw:,} cells")
print("distinct levels per categorical column:", df[cat_cols].nunique().to_dict())
print(f"encoded columns = {num_cols} numeric/date + {enc.shape[1] - num_cols} one-hot = {p_enc}")
print(f"encoded: {n:,} x {p_enc:,} = {n * p_enc:,} cells -> >= 3M: {n * p_enc >= 3_000_000}")
print(f"hybrid era (2014+) subset: {(df.year >= 2014).sum():,} rows")
