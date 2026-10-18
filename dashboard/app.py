"""
Ontario electricity demand dashboard.

Usage:
    streamlit run dashboard/app.py
"""

from pathlib import Path

import duckdb
import streamlit as st

DATA = (Path(__file__).parent / "fct_hourly.parquet").as_posix()

st.set_page_config(page_title="Ontario Grid Demand", layout="wide")
st.title("Ontario electricity demand and temperature")
st.caption("Hourly data from IESO (Ontario's grid operator) and Open-Meteo, "
           "updated daily by an automated pipeline.")


@st.cache_data
def query(sql: str):
    return duckdb.sql(sql.replace("{data}", f"'{DATA}'")).df()


# ---- Headline numbers --------------------------------------------------
kpi = query("""
    SELECT count(*)                          AS hours,
           min(date_est)                     AS first_day,
           max(date_est)                     AS last_day,
           round(avg(ontario_demand_mw))     AS avg_mw,
           max(ontario_demand_mw)            AS peak_mw
    FROM {data}
""").iloc[0]

c1, c2, c3 = st.columns(3)
c1.metric("Hours of data", f"{int(kpi.hours):,}",
          help=f"{kpi.first_day} to {kpi.last_day}")
c2.metric("Average demand", f"{int(kpi.avg_mw):,} MW")
c3.metric("Peak demand", f"{int(kpi.peak_mw):,} MW")

# ---- Chart 1: demand vs temperature -------------------------------------
st.subheader("Demand rises in both cold and hot weather")
by_temp = query("""
    SELECT CAST(floor(temperature_c / 5) * 5 AS INTEGER) AS temperature_c,
           round(avg(ontario_demand_mw))                AS avg_demand_mw
    FROM {data}
    WHERE temperature_c IS NOT NULL
    GROUP BY 1 ORDER BY 1
""")
st.bar_chart(by_temp, x="temperature_c", y="avg_demand_mw",
             x_label="Temperature (°C, 5-degree bands)",
             y_label="Average demand (MW)")

# ---- Chart 2: daily pattern ---------------------------------------------
st.subheader("Demand by hour of day")
by_hour = query("""
    SELECT hour_ending                    AS hour,
           round(avg(ontario_demand_mw))  AS avg_demand_mw
    FROM {data}
    GROUP BY 1 ORDER BY 1
""")
st.line_chart(by_hour, x="hour", y="avg_demand_mw",
              x_label="Hour ending (Eastern Standard Time)",
              y_label="Average demand (MW)")

# ---- Chart 3: trend over time -------------------------------------------
st.subheader("Daily average demand over time")
by_day = query("""
    SELECT date_est                       AS day,
           round(avg(ontario_demand_mw))  AS avg_demand_mw
    FROM {data}
    GROUP BY 1 ORDER BY 1
""")
st.line_chart(by_day, x="day", y="avg_demand_mw",
              x_label="Date", y_label="Average demand (MW)")