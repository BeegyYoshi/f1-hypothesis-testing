# 1. Dataset

## Source

The data come from the **Jolpica F1 database** (<https://api.jolpi.ca>). Jolpica is the community successor to the Ergast Developer API, which was retired after the 2024 season, and it keeps Ergast's API format. We downloaded its public CSV dump (snapshot dated 9 October 2026), which covers every World Championship race from the 1950 British Grand Prix to round 16 of 2026, held on 4 October 2026.

The dump is a relational database of 18 tables. We use seven of them:

- `session`: races, qualifying and practice sessions
- `sessionentry`: one driver's result in one session
- `round`: a Grand Prix weekend
- `circuit`, `driver`, `team` and `pitstop`

The tables `season`, `roundentry` and `teamdriver` serve only as keys for the joins.

## Analysis table

We keep only race sessions (type `R`) and join the other tables to them, so that **one row is one driver's result in one Grand Prix**. Each driver's pit stops are aggregated into a stop count and a mean stop duration.

**Result: 26,225 rows × 26 columns, covering 1,165 races.**

## Size after encoding

Of the 26 columns, 18 are numeric, boolean or a date (stored as an ordinal day number), so each one stays a single column. The other 8 are nominal text columns, and one-hot encoding turns each into one indicator column per distinct value:

| Text column | Distinct values = new columns |
|---|---:|
| driver | 818 |
| constructor | 205 |
| finish status (`detail`) | 136 |
| circuit | 78 |
| race name | 56 |
| driver nationality | 40 |
| circuit country | 34 |
| constructor nationality | 23 |
| **Total one-hot columns** | **1,390** |

```
#attributes                 = 18 + 1,390        = 1,408
#instances × #attributes    = 26,225 × 1,408    = 36,924,800  ≥ 3,000,000  ✔
```

The table is about **12 times** the required size. Before encoding it has 26,225 × 26 = 681,850 cells. The hypothesis tests use the hybrid era (2014–2026), a subset of 5,457 rows.

## Selected features and their real-world meaning

- **`grid`**: the starting slot, set mainly by qualifying (1 = pole position). A value of 0 means the car started from the pit lane.
- **`position`**: the finishing order. **`is_classified`**: whether the driver covered enough of the race distance (90%) to be classified.
- **`points`**: championship points scored in the race (25 for a win under the current system).
- **`detail`**: the finish status, such as *Finished*, *+1 Lap*, *Accident*, *Engine* or *Gearbox*. It separates mechanical failures from driver errors.
- **`laps_completed`** versus **`scheduled_laps`**: how far the car got. The gap shows how early a retirement came.
- **`constructor`**: the team that built and runs the car, for example Mercedes, Red Bull or Ferrari. It stands in for car performance.
- **`circuit`**, with **`latitude`**, **`longitude`** and **`altitude`**: the track. Altitude matters for engine power and cooling, as at Mexico City, 2,227 m above sea level.
- **`pit_stops`** and **`mean_pit_s`**: the number of stops and the mean time from pit-lane entry to exit (around 22–24 s), which includes the stationary tyre change. These data exist only from 2011 onward.
- **`driver_age`**: the driver's age on race day, computed from the date of birth.
- **`fastest_lap_rank`** and **`race_time_s`**: the driver's pace. The race time exists only for the winner and for drivers on the lead lap.
