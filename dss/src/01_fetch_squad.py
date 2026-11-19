"""Stage A: build Bath's available player pool for the 2025-26 season.

The club's team file records one row per fixture, including a `players` column
listing every player on that team sheet. The union of those lists across the
season is the pool the selection is actually drawn from.

Run from the project root:  python src\\01_fetch_squad.py
"""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from rugbystore import get  # noqa: E402

TEAM_ID = cfg.CLUB_ID
SEASON_START = cfg.SEASON_START
SEASON_END = cfg.SEASON_END
RAW = cfg.RAW


def main() -> None:
    os.makedirs(RAW, exist_ok=True)

    print("fetching club team sheets...")
    team = get("team", TEAM_ID)
    team["match_date"] = pd.to_datetime(team.game_date, format="%Y%m%d")

    window = team[
        (team.match_date >= SEASON_START) & (team.match_date <= SEASON_END)
    ].sort_values("match_date")
    print(f"  fixtures in season window: {len(window)}")

    pool = set()
    for sheet in window["players"]:
        pool.update(list(sheet))
    pool = sorted(pool)
    print(f"  unique players featured:   {len(pool)}")

    print("fetching player match records...")
    frames, failed = [], []
    for n, pid in enumerate(pool, 1):
        try:
            frames.append(get("player", pid))
        except Exception as exc:
            failed.append((pid, type(exc).__name__))
        if n % 10 == 0:
            print(f"  {n}/{len(pool)}")

    players = pd.concat(frames, ignore_index=True)
    print(f"  fetched {len(frames)}, failed {len(failed)}, rows {players.shape}")
    if failed:
        print(f"  failures: {failed}")

    team.drop(columns="match_date").to_parquet(f"{RAW}/club_team.parquet")
    players.to_parquet(f"{RAW}/pool_players_raw.parquet")
    json.dump(pool, open(f"{RAW}/pool_ids.json", "w"))
    json.dump(list(window.match_id), open(f"{RAW}/window_match_ids.json", "w"))

    print()
    print("--- checkpoint ---")
    prem = players[players.competition == "Gallagher Premiership"]
    in_window = prem[prem.match_id.isin(set(window.match_id))]
    print(f"Premiership rows in window: {len(in_window)}")
    print(f"distinct players:           {in_window.player_id.nunique()}")
    print(f"distinct fixtures:          {in_window.match_id.nunique()}")


if __name__ == "__main__":
    main()