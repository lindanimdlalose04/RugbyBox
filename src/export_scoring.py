"""Export the figures the Excel scoring sheet needs.

Writes each squad player's season totals, and the best total achieved in each
position across the competition, which the sheet divides by.

Run from the project root:  python src\\export_scoring.py
"""

import pandas as pd

PROCESSED = "data/processed"
MEASURES = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]


def main() -> None:
    league = pd.read_parquet(f"{PROCESSED}/players_season.parquet")
    for c in MEASURES:
        league[c] = league[c].fillna(0)

    squad = league[league.in_squad & league.role.notna()]
    squad[["name", "role"] + MEASURES].to_csv(
        f"{PROCESSED}/scoring_players.csv", index=False
    )

    best = league[league.frontier].groupby("role")[MEASURES].max().reset_index()
    best.to_csv(f"{PROCESSED}/scoring_bests.csv", index=False)

    print(f"players written: {len(squad)}")
    print(f"positions written: {len(best)}")
    print()
    print("best in each position across the league:")
    print(best.round(0).to_string(index=False))


if __name__ == "__main__":
    main()