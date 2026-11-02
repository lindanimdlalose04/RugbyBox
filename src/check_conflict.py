"""Find the performance level at which the three goals start to conflict.

Maximises squad performance while holding the workload and budget targets as
hard limits. The answer is the best performance obtainable without breaking
either promise, so a performance target above it cannot be met without
sacrificing one of the other two.

Run from the project root:  python src\\check_conflict.py
"""

import pandas as pd
import pulp

PROCESSED = "data/processed"
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


def main() -> None:
    p = pd.read_parquet(f"{PROCESSED}/squad_value.parquet")
    p = p[p.role.notna() & p.cost.notna()].reset_index(drop=True)

    prob = pulp.LpProblem("breaking_point", pulp.LpMaximize)
    x = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in p.index}

    prob += pulp.lpSum(p.loc[i, "value"] * x[i] for i in p.index)

    prob += pulp.lpSum(x.values()) == SQUAD_SIZE
    fwd = pulp.lpSum(x[i] for i in p.index if p.loc[i, "role"] in FORWARD_ROLES)
    prob += fwd >= FORWARDS_MIN
    prob += fwd <= FORWARDS_MAX
    prob += pulp.lpSum(
        x[i] for i in p.index if p.loc[i, "role"] in {"hooker", "prop"}
    ) >= FRONT_ROW_MIN
    for role, lo in ROLE_MIN.items():
        prob += pulp.lpSum(x[i] for i in p.index if p.loc[i, "role"] == role) >= lo

    # Both other promises held as hard limits.
    prob += pulp.lpSum(p.loc[i, "workload"] * x[i] for i in p.index) <= TARGET_WORKLOAD
    prob += pulp.lpSum(p.loc[i, "cost"] * x[i] for i in p.index) <= TARGET_COST

    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    print(f"status: {pulp.LpStatus[prob.status]}")
    if pulp.LpStatus[prob.status] != "Optimal":
        return

    picked = p.loc[[i for i in p.index if x[i].value() > 0.5]]
    print()
    print(f"best performance without breaking either promise: {picked.value.sum():.2f}")
    print(f"  that squad's workload  {picked.workload.sum():,.0f} of {TARGET_WORKLOAD:,}")
    print(f"  that squad's cost      £{picked.cost.sum():,.0f} of £{TARGET_COST:,}")
    print()
    print(f"best performance ignoring both promises: 11.45")
    print()
    print("Set the performance target above the first number and below the")
    print("second, and the three goals cannot all be satisfied at once.")


if __name__ == "__main__":
    main()