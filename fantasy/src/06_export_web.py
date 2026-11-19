"""Stage F: write what the interface needs.

The page has no server behind it, so every answer it can give is solved here
and shipped with it. The budget is swept and the optimal squad recorded at
each level, which is what lets the slider move without anything recomputing:
the page is choosing between real solutions rather than interpolating.

Written as `web/data.js` rather than a JSON file, because a page opened
straight off disk can load a script but cannot fetch a file beside it.

Run from the project root, after stage 04:  python src\\06_export_web.py
"""

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from rules import DEFAULT  # noqa: E402

WEB = "web"

# Budgets solved for, as a share of the one the rules set. The range runs
# from a squad that can barely be fielded to one that can buy anything.
BUDGET_STEPS = [round(0.6 + 0.05 * n, 2) for n in range(21)]

POSITION_ORDER = [
    "prop", "hooker", "lock", "loose_forward",
    "scrum_half", "fly_half", "centre", "back_three",
]

POSITION_LABELS = {
    "prop": "Prop",
    "hooker": "Hooker",
    "lock": "Lock",
    "loose_forward": "Loose forward",
    "scrum_half": "Scrum half",
    "fly_half": "Fly half",
    "centre": "Centre",
    "back_three": "Back three",
}

# Stated on the page itself, not buried. A squad list looks equally
# authoritative whether or not its prices are real, so the page has to say
# what this is. See docs/decisions/0002 and 0004.
CAVEATS = [
    "This uses its own scoring system, not any published fantasy game's. "
    "The squads are a demonstration of the method and are not advice for a "
    "real competition.",
    "Prices are modelled from projected points, because a scoring system of "
    "this project's own has no published price list.",
    "Two source columns, line breaks and turnovers won, hold copies of other "
    "columns and are not scored. The breakdown is therefore invisible: a "
    "jackaling openside earns nothing for it.",
    "Fixture difficulty is not modelled. The same player is worth more "
    "against a weak defence, and that is not accounted for here.",
]


def load_optimiser():
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location(
        "optimise", f"{here}/05_optimise.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_clubs(appearances: pd.DataFrame) -> dict:
    """One name per club.

    The source labels the same club several ways across a season, "Bath" and
    "Bath Rugby", and one club was renamed part way through. The most recent
    label is taken as the club's name, and a short form made for the pitch.
    """
    latest = appearances.sort_values("match_date").groupby("team_id").team.last()
    clubs = {}
    for team_id, name in latest.items():
        short = name.split()[0]
        clubs[team_id] = {
            "id": team_id,
            "name": name,
            "short": "Harlequins" if short == "Harlequin" else short,
        }
    return clubs


def star_rating(players: pd.DataFrame) -> pd.Series:
    """One to five stars, by where a player sits within his own position.

    The front of the interface shows form as stars rather than as a number,
    so that picking a team reads as a game and not as a spreadsheet. Ranking
    within position keeps a good prop a five-star prop, even though props
    score fewer points than fly halves.
    """
    rank = players.groupby("role").projected_points.rank(pct=True)
    return (rank * 5).clip(upper=4.999).astype(int) + 1


def player_record(row, rules) -> dict:
    return {
        "id": row.player_id,
        "name": row["name"],
        "role": row.role,
        "team": row.team,
        "team_id": row.team_id,
        "stars": int(row.stars),
        "appearances": int(row.appearances),
        "price": round(float(row.price), 2),
        "projected": round(float(row.projected_points), 2),
        "per_appearance": round(float(row.points_per_appearance), 2),
        "availability": round(float(row.availability), 3),
        "value": round(float(row.projected_points / row.price), 2),
        "captain": bool(row.captain),
    }


def main() -> None:
    os.makedirs(WEB, exist_ok=True)
    opt = load_optimiser()
    rules = DEFAULT

    players = pd.read_parquet(f"{cfg.PROCESSED}/priced.parquet")
    appearances = pd.read_parquet(f"{cfg.PROCESSED}/appearances.parquet")

    clubs = canonical_clubs(appearances)
    players["team"] = players.team_id.map(lambda t: clubs[t]["name"])
    players["stars"] = star_rating(players)
    players["captain"] = False

    manifest_path = cfg.MANIFEST
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}

    print(f"solving {len(BUDGET_STEPS)} budgets from "
          f"{rules.budget * BUDGET_STEPS[0]:.0f} to "
          f"{rules.budget * BUDGET_STEPS[-1]:.0f}")

    scenarios = []
    for share in BUDGET_STEPS:
        budget = round(rules.budget * share, 2)
        try:
            squad, _ = opt.pick(players, rules, budget=budget)
        except opt.NoSquad:
            print(f"  {budget:>6.0f}  no legal squad")
            continue
        scenarios.append({
            "budget": budget,
            "points": round(opt.expected(squad, rules), 1),
            "cost": round(float(squad.price.sum()), 2),
            "squad": [player_record(r, rules) for _, r in squad.iterrows()],
        })
        print(f"  {budget:>6.0f}  {scenarios[-1]['points']:>7.1f} points, "
              f"costing {scenarios[-1]['cost']:.1f}")

    if not scenarios:
        raise SystemExit("no budget produced a legal squad; nothing to export")

    # The squad with no budget at all, so the page can show what the
    # constraint costs rather than only what it produces.
    unlimited, _ = opt.pick(players, rules, budget=None)

    payload = {
        "meta": {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "data_as_of": manifest.get("data_as_of", "unknown"),
            "competition": manifest.get("competition", cfg.COMPETITION),
            "season": f"{cfg.SEASON_START[:4]}-{cfg.SEASON_END[2:4]}",
            "rules_name": rules.name,
            "players_considered": int(len(players)),
            "fixtures": int(appearances.match_id.nunique()),
            "appearances": int(len(appearances)),
        },
        # The pool the front of the interface picks from, best first.
        "players": [
            player_record(r, rules)
            for _, r in players.sort_values(
                "projected_points", ascending=False
            ).iterrows()
        ],
        "clubs": sorted(clubs.values(), key=lambda c: c["name"]),
        "rules": {
            "squad_size": rules.squad_size,
            "budget": rules.budget,
            "club_cap": rules.club_cap,
            "captain_multiplier": rules.captain_multiplier,
            "quota": {POSITION_LABELS[k]: v for k, v in rules.quota.items()},
            "points": {k: v for k, v in sorted(
                rules.points.items(), key=lambda kv: -abs(kv[1])
            )},
            "appearance_points": rules.appearance_points,
        },
        "positions": [
            {"key": k, "label": POSITION_LABELS[k], "quota": rules.quota[k]}
            for k in POSITION_ORDER
        ],
        "default_budget": rules.budget,
        "scenarios": scenarios,
        "unlimited": {
            "points": round(opt.expected(unlimited, rules), 1),
            "cost": round(float(unlimited.price.sum()), 2),
        },
        "caveats": CAVEATS,
    }

    body = json.dumps(payload, indent=1)
    with open(f"{WEB}/data.js", "w", encoding="utf-8") as handle:
        handle.write("// Written by src/06_export_web.py. Do not edit.\n")
        handle.write(f"window.FRB_DATA = {body};\n")

    size = os.path.getsize(f"{WEB}/data.js") / 1024
    print()
    print("--- checkpoint ---")
    print(f"scenarios written:   {len(scenarios)}")
    print(f"budget range:        {scenarios[0]['budget']:.0f} "
          f"to {scenarios[-1]['budget']:.0f}")
    print(f"points range:        {scenarios[0]['points']:.1f} "
          f"to {scenarios[-1]['points']:.1f}")
    print(f"unconstrained:       {payload['unlimited']['points']:.1f} points "
          f"costing {payload['unlimited']['cost']:.1f}")
    print(f"data as of:          {payload['meta']['data_as_of']}")
    print(f"written to {WEB}/data.js ({size:.0f} KB)")


if __name__ == "__main__":
    main()
