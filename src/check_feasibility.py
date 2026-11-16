"""Stage B and F check: bound the achievable range of each goal measure.

A goal target set outside the range any legal squad can reach makes that goal
either unsatisfiable or redundant, so each target must be placed inside the
range first. Solving for the extremes also confirms that the positional
constraints admit a feasible squad at all.

The structural constraints come from config.py, the same ones the goal
programme itself is built on.

Run from the project root:  python src\\check_feasibility.py
"""

import os
import sys

import pandas as pd
import pulp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402


def solve(players: pd.DataFrame, objective: str, sense: int, label: str):
    """The extreme of one measure, under the structural constraints alone."""
    prob = pulp.LpProblem("matchday_squad", sense)
    x = cfg.selection_vars(players)
    prob += pulp.lpSum(players.loc[i, objective] * x[i] for i in players.index)
    cfg.add_structure(prob, x, players)

    try:
        cfg.solve(prob, label)
    except cfg.SolverError as exc:
        print(f"{label:<24} {exc}")
        return None

    chosen = cfg.picked(players, x)
    print(f"{label:<24} {chosen[objective].sum():>12,.2f}")
    return chosen


def main() -> None:
    squad = cfg.selectable(pd.read_parquet(f"{cfg.PROCESSED}/squad_value.parquet"))
    print(cfg.solver_banner())
    print(f"selectable players: {len(squad)}")
    print()

    weakest = solve(squad, "value", pulp.LpMinimize, "weakest squad")
    strongest = solve(squad, "value", pulp.LpMaximize, "strongest squad")
    lightest = solve(squad, "workload", pulp.LpMinimize, "lightest workload")
    heaviest = solve(squad, "workload", pulp.LpMaximize, "heaviest workload")
    cheapest = solve(squad, "cost", pulp.LpMinimize, "cheapest squad")
    dearest = solve(squad, "cost", pulp.LpMaximize, "most expensive squad")

    extremes = {
        "performance": (weakest, strongest),
        "workload": (lightest, heaviest),
        "cost": (cheapest, dearest),
    }
    if any(e is None for pair in extremes.values() for e in pair):
        print()
        print("No legal squad exists for at least one measure. "
              "Check the positional counts before reading anything else.")
        return

    print()
    print("--- achievable ranges ---")
    print(f"performance  {weakest.value.sum():.2f} to {strongest.value.sum():.2f}")
    print(f"workload     {lightest.workload.sum():,.0f} to "
          f"{heaviest.workload.sum():,.0f} minutes")
    print(f"cost         GBP {cheapest.cost.sum():,.0f} to {dearest.cost.sum():,.0f}")
    print()
    print("--- the three targets currently set in config.py ---")
    for name, target in (
        ("performance", cfg.TARGET_PERFORMANCE),
        ("workload", cfg.TARGET_WORKLOAD),
        ("cost", cfg.TARGET_COST),
    ):
        column = cfg.GOAL_COLUMN[name]
        lo, hi = extremes[name]
        inside = lo[column].sum() <= target <= hi[column].sum()
        print(f"{name:<12} {target:>12,}   {'inside the range' if inside else 'OUT OF RANGE'}")
    print()
    print("--- what the strongest squad costs you ---")
    print(f"its workload  {strongest.workload.sum():,.0f} minutes")
    print(f"its cost      GBP {strongest.cost.sum():,.0f}")


if __name__ == "__main__":
    main()
