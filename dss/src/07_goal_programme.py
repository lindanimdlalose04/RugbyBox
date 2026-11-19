"""Stage G: select the matchday 23 by goal programming.

Three goals, each with a target. Only the unwanted miss on each is penalised:
falling short on performance, and going over on workload and on cost. Because
the three are measured in different units, each miss is expressed as a
fraction of its own target before the weights are applied.

Solved twice. The weighted form trades the three off using the weights from
stage D. The pre-emptive form satisfies them in strict priority order,
settling the first as far as possible before considering the second.

The squad structure and the three targets come from config.py, so this stage
and the two diagnostics cannot drift apart.

Run from the project root:  python src\\07_goal_programme.py
"""

import json
import os
import sys

import pandas as pd
import pulp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402

PRIORITY_ORDER = ["performance", "workload", "cost"]


def goals(prob, x, players):
    """The three goal constraints and their deviation variables."""
    d = {
        name: {
            "under": pulp.LpVariable(f"d_{name}_under", lowBound=0),
            "over": pulp.LpVariable(f"d_{name}_over", lowBound=0),
        }
        for name in cfg.GOAL_NAMES
    }

    for name in cfg.GOAL_NAMES:
        column = cfg.GOAL_COLUMN[name]
        _, target = cfg.UNWANTED[name]
        prob += (
            pulp.lpSum(players.loc[i, column] * x[i] for i in players.index)
            + d[name]["under"] - d[name]["over"] == target,
            f"goal_{name}",
        )
    return d


def report(label, players, x, d):
    chosen = cfg.picked(players, x)
    tp, tw, tc = cfg.TARGET_PERFORMANCE, cfg.TARGET_WORKLOAD, cfg.TARGET_COST
    print(f"=== {label} ===")
    print(f"performance  {chosen.value.sum():>10.2f}   target {tp:>10.2f}"
          f"   short by {d['performance']['under'].value():.2f}")
    print(f"workload     {chosen.workload.sum():>10,.0f}   target {tw:>10,}"
          f"   over by  {d['workload']['over'].value():,.0f}")
    print(f"cost         {chosen.cost.sum():>10,.0f}   target {tc:>10,}"
          f"   over by  {d['cost']['over'].value():,.0f}")
    print(f"forwards {chosen.role.isin(cfg.FORWARD_ROLES).sum()}, backs "
          f"{(~chosen.role.isin(cfg.FORWARD_ROLES)).sum()}")
    print()
    print(chosen.sort_values(["role", "value"], ascending=[True, False])[
        ["name", "role", "appearances", "value", "workload", "cost"]
    ].round(2).to_string(index=False))
    print()
    return chosen


def solve_weighted(players, w):
    prob = pulp.LpProblem("weighted", pulp.LpMinimize)
    x = cfg.selection_vars(players)
    cfg.add_structure(prob, x, players)
    d = goals(prob, x, players)

    prob += pulp.lpSum(
        w[name] * d[name][side] / target
        for name, (side, target) in cfg.UNWANTED.items()
    )
    cfg.solve(prob, "weighted goal programme")
    return report("weighted", players, x, d), prob.objective.value()


def solve_preemptive(players, order):
    """Settle each goal in turn, holding the earlier ones at their best."""
    achieved = {}
    x = d = None

    for level, name in enumerate(order, 1):
        prob = pulp.LpProblem(f"priority_{level}", pulp.LpMinimize)
        x = cfg.selection_vars(players)
        cfg.add_structure(prob, x, players)
        d = goals(prob, x, players)

        side, target = cfg.UNWANTED[name]
        prob += (1 / target) * d[name][side]

        # Earlier priorities may not be worsened.
        for done, best in achieved.items():
            s, t = cfg.UNWANTED[done]
            prob += (1 / t) * d[done][s] <= best + 1e-6, f"hold_{done}"

        cfg.solve(prob, f"pre-emptive priority {level} ({name})")
        achieved[name] = d[name][side].value() / target
        print(f"priority {level}: {name}, miss {achieved[name] * 100:.2f}%")

    print()
    # The final level still holds every earlier priority, so its solution is
    # the pre-emptive answer. Returned explicitly rather than left to whatever
    # the loop happened to bind last.
    return report("pre-emptive", players, x, d)


def main() -> None:
    players = cfg.selectable(pd.read_parquet(f"{cfg.PROCESSED}/squad_value.parquet"))
    w = json.load(open(f"{cfg.PROCESSED}/weights.json"))["goals"]

    print(cfg.solver_banner())
    print(f"weights: performance {w['performance']:.3f}, "
          f"workload {w['workload']:.3f}, cost {w['cost']:.3f}")
    print()

    weighted, obj = solve_weighted(players, w)
    print(f"weighted objective value: {obj:.4f}")
    print()

    preemptive = solve_preemptive(players, PRIORITY_ORDER)

    same = set(weighted.player_id) & set(preemptive.player_id)
    print(f"the two squads share {len(same)} of {cfg.SQUAD_SIZE} players")
    print(f"only in weighted:    {sorted(set(weighted.name) - set(preemptive.name))}")
    print(f"only in pre-emptive: {sorted(set(preemptive.name) - set(weighted.name))}")

    weighted.to_csv(f"{cfg.PROCESSED}/squad_weighted.csv", index=False)
    preemptive.to_csv(f"{cfg.PROCESSED}/squad_preemptive.csv", index=False)


if __name__ == "__main__":
    main()
