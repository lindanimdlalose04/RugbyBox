"""Find the performance level at which the three goals start to conflict.

Maximises squad performance while holding the workload and budget targets as
hard limits. The answer is the best performance obtainable without breaking
either promise, so a performance target above it cannot be met without
sacrificing one of the other two.

The unconstrained best is solved for as well, rather than quoted, so the two
figures always describe the same player pool.

Run from the project root:  python src\\check_conflict.py
"""

import os
import sys

import pandas as pd
import pulp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402


def best_performance(players, hold_promises: bool):
    """Strongest legal squad, optionally also inside the workload and budget."""
    prob = pulp.LpProblem("breaking_point", pulp.LpMaximize)
    x = cfg.selection_vars(players)
    prob += pulp.lpSum(players.loc[i, "value"] * x[i] for i in players.index)
    cfg.add_structure(prob, x, players)

    if hold_promises:
        prob += pulp.lpSum(
            players.loc[i, "workload"] * x[i] for i in players.index
        ) <= cfg.TARGET_WORKLOAD, "hold_workload"
        prob += pulp.lpSum(
            players.loc[i, "cost"] * x[i] for i in players.index
        ) <= cfg.TARGET_COST, "hold_cost"

    cfg.solve(prob, "constrained best" if hold_promises else "unconstrained best")
    return cfg.picked(players, x)


def main() -> None:
    players = cfg.selectable(pd.read_parquet(f"{cfg.PROCESSED}/squad_value.parquet"))
    print(cfg.solver_banner())
    print()

    held = best_performance(players, hold_promises=True)
    free = best_performance(players, hold_promises=False)

    print(f"best performance without breaking either promise: {held.value.sum():.2f}")
    print(f"  that squad's workload  {held.workload.sum():,.0f} "
          f"of {cfg.TARGET_WORKLOAD:,}")
    print(f"  that squad's cost      GBP {held.cost.sum():,.0f} "
          f"of {cfg.TARGET_COST:,}")
    print()
    print(f"best performance ignoring both promises: {free.value.sum():.2f}")
    print(f"  that squad's workload  {free.workload.sum():,.0f} "
          f"of {cfg.TARGET_WORKLOAD:,}")
    print(f"  that squad's cost      GBP {free.cost.sum():,.0f} "
          f"of {cfg.TARGET_COST:,}")
    print()
    print("Set the performance target above the first number and below the")
    print("second, and the three goals cannot all be satisfied at once.")
    print(f"config.py currently sets it to {cfg.TARGET_PERFORMANCE}, which is "
          f"{'inside' if held.value.sum() < cfg.TARGET_PERFORMANCE <= free.value.sum() else 'OUTSIDE'}"
          " that band.")


if __name__ == "__main__":
    main()
