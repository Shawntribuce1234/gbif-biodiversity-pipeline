# GBIF Biodiversity Pipeline

A Python coursework project for retrieving species-occurrence records from GBIF, cleaning them with explicit retention metrics, enriching them with state information, and summarizing observations by state and month.

Created by **Shawn Tribuce** for **DS3500 — Homework 2**, the project demonstrates API requests, Pandas transformations, reference-data joins, exploratory visualization, and Pytest checks.

The repository contains reusable functions and three tests. It does not include a saved occurrence dataset, a state reference table, exported charts, or a complete command-line runner.

## Repository Structure

```text
gbif-biodiversity-pipeline/
├── README.md
├── hw2_ds3500.py
└── test_pipeline.py
```

The implementation retains its original filename so the supplied test imports continue to work. `pytest_hw2.py` is renamed to `test_pipeline.py` for standard Pytest discovery. Both files otherwise retain their original contents. Submission metadata is excluded.

## Workflow

### 1. Retrieve occurrence data

`fetch_gbif_data(species_list, year)` queries the GBIF occurrence-search endpoint for each requested scientific name. Requests include:

- The caller's species name and year.
- `hasCoordinate=true` and `country=US`.
- A fixed geographic rectangle spanning longitude −77.5 to −66.5 and latitude 38.8 to 47.5.
- A page limit of 300 and an offset that increases by 300.

The loop continues while fewer than 100 records have been collected for that species, but each response can contain up to 300 records. It does not trim the result to 100 or download every matching occurrence. This is a bounded retrieval workflow rather than an exhaustive census.

A non-200 response prints a message and stops retrieval for that species. An empty result page also stops its loop. There is no request timeout, retry policy, or local cache.

`convert_gbif_to_dataframe` selects six fields:

| Output field | Source or meaning |
|---|---|
| `species` | The scientific name supplied by the caller |
| `lat` | `decimalLatitude` |
| `lon` | `decimalLongitude` |
| `date` | `eventDate` |
| `state` | `stateProvince` |
| `coordinate_uncertainty_m` | `coordinateUncertaintyInMeters` |

The species label is copied from the requested name, not extracted from each returned occurrence. Occurrence identifiers, source datasets, and other provenance fields are not retained.

### 2. Clean records and report retention

`clean_biodiversity_data(raw_df)` works on a copy of the input and:

1. Drops rows missing any of the six required fields, including coordinate uncertainty.
2. Parses dates with `errors="coerce"` and removes invalid dates.
3. Removes duplicate combinations of species, latitude, longitude, and parsed date.
4. Adds a numeric `month` column.

It returns `(clean_df, metrics)`. Metrics include `raw_count`, `clean_count`, `percent_retained`, and `removed_by_reason`, with counts for missing required values, invalid dates, and duplicates. Removal counts reflect that sequential order.

The cleaner requires coordinate uncertainty to be present but does not apply an uncertainty threshold or check coordinate ranges.

### 3. Enrich with state information

`enrich_with_state_data(clean_df, state_ref_df)` expects a reference DataFrame with:

- `state_name`
- `abbreviation`
- `region`
- `area_sq_km`

It strips surrounding whitespace, left-joins on full state name, and attempts an abbreviation-based match for rows whose region is missing. The returned table includes `region` and `area_sq_km`, with temporary reference-name columns removed.

The reference table is not supplied. Matching is case-sensitive, unmatched states remain missing, and the original `state` value is retained. Full names and abbreviations can consequently form separate groups in later analysis. Reference keys should be unique; the code does not validate them before merging.

### 4. Summarize and visualize

`calculate_analysis(enriched_df)` groups records by the original state label and returns a summary containing:

- `observations`: retained records per state.
- `area_sq_km`: the first available area value within the group.
- `obs_per_1000_sq_km`: observation count divided by state area in thousands of square kilometers.

It prints this summary and displays a Seaborn grouped bar chart of record counts by month and species using Matplotlib. The chart and summary are not automatically saved.

This metric is a density of retrieved records relative to state area, not an estimate of species abundance. Retrieval limits, reporting effort, required-field exclusions, and the bounding rectangle all affect the counts. Dividing observations from a clipped geographic area by a whole state's area also limits comparisons.

## Setup

Use Python 3 and install the imported dependencies and test runner:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install requests pandas seaborn matplotlib pytest
```

On Windows, activate the environment with `.venv\Scripts\activate`.

The project has no pinned dependency versions. Live retrieval requires internet access, while the two synthetic-data tests can run offline.

## Using the Functions

From the repository root, this example uses the species and year already present in the supplied API test:

```python
from hw2_ds3500 import fetch_gbif_data, clean_biodiversity_data

raw = fetch_gbif_data(["Sturnus vulgaris"], 2023)

if raw.empty:
    print("No occurrence records were returned.")
else:
    cleaned, metrics = clean_biodiversity_data(raw)
    print(metrics)
    print(cleaned.head())
```

To continue to enrichment and plotting, supply a state reference DataFrame with the four columns described above, pass it with the cleaned data to `enrich_with_state_data`, and pass that result to `calculate_analysis`.

Running `python hw2_ds3500.py` alone does not execute the workflow: the file defines functions but has no main execution block.

## Tests

The three supplied tests check:

| Test | Scope |
|---|---|
| `test_fetch_returns_required_columns` | Live GBIF request for `Sturnus vulgaris` in 2023; checks expected columns. |
| `test_clean_outputs_month_and_metrics_valid` | Synthetic records; checks month range and basic retention-metric bounds. |
| `test_enrich_adds_region_and_area` | Synthetic Massachusetts record and reference row; checks enrichment columns and a non-null area. |

Run the offline checks:

```bash
python -m pytest test_pipeline.py -v -k "not fetch"
```

Run all three, including the live request:

```bash
python -m pytest test_pipeline.py -v
```

These checks do not establish complete API coverage, taxonomic accuracy, deduplication correctness, abbreviation-fallback behavior, or chart correctness. The live test checks column presence rather than the number or quality of returned records.

## Verification and Limitations

During repository preparation, the two offline tests were executed using the supplied implementation. The live GBIF test was not run, and no empirical biodiversity findings are claimed from the files provided.

Additional implementation limits include:

- An empty species list produces a DataFrame with the expected columns, but a nonempty species request with no returned records can produce an empty DataFrame without those columns. Passing that result directly to the cleaner can raise a missing-column error.
- The first records returned are used without random sampling or a configured sort, so the subset should not be treated as representative.
- Records with missing uncertainty values are discarded even if other fields are usable.
- State areas are not checked for missing, zero, or invalid values before division.
- The monthly chart shows observed groups; it does not explicitly fill absent species-month combinations with zeros.
- Fetching, enrichment, and plotting are not connected by a supplied end-to-end runner.

The repository is best understood as a coursework data-pipeline implementation with basic tests, rather than a completed ecological study.

## Author and Coursework

**Shawn Tribuce**  
**DS3500 — Homework 2**
