"""The two measures the project derives rather than reads.

Both are stated in the README with a specific claim attached. Minutes are
rebuilt from carries and a carrying rate, claimed accurate to a mean absolute
error of 2.5 minutes. Cost is modelled as a position average scaled by playing
time, claimed to preserve the published position average. Each claim is
checked here against the data rather than taken on trust.
"""

import numpy as np
import pandas as pd

CLAIMED_MAE_MINUTES = 2.5


def test_minutes_reconstruction_matches_the_claimed_accuracy(
    clean, league_raw, cfg
):
    """Rebuild minutes where they are recorded, and compare with the record.

    Scoped to the season window, because that is the only place stage B ever
    reconstructs minutes: it filters to the window first and derives minutes
    afterwards. Measured across every season in the raw file the error is
    3.01 minutes, but those earlier rows never enter the model.
    """
    df = league_raw.copy()
    df["match_date"] = pd.to_datetime(df.game_date, format="%Y%m%d")
    df = df[
        (df.match_date >= cfg.SEASON_START) & (df.match_date <= cfg.SEASON_END)
    ]

    recorded = pd.to_numeric(df.get("minutes_played"), errors="coerce")
    rate = pd.to_numeric(df.get("carries_per_minute"), errors="coerce")
    carries = pd.to_numeric(df.get("carries"), errors="coerce")

    # Only the appearances where the source records minutes AND the rate
    # needed to derive them, so the two are genuinely comparable.
    both = recorded.notna() & (rate > 0) & carries.notna()
    assert both.sum() > 100, "too few overlapping rows to judge the claim"

    derived = (carries[both] / rate[both]).clip(upper=80)
    mae = (derived - recorded[both].clip(upper=80)).abs().mean()
    assert mae <= CLAIMED_MAE_MINUTES, (
        f"minute reconstruction is off by {mae:.2f} on average, "
        f"against a claimed {CLAIMED_MAE_MINUTES}"
    )


def test_reconstruction_prefers_the_recorded_value(clean):
    """Where minutes are recorded, they are used, not the derived figure."""
    df = pd.DataFrame({
        "minutes_played": [60.0, np.nan],
        "carries_per_minute": [0.5, 0.2],
        "carries": [5.0, 10.0],
    })
    out = clean.reconstruct_minutes(df)
    assert out.iloc[0] == 60.0      # recorded wins over 5 / 0.5 = 10
    assert out.iloc[1] == 50.0      # derived where nothing is recorded


def test_reconstruction_never_exceeds_a_full_match(clean):
    df = pd.DataFrame({
        "minutes_played": [np.nan],
        "carries_per_minute": [0.01],
        "carries": [20.0],          # would imply 2000 minutes
    })
    assert clean.reconstruct_minutes(df).iloc[0] == 80


def test_cost_model_preserves_the_published_position_average(
    players_season, clean
):
    """Mean modelled cost within a role must stay in step with its salary.

    Individual cost is the position average scaled by a mean-preserving
    multiplier, so dividing each role's mean modelled cost by its published
    annual salary must give the same constant (one over the club's fixture
    count) for every role.
    """
    squad = players_season[players_season.in_squad].dropna(subset=["cost", "role"])
    ratios = {
        role: group.cost.mean() / clean.SALARY[role]
        for role, group in squad.groupby("role")
    }
    assert len(ratios) >= 6, "too few roles present to judge the claim"
    spread = max(ratios.values()) - min(ratios.values())
    assert spread < 1e-9, f"position averages are not preserved: {ratios}"


def test_cost_is_modelled_only_for_the_club(players_season):
    """A per-match cost for a player at another club would be meaningless."""
    assert players_season[~players_season.in_squad].cost.isna().all()


def test_cost_multiplier_cannot_go_negative(players_season, cfg, clean):
    """The multiplier is 1 + d(raw - 1) with raw >= 0, so it floors at 1 - d."""
    squad = players_season[players_season.in_squad].dropna(subset=["cost", "role"])
    implied = squad.cost / squad.role.map(clean.SALARY)
    assert (implied > 0).all()
    role_mean = implied.groupby(squad.role).transform("mean")
    multiplier = implied / role_mean
    assert multiplier.min() >= 1 - cfg.COST_DISPERSION - 1e-9
