"""Export one position's peer group for the Excel efficiency demonstration.

Efficiency is measured against every player in the same position across the
competition, so the Excel sheet needs that peer group's minutes and
contribution totals, along with the player being evaluated.

Run from the project root:  python src\\export_dea.py
"""

import pandas as pd

PROCESSED = "data/processed"
ROLE = "hooker"
PLAYER = "Dan Frost"
OUTPUTS = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]


def main() -> None:
    league = pd.read_parquet(f"{PROCESSED}/players_season.parquet")
    for c in OUTPUTS:
        league[c] = league[c].fillna(0)

    peers = league[
        (league.role == ROLE) & league.frontier & (league.minutes > 0)
    ].copy()

    target = league[league.name.str.lower() == PLAYER.lower()]
    if target.empty:
        print(f"{PLAYER} not found")
        return
    target_minutes = float(target.minutes.iloc[0])

    peers["ratio"] = peers.minutes / target_minutes
    out = peers[["name", "minutes"] + OUTPUTS + ["ratio"]].sort_values("name")
    out.to_csv(f"{PROCESSED}/dea_peers.csv", index=False)

    print(f"peer group: {len(out)} {ROLE}s")
    print(f"{PLAYER} minutes: {target_minutes:.2f}")
    print()
    print("the player being evaluated:")
    print(target[["name", "minutes"] + OUTPUTS].round(1).to_string(index=False))


if __name__ == "__main__":
    main()