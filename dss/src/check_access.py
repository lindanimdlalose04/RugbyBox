"""Confirms which URL form the rugbydata parquet store answers.
Evidence for the solution-process section of the report."""

import pandas as pd

PATHS = {
    "package URL form (github.com blob)":
        "https://github.com/seanyboi/rugbydata/blob/main/data/v3/team/team_registry.parquet?raw=true",
    "direct store (raw.githubusercontent.com)":
        "https://raw.githubusercontent.com/seanyboi/rugbydata/main/data/v3/team/team_registry.parquet",
}

for label, url in PATHS.items():
    try:
        df = pd.read_parquet(url, engine="pyarrow")
        print(f"OK    {label}: {df.shape[0]} rows")
    except Exception as exc:
        print(f"FAIL  {label}: {type(exc).__name__}: {str(exc)[:80]}")
        