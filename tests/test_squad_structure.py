"""The twelve constraints that no goal may override.

A squad that breaks one of these is not a squad that could take the field, so
these are the tests worth having even if nothing else is tested. Both solved
squads are checked against every constraint.
"""

import pytest

SQUADS = ["weighted", "preemptive"]

# Stated here rather than read from config, so the test fails if a role is
# ever silently dropped from the constraint set.
ROLES = [
    "hooker", "prop", "lock", "loose_forward",
    "scrum_half", "fly_half", "centre", "back_three",
]


@pytest.fixture(params=SQUADS)
def squad(request, weighted, preemptive):
    return {"weighted": weighted, "preemptive": preemptive}[request.param]


def test_squad_holds_exactly_twenty_three(squad, cfg):
    assert len(squad) == cfg.SQUAD_SIZE


def test_no_player_selected_twice(squad):
    assert squad.player_id.nunique() == len(squad)


def test_forward_count_within_bounds(squad, cfg):
    forwards = squad.role.isin(cfg.FORWARD_ROLES).sum()
    assert cfg.FORWARDS_MIN <= forwards <= cfg.FORWARDS_MAX


def test_front_row_cover(squad, cfg):
    """The laws require trained front-row cover on the bench."""
    assert squad.role.isin(cfg.FRONT_ROW_ROLES).sum() >= cfg.FRONT_ROW_MIN


@pytest.mark.parametrize("role", ROLES)
def test_minimum_per_role(squad, cfg, role):
    assert role in cfg.ROLE_MIN, f"{role} has lost its minimum"
    assert (squad.role == role).sum() >= cfg.ROLE_MIN[role]


def test_constraint_set_covers_every_role(cfg):
    assert set(cfg.ROLE_MIN) == set(ROLES)
    assert cfg.FORWARD_ROLES <= set(ROLES)
    assert cfg.FRONT_ROW_ROLES <= cfg.FORWARD_ROLES


def test_every_selected_player_is_priced_and_classified(squad):
    assert squad.cost.notna().all()
    assert squad.role.notna().all()


def test_role_minimums_are_satisfiable_at_all(squad_value, cfg):
    """A sanity check on the constraints themselves, not on a solution.

    If the pool cannot cover the role minimums, every solve downstream is
    infeasible and the failure should be reported here rather than as a
    solver status buried in a log.
    """
    pool = squad_value[squad_value.role.notna() & squad_value.cost.notna()]
    for role, lo in cfg.ROLE_MIN.items():
        assert (pool.role == role).sum() >= lo, f"not enough {role} in the pool"
    assert sum(cfg.ROLE_MIN.values()) <= cfg.SQUAD_SIZE
