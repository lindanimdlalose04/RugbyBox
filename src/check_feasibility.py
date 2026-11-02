"""Stage B and F check: bound the achievable range of each goal measure.

A goal target set outside the range any legal squad can reach makes that goal
either unsatisfiable or redundant, so each target must be placed inside the
range first. Solving for the extremes also confirms that the positional
constraints admit a feasible squad at all.

Run from the project root:  python src\\check_feasibility.py
"""

import pandas as pd
import pulp

PROCESSED = "data/processed"
SQUAD_SIZE = 23
FORWARDS_MIN, FORWARDS_MAX = 13, 14

ROLE_MIN = {
    "hooker": 2,
    "prop": 3,
    "lock": 3,
    "loose_forward": 4,
    "scrum_half": 2,
    "fly_half": 2,
    "centre": 2,
    "back_three": 3,
}
FRONT_ROW_MIN = 5
FORWARD_ROLES = {"hooker", "prop", "lock", "loose_forward"}


def build(players: pd.DataFrame, objective: str, sense: int):
    """A selection model over one objective, under the structural constraints."""
    prob = pulp.LpProblem("matchday_squad", sense)
    x = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in players.index}

    prob += pulp.lpSum(players.loc[i, objective] * x[i] for i in players.index)
    prob += pulp.lpSum(x.values()) == SQUAD_SIZE, "squad_size"

    forwards = pulp.lpSum(
        x[i] for i in players.index if players.loc[i, "role"] in FORWARD_ROLES
    )
    prob += forwards >= FORWARDS_MIN, "forwards_min"
    prob += forwards <= FORWARDS_MAX, "forwards_max"

    front_row = pulp.lpSum(
        x[i] for i in players.index if players.loc[i, "role"] in {"hooker", "prop"}
    )
    prob += front_row >= FRONT_ROW_MIN, "front_row_cover"

    for role, lo in ROLE_MIN.items():
        members = [i for i in players.index if players.loc[i, "role"] == role]
        prob += pulp.lpSum(x[i] for i in members) >= lo, f"min_{role}"

    return prob, x


def solve(players: pd.DataFrame, objective: str, sense: int, label: str):
    prob, x = build(players, objective, sense)
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        print(f"{label:<24} INFEASIBLE ({pulp.LpStatus[status]})")
        return None
    picked = players.loc[[i for i in players.index if x[i].value() > 0.5]]
    print(f"{label:<24} {picked[objective].sum():>12,.2f}")
    return picked


def main() -> None:
    squad = pd.read_parquet(f"{PROCESSED}/squad_value.parquet")
    squad = squad[squad.role.notna() & squad.cost.notna()].reset_index(drop=True)
    print(f"selectable players: {len(squad)}")
    print()

    weakest = solve(squad, "value", pulp.LpMinimize, "weakest squad")
    strongest = solve(squad, "value", pulp.LpMaximize, "strongest squad")
    lightest = solve(squad, "workload", pulp.LpMinimize, "lightest workload")
    heaviest = solve(squad, "workload", pulp.LpMaximize, "heaviest workload")
    cheapest = solve(squad, "cost", pulp.LpMinimize, "cheapest squad")
    dearest = solve(squad, "cost", pulp.LpMaximize, "most expensive squad")

    if strongest is None:
        print("No legal squad exists. Check the positional counts.")
        return

    print()
    print("--- achievable ranges ---")
    print(f"performance  {weakest.value.sum():.2f} to {strongest.value.sum():.2f}")
    print(f"workload     {lightest.workload.sum():,.0f} to {heaviest.workload.sum():,.0f} minutes")
    print(f"cost         £{cheapest.cost.sum():,.0f} to £{dearest.cost.sum():,.0f}")
    print()
    print("--- what the strongest squad costs you ---")
    print(f"its workload  {strongest.workload.sum():,.0f} minutes")
    print(f"its cost      £{strongest.cost.sum():,.0f}")


if __name__ == "__main__":
    main()