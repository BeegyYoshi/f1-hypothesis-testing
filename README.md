# F1 Hybrid-Era Hypothesis Testing

Data Science midterm project. We test how much qualifying position, team, era, pit-crew performance and track type shape a Formula 1 race result in the hybrid era (2014–2026), using six hypothesis tests with effect sizes, 95% confidence intervals and Holm correction.

## Data

[Jolpica F1](https://github.com/jolpica/jolpica-f1) database dump (CSV), the community successor to the Ergast API. Our snapshot is dated 9 October 2026, covering 1950 to round 16 of 2026.

The raw dump is not committed. To download it:

```bash
mkdir -p data
curl -L -o data/jolpica-f1-csv.zip "https://api.jolpi.ca/data/dumps/download/delayed/?dump_type=csv"
unzip data/jolpica-f1-csv.zip -d data/raw
```

The latest dump may contain newer races than our snapshot, so the numbers may shift slightly.

## Reproduce

Python 3.12:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/build_dataset.py   # joins the raw tables -> data/f1_race_results.csv, prints the 3M-cell check
python src/prepare.py         # cleaning -> data/f1_clean.csv, data/pit_stops_clean.csv
python src/before_after.py    # before/after comparison + figure
python src/eda.py             # EDA figures
python src/tests.py           # tests A-F, Holm correction -> data/test_results.csv
```

Run the scripts from the project root, in this order. Figures are written to `report/figures/`.

## Layout

| Path | Contents |
|---|---|
| `src/build_dataset.py` | One row per driver per Grand Prix from the 18 raw tables (26,225 × 26) |
| `src/prepare.py` | Duplicates, era filter, pit-lane starts, missing values, pit-stop outliers, encoding |
| `src/before_after.py` | Before-and-after observations of the cleaning |
| `src/eda.py` | Five EDA plots, one per test |
| `src/tests.py` | Tests A–F with robustness checks, CIs, practical verdicts, Holm |
| `data/` | Derived tables (the raw dump is ignored) |
| `report/` | Report sections (Markdown + LaTeX) and figures |

## Tests

| | Question | Test | Result |
|---|---|---|---|
| A | Does grid position predict finishing position? | t-test for Pearson r | r = 0.745, r² = 0.555: matters |
| B | Has the pole-win rate changed between eras? | Two-proportion z-test | 52% vs 56%, p = 0.50: inconclusive |
| C | Do the top teams finish differently? | Chi-square test of independence | V = 0.218: matters |
| D | Do winners have faster pit stops? | Welch t-test | −0.56 s [−0.68, −0.45]: matters |
| E | Does track type change how well the grid predicts the finish? | Welch t-test on Fisher z | p = 0.18: inconclusive |

The full write-up is in `report/section5_tests.md`.
