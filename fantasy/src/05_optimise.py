"""Stage E: pick the squad.

A binary integer programme. One variable per player, one if selected, plus a
second set for the captaincy. Maximise projected points subject to the squad
size, the budget, the position quotas and the cap on players from one club.

The captain is chosen inside the same programme rather than afterwards. The
best captain among an already-optimal squad is not necessarily part of the
best squad-and-captain pair, because a captaincy doubles one player's points
and so changes what that player is worth to the squad. Stage output shows
whether that mattered on this data.

Three things are checked rather than assumed:

  the budget binds        the squad chosen under the budget must differ
                          from the one chosen without it. Anything less
                          and the budget is decoration.
  the captain matters     solving jointly is compared against picking the
                          squad first and the captain second
  the price of a point    the budget is swept, so the exchange rate between
                          money and points is visible rather than implied

Run from the project root, after stage 04:  python src\\05_optimise.py
"""

import os
import sys

import pandas as pd
import pulp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from rules import DEFAULT  # noqa: E402


class NoSquad(RuntimeError):
    """Raised when no legal squad exists under the constraints given."""


def pick(players: pd.DataFrame, rules, budget=None, captain=True):
    """The best squad, and its captain.

    `budget` of None removes the budget constraint entirely, which is how the
    budget's effect is measured. `captain` of False scores every player once,
    for comparing a joint solve against a two-step one.
    """
    prob = pulp.LpProblem("squad", pulp.LpMaximize)
    index = list(players.index)

    chosen = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in index}
    leads = {i: pulp.LpVariable(f"c_{i}", cat="Binary") for i in index}
    points = players.projected_points

    extra = (rules.captain_multiplier - 1) if captain else 0
    prob += (
        pulp.lpSum(points[i] * chosen[i] for i in index)
        + pulp.lpSum(extra * points[i] * leads[i] for i in index)
    )

    prob += pulp.lpSum(chosen.values()) == rules.squad_size, "squad_size"

    if budget is not None:
        prob += pulp.lpSum(
            players.price[i] * chosen[i] for i in index
        ) <= budget, "budget"

    for role, needed in rules.quota.items():
        members = [i for i in index if players.role[i] == role]
        prob += pulp.lpSum(chosen[i] for i in members) == needed, f"quota_{role}"

    for club, members in players.groupby("team_id").groups.items():
        prob += pulp.lpSum(
            chosen[i] for i in members
        ) <= rules.club_cap, f"club_{club}"

    # Exactly one captain, and he has to be in the squad.
    if captain:
        prob += pulp.lpSum(leads.values()) == 1, "one_captain"
        for i in index:
            prob += leads[i] <= chosen[i], f"captain_in_squad_{i}"
    else:
        for i in index:
            prob += leads[i] == 0, f"no_captain_{i}"

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise NoSquad(
            f"solver returned {pulp.LpStatus[status]!r}. No legal squad exists "
            f"under these constraints."
        )

    squad = players.loc[[i for i in index if chosen[i].value() > 0.5]].copy()
    skipper = next((i for i in index if leads[i].value() and leads[i].value() > 0.5), None)
    squad["captain"] = squad.index == skipper
    return squad, pulp.value(prob.objective)


def expected(squad: pd.DataFrame, rules) -> float:
    """Points the squad is expected to score, counting the captaincy."""
    base = squad.projected_points.sum()
    bonus = (rules.captain_multiplier - 1) * squad.loc[
        squad.captain, "projected_points"
    ].sum()
    return base + bonus


def show(squad: pd.DataFrame, rules, label: str) -> None:
    order = ["prop", "hooker", "lock", "loose_forward",
             "scrum_half", "fly_half", "centre", "back_three"]
    print(f"=== {label} ===")
    print(f"projected points {expected(squad, rules):>8.1f}"
          f"   cost {squad.price.sum():>6.1f} of {rules.budget}")
    print()
    listing = squad.copy()
    listing["role"] = pd.Categorical(listing.role, order, ordered=True)
    listing = listing.sort_values(["role", "projected_points"], ascending=[True, False])
    listing["name"] = [
        f"{n} (c)" if c else n for n, c in zip(listing.name, listing.captain)
    ]
    print(listing[[
        "name", "role", "team", "appearances", "projected_points", "price"
    ]].round(2).to_string(index=False))
    print()


def main() -> None:
    rules = DEFAULT
    players = pd.read_parquet(f"{cfg.PROCESSED}/priced.parquet")
    print(f"choosing from {len(players)} players")
    print()

    squad, _ = pick(players, rules, budget=rules.budget)
    show(squad, rules, f"best squad within {rules.budget:.0f}")

    # --- does the budget change the answer? -------------------------------
    unlimited, _ = pick(players, rules, budget=None)
    shared = set(squad.index) & set(unlimited.index)

    print("--- does the budget bind on the optimum? ---")
    print(f"unconstrained squad: {expected(unlimited, rules):.1f} points "
          f"costing {unlimited.price.sum():.1f}")
    print(f"within the budget:   {expected(squad, rules):.1f} points "
          f"costing {squad.price.sum():.1f}")
    print(f"the two share {len(shared)} of {rules.squad_size} players")

    if len(shared) == rules.squad_size:
        raise SystemExit(
            "\n  The budget changes nothing: the same squad is optimal with and\n"
            "  without it. The optimiser is ranking, not choosing. Raise\n"
            "  PRICE_CURVE or lower the budget in config.py."
        )
    forgone = expected(unlimited, rules) - expected(squad, rules)
    print(f"the budget costs {forgone:.1f} projected points "
          f"({forgone / expected(unlimited, rules):.1%})")
    print(f"  dropped: {sorted(set(unlimited.name) - set(squad.name))}")
    print(f"  instead: {sorted(set(squad.name) - set(unlimited.name))}")
    print()

    # --- did the captaincy need solving jointly? --------------------------
    print("--- was it worth solving the captain jointly? ---")
    plain, _ = pick(players, rules, budget=rules.budget, captain=False)
    best_lead = plain.projected_points.idxmax()
    plain["captain"] = plain.index == best_lead
    two_step = expected(plain, rules)
    joint = expected(squad, rules)

    print(f"squad first, then captain: {two_step:.1f} points")
    print(f"both together:             {joint:.1f} points")
    if joint > two_step + 1e-6:
        print(f"  solving jointly gains {joint - two_step:.1f} points, so it is "
              f"worth the extra variables")
    else:
        print("  no difference on this data. The joint solve is kept anyway: it")
        print("  cannot be worse, and the two agreeing is a property of these")
        print("  numbers rather than something guaranteed.")
    print()

    # --- what is a point worth? -------------------------------------------
    print("--- what would more money buy? ---")
    # Equal steps, and the gain expressed per unit of budget. Unequal steps
    # make a diminishing return look like a rising one, because a wider step
    # buys more in total while buying less per pound.
    step = rules.budget * 0.1
    print(f"  {'budget':>8}{'points':>9}{'per extra unit':>16}")
    previous = None
    marginal = []
    for n in range(7, 17):
        budget = step * n
        try:
            trial, _ = pick(players, rules, budget=budget)
        except NoSquad:
            print(f"  {budget:>8.0f}      no legal squad")
            continue
        got = expected(trial, rules)
        if previous is None:
            rate = ""
        else:
            per_unit = (got - previous) / step
            marginal.append(per_unit)
            rate = f"{per_unit:>16.2f}"
        print(f"  {budget:>8.0f}{got:>9.1f}{rate}")
        previous = got

    print()
    if len(marginal) >= 2 and marginal[-1] < marginal[0]:
        print(f"  The exchange rate falls from {marginal[0]:.2f} points per unit "
              f"to {marginal[-1]:.2f},")
        print("  so the budget is worth most to a squad that has least.")
    else:
        print("  The exchange rate does not fall, which is worth investigating:")
        print("  a budget constraint should bind hardest when money is tightest.")

    squad.to_csv(f"{cfg.PROCESSED}/squad.csv", index=False)
    print()
    print(f"squad written to {cfg.PROCESSED}/squad.csv")


if __name__ == "__main__":
    main()
