"""Stage B: build the modelling table from the raw match records.

Produces one row per player with season totals (inputs and outputs for the
efficiency analysis), per-80-minute rates (inputs to the scoring model), recent
workload, per-match cost, and the positional classification used by the
selection constraints.

Run from the project root:  python src\\03_clean.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402

RAW = cfg.RAW
OUT = cfg.PROCESSED
CLUB_ID = cfg.CLUB_ID
COMPETITION = cfg.COMPETITION
SEASON_START = cfg.SEASON_START
SEASON_END = cfg.SEASON_END

# Appearances required before a player may define the efficiency frontier.
FRONTIER_MIN_APPS = cfg.FRONTIER_MIN_APPS

# Recent fixtures counted towards accumulated workload.
WORKLOAD_FIXTURES = cfg.WORKLOAD_FIXTURES

# Average annual salary by position, Premiership Rugby salary cap report,
# 2022/23 season. The most recent published per-position breakdown; applied to
# the 2025-26 squad as a proxy, which is stated as a limitation. Back three
# blends the published wing and full-back figures in the 2:1 ratio a matchday
# back three is made up of.
SALARY = {
    "fly_half": 217_761,
    "centre": 178_755,
    "lock": 174_785,
    "loose_forward": 159_467,
    "prop": 143_187,
    "hooker": 128_556,
    "scrum_half": 121_104,
    "back_three": round((2 * 127_969 + 169_918) / 3),
}

# Individual cost is not published. It is modelled as the position average
# scaled by the player's share of playing time within their role at the club,
# on the assumption that regular starters are the more senior and more highly
# paid squad members. The scaling is mean-preserving, so each role's squad
# average still reproduces the published figure. COST_DISPERSION controls how
# far individual cost departs from that average and is a stated assumption
# tested by sensitivity analysis: 0 gives a flat position average, 1 scales
# cost in direct proportion to minutes played.
COST_DISPERSION = cfg.COST_DISPERSION

# Raw position labels to the eight roles used as efficiency peer groups.
ROLE_MAP = {
    "hooker": "hooker",
    "prop": "prop",
    "loosehead_prop": "prop",
    "tighthead_prop": "prop",
    "lock": "lock",
    "flanker": "loose_forward",
    "openside_flanker": "loose_forward",
    "blindside_flanker": "loose_forward",
    "number_eight": "loose_forward",
    "scrum_half": "scrum_half",
    "fly_half": "fly_half",
    "centre": "centre",
    "inside_centre": "centre",
    "outside_centre": "centre",
    "wing": "back_three",
    "left_wing": "back_three",
    "right_wing": "back_three",
    "fullback": "back_three",
}

# Roles to the positional units the squad constraints are written over.
UNIT_MAP = {
    "hooker": "front_row",
    "prop": "front_row",
    "lock": "second_row",
    "loose_forward": "loose_forwards",
    "scrum_half": "scrum_half",
    "fly_half": "fly_half",
    "centre": "centres",
    "back_three": "back_three",
}

FORWARD_UNITS = {"front_row", "second_row", "loose_forwards"}

# Opportunity consumed. Minutes alone: carries is work already performed and
# belongs on the output side of the relationship, not the input side.
INPUTS = ["minutes"]

# Contribution produced. Offloads are excluded: they are recorded sparsely,
# are zero for most forwards, and a near-zero output weakens the analysis.
OUTPUTS = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]

# Summed and rated but not used in the model, kept for reference.
EXTRA = ["carries", "offloads"]


def reconstruct_minutes(df: pd.DataFrame) -> pd.Series:
    """Minutes played, falling back to carries divided by the carrying rate.

    The source records minutes for roughly half of all appearances but also
    carries a per-minute carrying rate, from which minutes can be recovered.
    Validated against the subset where both are present: mean absolute
    error 2.5 minutes.
    """
    direct = pd.to_numeric(df.get("minutes_played"), errors="coerce")
    rate = pd.to_numeric(df.get("carries_per_minute"), errors="coerce")
    carries = pd.to_numeric(df.get("carries"), errors="coerce")

    derived = np.where((rate > 0) & carries.notna(), carries / rate, np.nan)
    minutes = direct.fillna(pd.Series(derived, index=df.index))
    return minutes.clip(upper=80)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)

    league = pd.read_parquet(f"{RAW}/league_players_raw.parquet")
    league["match_date"] = pd.to_datetime(league.game_date, format="%Y%m%d")
    in_window = (league.match_date >= SEASON_START) & (league.match_date <= SEASON_END)

    # Workload is physical, so every fixture in the window counts towards it,
    # not only league fixtures.
    all_comps = league[in_window].copy()
    all_comps["minutes"] = reconstruct_minutes(all_comps)

    # Performance is measured within one competition so that players are
    # compared against a consistent standard of opposition.
    season = all_comps[all_comps.competition == COMPETITION].copy()
    print(f"league rows in window:     {len(all_comps)}")
    print(f"  of which {COMPETITION}: {len(season)}")

    # --- positional classification ---------------------------------------
    BENCH = {"front_row_sub", "back_sub", "forward_sub", "default", ""}
    specialist = season[~season.position.isin(BENCH)].dropna(subset=["position"])
    modal = specialist.groupby("player_id")["position"].agg(lambda s: s.mode().iloc[0])
    role = modal.map(ROLE_MAP)

    unmapped = modal[role.isna()]
    if len(unmapped):
        print(f"  WARN unmapped position labels: {sorted(set(unmapped))}")

    # --- season aggregates ------------------------------------------------
    stat_cols = EXTRA + OUTPUTS
    for c in stat_cols:
        season[c] = pd.to_numeric(season[c], errors="coerce")

    # One row per appearance, kept so later stages can judge how much evidence
    # a player's season rate actually rests on. Season totals alone cannot
    # distinguish a steady rate from one good afternoon.
    season[["player_id", "match_id", "minutes", *stat_cols]].to_parquet(
        f"{OUT}/player_appearances.parquet", index=False
    )

    agg = season.groupby("player_id").agg(
        name=("name", "first"),
        team_id=("team_id", "first"),
        appearances=("match_id", "nunique"),
        minutes=("minutes", "sum"),
        **{c: (c, "sum") for c in stat_cols},
    )

    # --- per-80-minute rates ----------------------------------------------
    for c in OUTPUTS + EXTRA:
        agg[f"p80_{c}"] = np.where(agg.minutes > 0, agg[c] / agg.minutes * 80, np.nan)

    # --- recent workload ---------------------------------------------------
    recent = (
        all_comps.sort_values("match_date")
        .groupby("player_id")
        .tail(WORKLOAD_FIXTURES)
        .groupby("player_id")["minutes"]
        .sum()
    )
    agg["workload"] = recent

    # --- assemble -----------------------------------------------------------
    agg["role"] = role
    agg["unit"] = agg.role.map(UNIT_MAP)
    agg["is_forward"] = agg.unit.isin(FORWARD_UNITS)
    agg["in_squad"] = agg.team_id == CLUB_ID
    agg["frontier"] = agg.appearances >= FRONTIER_MIN_APPS

    # Salaries are annual and the decision is a single fixture, so cost is
    # expressed per match over the club's own fixture count.
    club_fixtures = all_comps[all_comps.team_id == CLUB_ID].match_id.nunique()

    # Share of the role's total minutes at the club, scaled so the mean within
    # each role is exactly 1 and the published position average is preserved.
    # The multiplier is 1 + COST_DISPERSION * (raw - 1) with raw never
    # negative, so it cannot fall below 1 - COST_DISPERSION and needs no floor.
    club = agg[agg.in_squad]
    role_mean_minutes = club.groupby("role").minutes.transform("mean")
    raw = club.minutes / role_mean_minutes
    multiplier = 1 + COST_DISPERSION * (raw - 1)

    # Cost is modelled only for the club's own players. A per-match figure for
    # a league player, derived from this club's fixture count, would mean
    # nothing, and nothing downstream selects from outside the squad.
    agg["cost"] = np.nan
    agg.loc[club.index, "cost"] = (
        club.role.map(SALARY) / club_fixtures * multiplier
    )

    agg = agg.reset_index()
    agg.to_parquet(f"{OUT}/players_season.parquet")
    agg[agg.in_squad].to_csv(f"{OUT}/squad_season.csv", index=False)

    # --- checkpoint ----------------------------------------------------------
    squad = agg[agg.in_squad]
    print()
    print("--- checkpoint ---")
    print(f"league players:            {len(agg)}")
    print(f"  with a role assigned:    {agg.role.notna().sum()}")
    print(f"  eligible for frontier:   {agg.frontier.sum()}")
    print(f"squad players:             {len(squad)}")
    print(f"  with a role assigned:    {squad.role.notna().sum()}")
    print(f"  minutes missing:         {squad.minutes.isna().sum()}")
    print()
    print("squad by unit:")
    print(squad.unit.value_counts().to_string())
    print()
    print("squad by role:")
    print(squad.role.value_counts().to_string())
    print()
    print("frontier peer group sizes (league, role):")
    print(agg[agg.frontier].role.value_counts().to_string())

    priced = squad.dropna(subset=["cost"])
    print()
    print(f"club fixtures in season:   {club_fixtures}")
    print(f"squad players priced:      {len(priced)}")
    print(f"per-match cost range:      "
          f"£{priced.cost.min():,.0f} to £{priced.cost.max():,.0f}")
    print(f"cheapest 23 (unconstrained):  £{priced.nsmallest(23, 'cost').cost.sum():,.0f}")
    print(f"most expensive 23:            £{priced.nlargest(23, 'cost').cost.sum():,.0f}")
    print()
    print("most expensive players:")
    print(priced.nlargest(6, "cost")[["name", "role", "appearances", "cost"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()