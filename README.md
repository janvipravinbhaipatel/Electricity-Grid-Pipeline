# Ontario Grid Pipeline

An automated data pipeline that collects Ontario's hourly electricity demand and Toronto's
weather, models it with dbt in DuckDB, tests data quality on every run, and analyses how
temperature drives electricity use.

**Live dashboard:** TODO (added after publishing)

## Architecture

```mermaid
flowchart LR
    A[IESO hourly demand] --> C[ingest.py]
    B[Open-Meteo weather] --> C
    C --> D[(Raw files)]
    D --> E[load.py]
    E --> F[(DuckDB)]
    F --> G[dbt models + tests]
    G --> H[export.py]
    H --> I[Streamlit dashboard]
```

The whole pipeline runs daily through `run_pipeline.py`, and each run is logged.

## Tech stack

Python, SQL, DuckDB, dbt, Streamlit, Git

## Data

| Source | What | Frequency |
|---|---|---|
| [IESO](https://www.ieso.ca/power-data) | Ontario electricity demand (MW) | Hourly |
| [Open-Meteo](https://open-meteo.com) | Toronto air temperature | Hourly |

Coverage: January 2024 to today, about 24,000 hours.

## dbt models

| Model | Layer | Purpose |
|---|---|---|
| `stg_demand` | Staging | Converts IESO's Eastern Standard Time hours to UTC, removes duplicates |
| `stg_weather` | Staging | Drops missing readings, removes duplicates |
| `fct_hourly` | Mart | One row per hour: demand joined with temperature |

9 data tests run on every build: unique and non-null hours, plus realistic ranges for
demand (8,000 to 30,000 MW) and temperature (-40 to 45°C).

 ## Key findings

- **Heat drives demand more than cold.** Average demand is lowest at 10 to 15°C
  (about 14,300 MW), rises to about 19,300 MW in the coldest hours, and to about
  24,300 MW above 35°C, roughly 70% above the mild-weather level. A likely reason is that
  much of Ontario's heating uses natural gas, while air conditioning runs on electricity.
- **Daily pattern:** demand is lowest around 3 to 4 a.m. (about 14,000 MW) and peaks
  around 5 to 6 p.m. Eastern Standard Time (about 18,600 MW).
- **Seasonal pattern:** the highest daily peaks come in July each year, with smaller
  winter peaks and the lowest demand in spring and autumn.
- **Data quality:** the pipeline's checks found missing hours in IESO's published data
  for 1 May 2025.

## Design decisions

- **Raw data is stored untouched,** so any transformation bug can be fixed by reprocessing,
  without downloading again.
- **Reruns are safe (idempotent):** files are overwritten by date and tables are rebuilt,
  so running twice never creates duplicates.
- **Time zones are aligned explicitly:** IESO reports "hour ending" in Eastern Standard Time
  all year, while the weather is in UTC. Getting this wrong would silently match every
  temperature to the wrong hour.
- **Left join for weather:** the weather archive runs a few days behind, so recent hours are
  kept with an empty temperature instead of being dropped.
- **Tests gate the dashboard:** if a dbt test fails, the pipeline stops before exporting,
  so bad data never reaches the charts.

## How to run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt

python backfill.py              # one-time: download history
python run_pipeline.py          # ingest, load, dbt build, export
streamlit run dashboard/app.py  # open the dashboard
```

## Next steps

- GitHub Actions to run the tests on every push and the pipeline in the cloud
- Next-day demand forecast