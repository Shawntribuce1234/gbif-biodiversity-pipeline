import pandas as pd

from hw2_ds3500 import (
    fetch_gbif_data,
    clean_biodiversity_data,
    enrich_with_state_data
)

def test_fetch_returns_required_columns():
    df = fetch_gbif_data(["Sturnus vulgaris"], 2023)

    required_cols = ["species", "lat", "lon", "date", "state", "coordinate_uncertainty_m"]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"


def test_clean_outputs_month_and_metrics_valid():
    raw = pd.DataFrame({
        "species": ["A", "A", "A"],
        "lat": [1.0, 1.0, None],
        "lon": [2.0, 2.0, 3.0],
        "date": ["2023-01-05", "bad_date", "2023-02-01"],
        "state": ["Massachusetts", "Massachusetts", "Massachusetts"],
        "coordinate_uncertainty_m": [5.0, 5.0, 5.0]
    })

    clean_df, metrics = clean_biodiversity_data(raw)

    assert "month" in clean_df.columns, "month column not detected"
    assert clean_df["month"].between(1, 12).all(), "month out of required range"

    assert metrics["clean_count"] <= metrics["raw_count"], "clean count cannot exceed the raw count"
    assert 0 <= metrics["percent_retained"] <= 100, "percent must be between 0 and 100"


def test_enrich_adds_region_and_area():
    clean_df = pd.DataFrame({
        "species": ["A"],
        "lat": [1.0],
        "lon": [2.0],
        "date": pd.to_datetime(["2023-01-05"]),
        "state": ["Massachusetts"],
        "coordinate_uncertainty_m": [5.0],
        "month": [1]
    })

    state_ref_df = pd.DataFrame({
        "state_name": ["Massachusetts"],
        "abbreviation": ["MA"],
        "region": ["Northeast"],
        "area_sq_km": [27336]
    })

    enriched = enrich_with_state_data(clean_df, state_ref_df)

    assert "region" in enriched.columns, "region column missing after enrichment"
    assert "area_sq_km" in enriched.columns, "area_sq_km column missing after enrichment"
    assert enriched["area_sq_km"].notna().all(), "area_sq_km has missing values"