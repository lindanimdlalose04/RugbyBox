"""Stage A: build the league-wide comparison set for the efficiency analysis.

A club squad holds too few players in any one position to support a
discriminating efficiency comparison, so each player is benchmarked against
every player in that position across the competition. The ten competing clubs
are derived from the club's own fixture list rather than hardcoded.

Individual player files are cached, so a re-run only fetches what is missing.

Run from the project root:  python src\\02_fetch_league.py
"""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from rb import get  # noqa: E402

CLUB_ID = cfg.CLUB_ID
SEASON_START = cfg.SEASON_START
SEASON_END = cfg.SEASON_END
RAW = cfg.RAW
CACHE = cfg.PLAYER_CACHE


def cached_player(pid: str) -> pd.DataFrame:
    """Fetch one player's match records, reading from local cache if present."""
    path = f"{CACHE}/{pid}.parquet"
    if os.path.exists(path):
        return pd.read_parquet(path)
    df = get("player", pid)
    df.to_parquet(path)
    return df


def main() -> None:
    os.makedirs(CACHE, exist_ok=True)

    club = pd.read_parquet(f"{RAW}/club_team.parquet")
    pool = pd.read_parquet(f"{RAW}/pool_players_raw.parquet")
    window_ids = set(json.load(open(f"{RAW}/window_match_ids.json")))

    # Fixtures in the window that were league fixtures, taken from the
    # competition recorded against the player rows.
    league_ids = set(
        pool[
            (pool.competition == "Gallagher Premiership")
            & (pool.match_id.isin(window_ids))
        ].match_id.unique()
    )
    print(f"league fixtures in window: {len(league_ids)}")

    # Every club met in those fixtures, plus the club itself.
    opponents = club[club.match_id.isin(league_ids)].team_vs_id.dropna().unique()
    clubs = sorted({CLUB_ID, *opponents})
    print(f"clubs in comparison set:   {len(clubs)}")

    # Union of every player who featured for any of those clubs in the window.
    league_pool = set()
    for cid in clubs:
        try:
            t = get("team", cid)
        except Exception as exc:
            print(f"  WARN could not read club {cid}: {type(exc).__name__}")
            continue
        t["match_date"] = pd.to_datetime(t.game_date, format="%Y%m%d")
        w = t[(t.match_date >= SEASON_START) & (t.match_date <= SEASON_END)]
        before = len(league_pool)
        for sheet in w["players"]:
            league_pool.update(list(sheet))
        print(f"  {cid}: {len(w):>2} fixtures, +{len(league_pool) - before} new players")

    league_pool = sorted(league_pool)
    print(f"total players to fetch:    {len(league_pool)}")

    frames, failed = [], []
    for n, pid in enumerate(league_pool, 1):
        try:
            frames.append(cached_player(pid))
        except Exception as exc:
            failed.append((pid, type(exc).__name__))
        if n % 50 == 0:
            print(f"  {n}/{len(league_pool)}")

    league = pd.concat(frames, ignore_index=True)
    league.to_parquet(f"{RAW}/league_players_raw.parquet")
    json.dump(clubs, open(f"{RAW}/league_club_ids.json", "w"))

    print()
    print("--- checkpoint ---")
    print(f"players fetched:  {len(frames)}, failed {len(failed)}")

    league["match_date"] = pd.to_datetime(league.game_date, format="%Y%m%d")
    prem = league[
        (league.competition == "Gallagher Premiership")
        & (league.match_date >= SEASON_START)
        & (league.match_date <= SEASON_END)
    ]
    print(f"league rows in window:     {len(prem)}")
    print(f"distinct players:          {prem.player_id.nunique()}")
    print(f"distinct clubs:            {prem.team_id.nunique()}")
    print(f"distinct fixtures:         {prem.match_id.nunique()}")
    if failed:
        print(f"failures: {failed[:10]}")

if __name__ == "__main__":
    main()