# 2. Data Preparation

All steps are in `src/prepare.py`, which reads the table from Section 1 and writes two files: `data/f1_clean.csv` (one row per driver per race) and `data/pit_stops_clean.csv` (one row per pit stop). Every rule below was fixed **before any test was run**, so the cleaning cannot be tuned to make a result significant.

## Summary of row counts

| Step | Rows left | Removed |
|---|---:|---:|
| Raw table, 1950–2026 | 26,225 | – |
| Drop exact duplicate rows | 26,225 | 0 |
| Drop repeated (year, round, driver) | 26,136 | 89 |
| Keep hybrid era (2014–2026) | 5,457 | 20,679 |
| Drop 2021 Belgian GP | 5,437 | 20 |
| Drop pit-lane starts (grid = 0) | **5,385** | 52 |

**Final table:** 5,385 driver-races from 267 races, 2014–2026, with 32 columns: the 26 original columns and the row key `entry_id`, plus `pit_delta_s` (step 6) and 4 group labels (step 7). `mean_pit_s` is recomputed from the cleaned stops.

## 1. Duplicates

**What:** We checked for fully identical rows (none) and for a driver appearing more than once in the same race. There were **89** such repeats, all in the 1950s, and we kept the first row of each.

**Why:** In the 1950s two drivers could share one car, and a driver could take over a teammate's car mid-race, so one driver could get two results in one race. Every test treats a driver-race as one independent observation, and counting a driver twice in one race would count that observation twice. None of these repeats is in the hybrid era, so the tests are unaffected either way.

## 2. Scope: the hybrid era (2014–2026)

**What:** We keep only seasons from 2014 on, when the 1.6 L turbo-hybrid engines were introduced.

**Why:** Pit-stop times exist only from 2011, and points systems, car rules and race formats changed many times before 2014. Comparing 1960 and 2024 cars would mix rule changes with the effects we want to measure. One rule era keeps the comparison fair, and with 5,457 rows it is still large.

## 3. Removing a race that was not a race: 2021 Belgian GP

**What:** We drop all 20 rows of the 2021 Belgian Grand Prix.

**Why:** Heavy rain meant the cars completed only laps behind the safety car and never raced. The finishing order is exactly the starting order, and no pit stops were made. Keeping it would add a perfect grid-to-finish correlation (Tests A and E) to a race in which nothing could change. It is the only race in the era with no pit-stop data.

## 4. Pit-lane starts (grid = 0)

**What:** We drop the 52 driver-races with `grid = 0`.

**Why:** A grid value of 0 is not a position. It is a code for a car that started from the pit lane, usually after a penalty or a setup change made under parc fermé rules. Read as a number, 0 would look *better* than pole position (1) and would distort every test that uses the grid (A, E). These cars really started behind the whole field, but placing them at "last + 1" would mean inventing a value.

## 5. Missing values

| Column | Missing (era) | Reason it is missing | What we did |
|---|---:|---|---|
| `pit_stops` | 349 | The driver made no stop, usually because they retired early | Set to **0**. Every remaining race has pit data, so no record means no stop |
| `race_time_s` | 1,911 | Only the winner and lead-lap finishers get a time | **Left missing.** Not used in any test |
| `fastest_lap_rank` | 33 | Retired before completing a timed lap | **Left missing.** Not used in any test |
| `mean_pit_s`, `pit_delta_s` | 349 → 460 | No stop, plus 111 driver-races whose only stops were removed as outliers (step 6) | **Left missing.** These rows are excluded from the pit test (D) |

**Why no imputation:** none of these values are missing at random. They are missing *because of* what happened in the race: a driver who retired has no race time. Filling in a mean or median would create race results that never happened and pull the groups toward each other. The variables the tests depend on (grid, position, points, status, constructor, circuit) have **no missing values**.

## 6. Outliers

**Positions, ages and laps:** grid and finishing positions run 1–22, driver ages 17.5–45.2 years (Max Verstappen debuted at 17), and laps completed never exceed scheduled laps. These are bounded or plausible values, so **nothing is removed**: a driver finishing 20th or retiring on lap 0 is a real result, not an error.

**Pit-stop durations** need cleaning. The recorded time is from pit-lane entry to exit, and in a normal stop that is 16–37 s depending on the track. The raw data, though, run up to **3,069 s**:

1. **Ceiling of 60 s (578 stops removed).** When a race is red-flagged, all cars park in the pit lane for 15–50 minutes, and the data log this as a "stop". No normal stop takes 60 s at any track: that is twice the slowest pit lane. These logged stops dominate red-flag races. At Monaco 2024 the *median* stop was 2,369 s, so a rule based only on the median would remove nothing there.
2. **Race median + 10 s (293 more stops removed).** Each remaining stop is compared with the median stop of its race, which accounts for the pit lane's length. A stop more than 10 s slower than that is a repair (a new front wing), a stop-and-go penalty or a botched wheel change. These are real events, but they measure crashes and penalties, not how fast a crew services the car, which is what Test D asks about.

| | Stops | Mean | Median | Max | SD |
|---|---:|---:|---:|---:|---:|
| Before | 9,759 | 105.5 s | 23.9 s | 3,069.0 s | 357.7 s |
| After | 8,888 | 24.2 s | 23.6 s | 44.7 s | 3.8 s |

The median hardly changes (23.9 → 23.6 s), which shows that only the abnormal tail was removed. Each stop is then converted to **delta = duration − race median**, and averaging over each driver's stops gives `pit_delta_s`, the variable used in Test D.

## 7. Encoding

| Variable | Encoding | Why |
|---|---|---|
| `driver`, `constructor`, `circuit`, `detail`, nationalities, `race_name` | One-hot (Section 1: 1,390 columns) | Nominal: no order, so a number code would imply a false order |
| `grid`, `position` | Kept as integers | Ordinal: 1st is better than 2nd, and the correlation tests need that order |
| `is_classified` | `t`/`f` → boolean | Two-valued |
| `date` | Text → date type | Allows sorting and era splits |
| `top_team` | Boolean: Mercedes, Red Bull, Ferrari, McLaren | The 4 constructors with the most points 2014+. Groups for Test C |
| `street` | Boolean: Monaco, Singapore, Baku, Jeddah, Las Vegas, Miami | Groups for Test E (45 street races, 222 permanent) |
| `finish_cat` | podium (P1–3) / points (P4–10) / no points / retired (not classified, which includes all 17 disqualifications; the source wrongly flags 3 of them as classified, which we corrected) | The 4 outcome categories for Test C |
| `winner` | Boolean: classified in P1 | Groups for Tests B and D |

The groups are fixed lists set by rule (points totals) or by what the track is. Albert Park, Montréal and Madrid also use public roads but were kept as permanent tracks because they were not in the pre-registered list.
