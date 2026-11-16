"""Invariants of the two goal programming runs.

The pre-emptive form carries a promise that is easy to break by accident:
a lower priority may never be bought at the expense of a higher one. That is
checked here by re-solving the first priority on its own and confirming the
shipped pre-emptive squad still achieves it.
"""

import pulp
import pytest


def miss(squad, cfg, name):
    """The unwanted deviation on one goal, as a fraction of its target."""
    side, target = cfg.UNWANTED[name]
    total = squad[cfg.GOAL_COLUMN[name]].sum()
    gap = (target - total) if side == "under" else (total - target)
    return max(gap, 0.0) / target


def test_only_the_unwanted_direction_counts_as_a_miss(cfg):
    """Overshooting performance, or coming in under budget, is not a miss."""
    import pandas as pd

    over = pd.DataFrame({
        "value": [cfg.TARGET_PERFORMANCE + 1],
        "workload": [cfg.TARGET_WORKLOAD - 100],
        "cost": [cfg.TARGET_COST - 1000],
    })
    for name in cfg.GOAL_NAMES:
        assert miss(over, cfg, name) == 0.0

    under = pd.DataFrame({
        "value": [cfg.TARGET_PERFORMANCE - cfg.TARGET_PERFORMANCE * 0.1],
        "workload": [cfg.TARGET_WORKLOAD * 1.1],
        "cost": [cfg.TARGET_COST * 1.1],
    })
    for name in cfg.GOAL_NAMES:
        assert miss(under, cfg, name) == pytest.approx(0.1)


def test_every_goal_is_measurable_on_both_squads(weighted, preemptive, cfg):
    for squad in (weighted, preemptive):
        for name in cfg.GOAL_NAMES:
            column = cfg.GOAL_COLUMN[name]
            assert column in squad.columns
            assert squad[column].notna().all()
            assert squad[column].sum() > 0


def test_preemptive_achieves_the_best_possible_first_priority(
    squad_value, preemptive, cfg, goal_programme
):
    """Priority one must be settled as far as the pool allows."""
    players = cfg.selectable(squad_value)
    first = "performance"

    prob = pulp.LpProblem("priority_one_alone", pulp.LpMinimize)
    x = cfg.selection_vars(players)
    cfg.add_structure(prob, x, players)
    d = goal_programme.goals(prob, x, players)
    side, target = cfg.UNWANTED[first]
    prob += (1 / target) * d[first][side]
    cfg.solve(prob, "priority one alone")

    best = d[first][side].value() / target
    achieved = miss(preemptive, cfg, first)
    assert achieved == pytest.approx(best, abs=1e-6), (
        f"pre-emptive squad misses {first} by {achieved:.6f}, "
        f"but {best:.6f} was achievable"
    )


def test_weighted_objective_is_not_beaten_by_the_preemptive_squad(
    weighted, preemptive, cfg, processed
):
    """The weighted run should win on its own objective, or tie."""
    import json
    w = json.load(open(processed / "weights.json"))["goals"]

    def objective(squad):
        return sum(
            w[name] * miss(squad, cfg, name) for name in cfg.GOAL_NAMES
        )

    assert objective(weighted) <= objective(preemptive) + 1e-9


def test_both_squads_are_drawn_from_the_selectable_pool(
    weighted, preemptive, squad_value, cfg
):
    pool = set(cfg.selectable(squad_value).player_id)
    assert set(weighted.player_id) <= pool
    assert set(preemptive.player_id) <= pool


def test_solve_refuses_a_problem_with_no_answer(cfg):
    """A bad solve must raise rather than return a meaningless figure."""
    prob = pulp.LpProblem("impossible", pulp.LpMinimize)
    y = pulp.LpVariable("y", lowBound=0)
    prob += y
    prob += y >= 5
    prob += y <= 1
    with pytest.raises(cfg.SolverError):
        cfg.solve(prob, "deliberately infeasible")
