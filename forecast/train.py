"""
Hourly demand forecast.

Trains a model on older data, tests it on the last 90 days, and compares it
with a simple baseline: "same hour last week".

Usage:
    python forecast/train.py
"""

import duckdb
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

DATA = "dashboard/fct_hourly.parquet"
TEST_DAYS = 90
FEATURES = ["hour_ending", "day_of_week", "month",
            "temperature_c", "demand_last_week"]


def load_data():
    """One row per hour, with the demand from the same hour 7 days earlier."""
    return duckdb.sql(f"""
        SELECT
            t.hour_start_utc,
            t.hour_ending,
            dayofweek(t.date_est)      AS day_of_week,
            t.month,
            t.temperature_c,
            t.ontario_demand_mw,
            w.ontario_demand_mw        AS demand_last_week,
            t.date_est > (SELECT max(date_est) FROM '{DATA}'
                          WHERE temperature_c IS NOT NULL)
                         - INTERVAL {TEST_DAYS} DAY AS is_test
        FROM '{DATA}' t
        JOIN '{DATA}' w
            ON w.hour_start_utc = t.hour_start_utc - INTERVAL 7 DAY
        WHERE t.temperature_c IS NOT NULL
        ORDER BY t.hour_start_utc
    """).df()


def mape(actual, predicted) -> float:
    return float(np.mean(np.abs((actual - predicted) / actual)) * 100)


def main() -> None:
    df = load_data()
    train, test = df[~df.is_test], df[df.is_test]
    print(f"Training hours: {len(train):,}   Test hours: {len(test):,}")

    # Baseline: same hour last week
    baseline_error = mape(test.ontario_demand_mw, test.demand_last_week)

    # Model
    model = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, random_state=42)
    model.fit(train[FEATURES], train.ontario_demand_mw)
    predictions = model.predict(test[FEATURES])
    model_error = mape(test.ontario_demand_mw, predictions)

    print(f"\nBaseline (same hour last week) MAPE: {baseline_error:.2f}%")
    print(f"Model MAPE:                          {model_error:.2f}%")
    print(f"Improvement over baseline:           "
          f"{(1 - model_error / baseline_error) * 100:.0f}%")

    # Save test-period predictions for the dashboard
    results = test[["hour_start_utc", "ontario_demand_mw"]].copy()
    results["forecast_mw"] = predictions.round()
    results["baseline_mw"] = test.demand_last_week
    duckdb.sql("COPY (SELECT * FROM results) "
               "TO 'dashboard/forecast_test.parquet' (FORMAT parquet)")
    print("\nSaved test-period forecasts to dashboard/forecast_test.parquet")


if __name__ == "__main__":
    main()