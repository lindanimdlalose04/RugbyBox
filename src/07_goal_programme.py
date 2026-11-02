"""Stage G: select the matchday 23 by goal programming.

Three goals, each with a target. Only the unwanted miss on each is penalised:
falling short on performance, and going over on workload and on cost. Because
the three are measured in different units, each miss is expressed as a
fraction of its own target before the weights are applied.

Solved twice. The weighted form trades the three off using the weights from
stage D. The pre-emptive form satisfies them in strict priority order,
settling the first as far as possible before considering the second.

Run from the project root:  python src\\07_goal_programme.py
"""

import json

import pandas as pd
import pulp

PROCESSED = "data/processed"

TARGET_PERFORMANCE = 11.1
TARGET_WORKLOAD = 2875
TARGET_COST = 130_000

SQUAD_SIZE = 23
FORWARDS_MIN, FORWARDS_MAX = 13, 14
FRONT_ROW_MIN = 5
ROLE_MIN = {
    "hooker": 2, "prop": 3, "lock": 3, "loose_forward": 4,
    "scrum_half": 2, "fly_half": 2, "centre": 2, "back_three": 3,
}
FORWARD_ROLES = {"hooker", "prop", "lock", "loose_forward"}


def structure(prob, x, players):
    """The constraints that cannot be broken, whatever the goals say."""
    prob += pulp.lpSum(x.values()) == SQUAD_SIZE, "squad_size"

    forwards = pulp.lpSum(
        x[i] for i in players.index if players.loc[i, "role"] in FORWARD_ROLES
    )
    prob += forwards >= FORWARDS_MIN, "forwards_min"
    prob += forwards <= FORWARDS_MAX, "forwards_max"

    prob += pulp.lpSum(
        x[i] for i in players.index if players.loc[i, "role"] in {"hooker", "prop"}
    ) >= FRONT_ROW_MIN, "front_row_cover"

    for role, lo in ROLE_MIN.items():
        members = [i for i in players.index if players.loc[i, "role"] == role]
        prob += pulp.lpSum(x[i] for i in members) >= lo, f"min_{role}"


def goals(prob, x, players):
    """The three goal constraints and their deviation variables."""
    d = {
        name: {
            "under": pulp.LpVariable(f"d_{name}_under", lowBound=0),
            "over": pulp.LpVariable(f"d_{name}_over", lowBound=0),
        }
        for name in ("performance", "workload", "cost")
    }

    prob += (
        pulp.lpSum(players.loc[i, "value"] * x[i] for i in players.index)
        + d["performance"]["under"] - d["performance"]["over"] == TARGET_PERFORMANCE,
        "goal_performance",
    )
    prob += (
        pulp.lpSum(players.loc[i, "workload"] * x[i] for i in players.index)
        + d["workload"]["under"] - d["workload"]["over"] == TARGET_WORKLOAD,
        "goal_workload",
    )
    prob += (
        pulp.lpSum(players.loc[i, "cost"] * x[i] for i in players.index)
        + d["cost"]["under"] - d["cost"]["over"] == TARGET_COST,
        "goal_cost",
    )
    return d


# The miss that matters for each goal, and the target it is measured against.
UNWANTED = {
    "performance": ("under", TARGET_PERFORMANCE),
    "workload": ("over", TARGET_WORKLOAD),
    "cost": ("over", TARGET_COST),
}


def report(label, players, x, d):
    picked = players.loc[[i for i in players.index if x[i].value() > 0.5]]
    print(f"=== {label} ===")
    print(f"performance  {picked.value.sum():>10.2f}   target {TARGET_PERFORMANCE:>10.2f}"
          f"   short by {d['performance']['under'].value():.2f}")
    print(f"workload     {picked.workload.sum():>10,.0f}   target {TARGET_WORKLOAD:>10,}"
          f"   over by  {d['workload']['over'].value():,.0f}")
    print(f"cost         {picked.cost.sum():>10,.0f}   target {TARGET_COST:>10,}"
          f"   over by  {d['cost']['over'].value():,.0f}")
    print(f"forwards {picked.role.isin(FORWARD_ROLES).sum()}, backs "
          f"{(~picked.role.isin(FORWARD_ROLES)).sum()}")
    print()
    print(picked.sort_values(["role", "value"], ascending=[True, False])[
        ["name", "role", "appearances", "value", "workload", "cost"]
    ].round(2).to_string(index=False))
    print()
    return picked


def solve_weighted(players, w):
    prob = pulp.LpProblem("weighted", pulp.LpMinimize)
    x = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in players.index}
    structure(prob, x, players)
    d = goals(prob, x, players)

    prob += pulp.lpSum(
        w[name] * d[name][side] / target for name, (side, target) in UNWANTED.items()
    )
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    return report("weighted", players, x, d), prob.objective.value()


def solve_preemptive(players, order):
    """Settle each goal in turn, holding the earlier ones at their best."""
    achieved = {}
    for level, name in enumerate(order, 1):
        prob = pulp.LpProblem(f"priority_{level}", pulp.LpMinimize)
        x = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in players.index}
        structure(prob, x, players)
        d = goals(prob, x, players)

        side, target = UNWANTED[name]
        prob += (1 / target) * d[name][side]

        # Earlier priorities may not be worsened.
        for done, best in achieved.items():
            s, t = UNWANTED[done]
            prob += (1 / t) * d[done][s] <= best + 1e-6, f"hold_{done}"

        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        achieved[name] = d[name][side].value() / target
        print(f"priority {level}: {name}, miss {achieved[name] * 100:.2f}%")

    print()
    return report("pre-emptive", players, x, d)


def main() -> None:
    players = pd.read_parquet(f"{PROCESSED}/squad_value.parquet")
    players = players[players.role.notna() & players.cost.notna()].reset_index(drop=True)
    w = json.load(open(f"{PROCESSED}/weights.json"))["goals"]

    print(f"weights: performance {w['performance']:.3f}, "
          f"workload {w['workload']:.3f}, cost {w['cost']:.3f}")
    print()

    weighted, obj = solve_weighted(players, w)
    print(f"weighted objective value: {obj:.4f}")
    print()

    preemptive = solve_preemptive(players, ["performance", "workload", "cost"])

    same = set(weighted.player_id) & set(preemptive.player_id)
    print(f"the two squads share {len(same)} of 23 players")
    print(f"only in weighted:    {sorted(set(weighted.name) - set(preemptive.name))}")
    print(f"only in pre-emptive: {sorted(set(preemptive.name) - set(weighted.name))}")

    weighted.to_csv(f"{PROCESSED}/squad_weighted.csv", index=False)
    preemptive.to_csv(f"{PROCESSED}/squad_preemptive.csv", index=False)


if __name__ == "__main__":
    main()