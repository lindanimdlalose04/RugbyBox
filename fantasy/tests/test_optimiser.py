"""The optimiser.

Two kinds of test. That the squad is legal, which is cheap to check and
catastrophic to get wrong. And that it is actually optimal, checked by trying
every single swap and confirming none improves it.
"""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import config as cfg  # noqa: E402
from rules import DEFAULT, Rules  # noqa: E402


@pytest.fixture(scope="module")
def opt():
    spec = importlib.util.spec_from_file_location("optimise", SRC / "05_optimise.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def players():
    path = ROOT / cfg.PROCESSED / "priced.parquet"
    if not path.exists():
        pytest.skip("prices not built; run stages 02 to 04")
    return pd.read_parquet(path)


@pytest.fixture(scope="module")
def squad(opt, players):
    chosen, _ = opt.pick(players, DEFAULT, budget=DEFAULT.budget)
    return chosen


@pytest.fixture(scope="module")
def unlimited(opt, players):
    chosen, _ = opt.pick(players, DEFAULT, budget=None)
    return chosen


# --- is the squad legal? --------------------------------------------------

def test_the_squad_is_the_right_size(squad):
    assert len(squad) == DEFAULT.squad_size


def test_every_quota_is_met_exactly(squad):
    counts = squad.role.value_counts()
    for role, needed in DEFAULT.quota.items():
        assert counts.get(role, 0) == needed, role


def test_the_squad_is_inside_the_budget(squad):
    assert squad.price.sum() <= DEFAULT.budget + 1e-6


def test_no_club_is_over_represented(squad):
    assert squad.team_id.value_counts().max() <= DEFAULT.club_cap


def test_nobody_is_picked_twice(squad):
    assert squad.player_id.nunique() == len(squad)


def test_there_is_exactly_one_captain(squad):
    assert squad.captain.sum() == 1


def test_the_captain_is_the_best_player_in_the_squad(squad):
    """With a doubling multiplier, no other choice can be better."""
    captain = squad[squad.captain].iloc[0]
    assert captain.projected_points == squad.projected_points.max()


# --- is the squad optimal? ------------------------------------------------

def test_no_single_swap_improves_the_squad(squad, players):
    """A one-opt check: the strongest practical test of optimality.

    Every selected player is swapped for every unselected player in the same
    position, and the result must never beat what the solver found.
    """
    best = opt_value(squad)
    outside = players[~players.index.isin(squad.index)]

    for i, out in squad.iterrows():
        candidates = outside[outside.role == out.role]
        for j, incoming in candidates.iterrows():
            trial = pd.concat([squad.drop(index=i), incoming.to_frame().T])
            if trial.price.sum() > DEFAULT.budget + 1e-6:
                continue
            if trial.team_id.value_counts().max() > DEFAULT.club_cap:
                continue
            trial = trial.copy()
            trial["captain"] = (
                trial.projected_points == trial.projected_points.max()
            )
            assert opt_value(trial) <= best + 1e-6, (
                f"swapping {out['name']} for {incoming['name']} would score more"
            )


def opt_value(squad: pd.DataFrame) -> float:
    base = squad.projected_points.sum()
    bonus = (DEFAULT.captain_multiplier - 1) * squad.loc[
        squad.captain, "projected_points"
    ].sum()
    return float(base + bonus)


def test_the_optimiser_beats_picking_the_best_by_position(squad, players):
    """The obvious greedy approach, which ignores the budget."""
    greedy = pd.concat([
        group.nlargest(DEFAULT.quota[role], "projected_points")
        for role, group in players.groupby("role") if role in DEFAULT.quota
    ])
    if greedy.price.sum() <= DEFAULT.budget:
        pytest.skip("the greedy squad is affordable, so there is nothing to beat")
    assert squad.price.sum() <= DEFAULT.budget < greedy.price.sum()


def test_the_optimiser_beats_best_value_for_money(squad, players):
    """Another tempting shortcut: buy whoever gives most points per unit."""
    priced = players.assign(vfm=players.projected_points / players.price)
    picks = []
    for role, needed in DEFAULT.quota.items():
        picks.append(priced[priced.role == role].nlargest(needed, "vfm"))
    shortcut = pd.concat(picks)
    if shortcut.price.sum() > DEFAULT.budget:
        pytest.skip("the value-for-money squad is not affordable")
    shortcut = shortcut.copy()
    shortcut["captain"] = (
        shortcut.projected_points == shortcut.projected_points.max()
    )
    assert opt_value(squad) >= opt_value(shortcut) - 1e-6


# --- does the budget do anything? -----------------------------------------

def test_the_budget_changes_the_squad(squad, unlimited):
    """If it did not, the optimiser would be ranking rather than choosing."""
    assert set(squad.index) != set(unlimited.index)


def test_removing_the_budget_scores_more(squad, unlimited):
    assert opt_value(unlimited) > opt_value(squad)


def test_the_unconstrained_squad_is_unaffordable(unlimited):
    assert unlimited.price.sum() > DEFAULT.budget


# --- failure modes --------------------------------------------------------

def test_an_impossible_budget_is_refused(opt, players):
    with pytest.raises(opt.NoSquad):
        opt.pick(players, DEFAULT, budget=1.0)


def test_an_impossible_club_cap_is_refused(opt, players):
    """Fifteen players and a cap of one needs fifteen clubs; there are ten."""
    strict = Rules(
        name="one per club",
        points=DEFAULT.points,
        appearance_points=DEFAULT.appearance_points,
        squad_size=DEFAULT.squad_size,
        quota=DEFAULT.quota,
        club_cap=1,
        budget=1000.0,
    )
    with pytest.raises(opt.NoSquad):
        opt.pick(players, strict, budget=strict.budget)


def test_a_generous_budget_reaches_the_unconstrained_squad(opt, players, unlimited):
    generous, _ = opt.pick(players, DEFAULT, budget=unlimited.price.sum() + 1)
    assert opt_value(generous) == pytest.approx(opt_value(unlimited), abs=1e-6)
