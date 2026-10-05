import requests
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

GBIF_URL = "https://api.gbif.org/v1/occurrence/search"


def fetch_gbif_data(species_list, year):
    all_dfs = []

    bbox_wkt = "POLYGON((-77.5 38.8, -66.5 38.8, -66.5 47.5, -77.5 47.5, -77.5 38.8))"

    for species in species_list:
        species_records = []
        offset = 0
        limit = 300

        # Sorting the data to put into a dataframe after making API request
        while len(species_records) < 100:
            params = {
                "scientificName": species,
                "year": year,
                "hasCoordinate": "true",
                "country": "US",
                "geometry": bbox_wkt,
                "limit": limit,
                "offset": offset
            }

            response = requests.get(GBIF_URL, params=params)

            if response.status_code != 200:
                print(f"GBIF API request failed for {species}: {response.status_code}")
                break

            data_dct = response.json()
            results = data_dct.get("results", [])

            if len(results) == 0:
                break

            species_records.extend(results)
            offset += limit

        df_species = convert_gbif_to_dataframe({"results": species_records}, species)
        all_dfs.append(df_species)


    if len(all_dfs) == 0:
        return pd.DataFrame(columns=[
            "species", "lat", "lon", "date", "state", "coordinate_uncertainty_m"
        ])

    return pd.concat(all_dfs, ignore_index=True)


def convert_gbif_to_dataframe(data, fallback_species_name):
    records = []

    # Converted retrieved data into a DataFrame
    for obs in data.get("results", []):
        records.append({
            "species": fallback_species_name,
            "lat": obs.get("decimalLatitude"),
            "lon": obs.get("decimalLongitude"),
            "date": obs.get("eventDate"),
            "state": obs.get("stateProvince"),
            "coordinate_uncertainty_m": obs.get("coordinateUncertaintyInMeters")
        })
    return pd.DataFrame(records)


def clean_biodiversity_data(raw_df):
    metrics = {}
    metrics["raw_count"] = len(raw_df)
    df = raw_df.copy()

    removed = {
        "missing_required": 0,
        "invalid_date": 0,
        "duplicates": 0
    }

    # Remove missing required fields
    required_cols = ["species", "lat", "lon", "date", "state", "coordinate_uncertainty_m"]
    before = len(df)
    df = df.dropna(subset=required_cols)
    removed["missing_required"] = before - len(df)

    # Convert dates and remove null values
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    before = len(df)
    df = df.dropna(subset=["date"])
    removed["invalid_date"] = before - len(df)

    # Remove duplicates
    dup_cols = ["species", "lat", "lon", "date"]
    before = len(df)
    df = df.drop_duplicates(subset=dup_cols)
    removed["duplicates"] = before - len(df)

    # Extract month
    df["month"] = df["date"].dt.month

    metrics["clean_count"] = len(df)
    metrics["removed_by_reason"] = removed

    if metrics["raw_count"] == 0:
        metrics["percent_retained"] = 0.0
    else:
        metrics["percent_retained"] = round((metrics["clean_count"] / metrics["raw_count"]) * 100, 2)

    return df, metrics


def enrich_with_state_data(clean_df, state_ref_df):
    df = clean_df.copy()
    ref = state_ref_df.copy()

    # Standardize strings
    df["state"] = df["state"].astype(str).str.strip()
    ref["state_name"] = ref["state_name"].astype(str).str.strip()
    ref["abbreviation"] = ref["abbreviation"].astype(str).str.strip()

    # Merging by full state name
    enriched = df.merge(
        ref[["state_name", "abbreviation", "region", "area_sq_km"]],
        left_on="state",
        right_on="state_name",
        how="left"
    )

    # For rows that did not match by state_name I used a fallback merge on abbreviation
    missing_mask = enriched["region"].isna()

    if missing_mask.any():
        df_missing = enriched.loc[missing_mask].copy()

        # Merging using the abbreviation
        df_missing = df_missing.drop(columns=["state_name", "abbreviation", "region", "area_sq_km"], errors="ignore")

        df_missing = df_missing.merge(
            ref[["state_name", "abbreviation", "region", "area_sq_km"]],
            left_on="state",
            right_on="abbreviation",
            how="left"
        )

        # Putting results back into the main dataframe
        enriched.loc[missing_mask, "region"] = df_missing["region"].values
        enriched.loc[missing_mask, "area_sq_km"] = df_missing["area_sq_km"].values

    # Deleting extra columns
    enriched = enriched.drop(columns=["state_name", "abbreviation"], errors="ignore")

    return enriched


def calculate_analysis(enriched_df):
    # Observations per state and density per 1000 sq km
    state_summary = (
        enriched_df
        .groupby("state")
        .agg(
            observations=("species", "count"),
            area_sq_km=("area_sq_km", "first")
        )
        .reset_index()
    )

    state_summary["obs_per_1000_sq_km"] = state_summary["observations"] / (state_summary["area_sq_km"] / 1000)
    print(state_summary)

    # Created the bar chart
    month_species = (
        enriched_df
        .groupby(["month", "species"])
        .size()
        .reset_index(name="observations")
    )

    sns.barplot(
        data=month_species,
        x="month",
        y="observations",
        hue="species"
    )

    plt.title("Species observations each month")
    plt.xlabel("Month")
    plt.ylabel("Observations")
    plt.show()

    return state_summary