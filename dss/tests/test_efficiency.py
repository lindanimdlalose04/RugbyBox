"""The three corrections applied to the efficiency measure in stage C.

Each is tested for the property it was added to provide: weight restrictions
stop one measure carrying a score, cross-efficiency discriminates and stays
bounded, and shrinkage pulls a thin-evidence player toward the league rather
than letting a freak rate stand.
"""

import numpy as np
import pandas as pd
import pytest

OUTPUTS = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]


def make_pool(rows):
    """A small peer group: one row per player, minutes plus the four outputs."""
    return pd.DataFrame([
        {"player_id": f"p{i}", "minutes": m, **dict(zip(OUTPUTS, outs))}
        for i, (m, outs) in enumerate(rows)
    ])


def normalise(pool):
    """Scale each output by the peer mean, as stage C does before solving.

    Weight restrictions are shares of the weight vector, so they only mean
    anything once the outputs are on a common scale. Metres run into the
    hundreds while turnovers are counted in ones, and a band applied to raw
    units would be comparing a weight per metre with a weight per turnover.
    """
    out = pool.copy()
    for r in OUTPUTS:
        out[r] = pool[r] / pool[r].mean()
    return out


# --- weight restrictions -------------------------------------------------

def test_restrictions_stop_one_measure_carrying_the_score(dea):
    """A player strong on one output only should no longer reach 1.000."""
    pool = normalise(make_pool([
        (100, [500, 0, 0, 0]),      # extreme on metres, nothing else
        (100, [100, 5, 20, 3]),
        (100, [120, 4, 18, 2]),
        (100, [90, 6, 22, 4]),
    ]))
    specialist = pool.iloc[0]

    free, _ = dea.solve_weights(specialist, pool, None)
    assert free == pytest.approx(1.0), "unrestricted CCR should flatter him"

    weights = {"prop": dict(zip(OUTPUTS, [0.25, 0.25, 0.25, 0.25]))}
    bounds = dea.share_bounds("prop", weights, 0.5)
    restricted, _ = dea.solve_weights(specialist, pool, bounds)
    assert restricted < free, "restrictions should cost the one-trick player"


def test_a_rounded_player_is_not_punished_by_the_restrictions(dea):
    """The bands should cost the specialist, not everybody."""
    pool = normalise(make_pool([
        (100, [220, 4, 17, 3]),     # strong across the board
        (100, [100, 5, 20, 3]),
        (100, [120, 4, 18, 2]),
        (100, [90, 2, 12, 1]),
    ]))
    weights = {"r": dict(zip(OUTPUTS, [0.25, 0.25, 0.25, 0.25]))}
    bounds = dea.share_bounds("r", weights, 0.5)

    free, _ = dea.solve_weights(pool.iloc[0], pool, None)
    restricted, _ = dea.solve_weights(pool.iloc[0], pool, bounds)
    assert restricted == pytest.approx(free, rel=0.05)


def test_share_bounds_are_always_satisfiable(dea):
    """The AHP weights themselves sit inside every band, so a solution exists."""
    w = {"r": dict(zip(OUTPUTS, [0.4832, 0.2717, 0.1569, 0.0882]))}
    bounds = dea.share_bounds("r", w, 0.5)
    for measure, (lo, hi) in bounds.items():
        assert lo <= w["r"][measure] <= hi
    assert sum(lo for lo, _ in bounds.values()) <= 1.0
    assert sum(hi for _, hi in bounds.values()) >= 1.0


def test_share_bounds_disabled_returns_nothing(dea):
    assert dea.share_bounds("r", {"r": {}}, None) is None


def test_restricted_weights_respect_their_bands(dea):
    pool = normalise(make_pool([
        (100, [300, 3, 15, 2]),
        (100, [100, 5, 20, 3]),
        (100, [120, 4, 18, 2]),
    ]))
    w = {"r": dict(zip(OUTPUTS, [0.4, 0.3, 0.2, 0.1]))}
    bounds = dea.share_bounds("r", w, 0.5)
    _, u = dea.solve_weights(pool.iloc[0], pool, bounds)

    shares = u / u.sum()
    for share, measure in zip(shares, OUTPUTS):
        lo, hi = bounds[measure]
        assert lo - 1e-6 <= share <= hi + 1e-6, f"{measure} share {share:.3f}"


# --- unit invariance ------------------------------------------------------

def test_unrestricted_score_is_invariant_to_units(dea):
    """Why normalising outputs first is safe.

    DEA does not care what units an output is recorded in, so rescaling one
    must leave the unrestricted score alone. That is what lets stage C
    normalise by the peer mean and then restrict weight shares meaningfully.
    """
    pool = make_pool([
        (100, [300, 3, 15, 2]),
        (120, [280, 5, 22, 1]),
        (90, [200, 2, 18, 4]),
    ])
    before, _ = dea.solve_weights(pool.iloc[0], pool, None)

    scaled = pool.copy()
    scaled["metres_carried"] = scaled.metres_carried / 1000.0
    after, _ = dea.solve_weights(scaled.iloc[0], scaled, None)

    assert before == pytest.approx(after, abs=1e-6)


# --- cross-efficiency -----------------------------------------------------

def test_cross_efficiency_stays_within_zero_and_one(squad_efficiency):
    cross = squad_efficiency.efficiency_cross.dropna()
    assert len(cross) > 0
    assert cross.between(0.0, 1.0).all()


def test_cross_efficiency_never_flatters_more_than_own_weights(squad_efficiency):
    """A player cannot do better under others' weights than under his own."""
    both = squad_efficiency.dropna(subset=["efficiency_own", "efficiency_cross"])
    assert (both.efficiency_cross <= both.efficiency_own + 1e-6).all()


def test_the_measure_discriminates(squad_efficiency):
    """The plain model left five players tied at a perfect score."""
    assert (squad_efficiency.efficiency >= 0.9999).sum() == 0
    assert squad_efficiency.efficiency.nunique() == len(squad_efficiency)


# --- shrinkage ------------------------------------------------------------

def test_evidence_weight_rises_with_minutes(squad_efficiency):
    ordered = squad_efficiency.sort_values("minutes")
    assert ordered.evidence.is_monotonic_increasing
    assert ordered.evidence.between(0.0, 1.0).all()


def test_thin_evidence_is_pulled_toward_the_league(squad_efficiency):
    """A player with little playing time is treated as a typical peer."""
    thin = squad_efficiency.nsmallest(5, "minutes")
    for _, p in thin.iterrows():
        to_baseline = abs(p.efficiency - p.league_baseline)
        to_own = abs(p.efficiency_raw - p.league_baseline)
        assert to_baseline <= to_own + 1e-9, p["name"]
        assert p.evidence < 0.25, f"{p['name']} should carry little weight"


def test_a_well_evidenced_player_keeps_most_of_his_own_score(squad_efficiency):
    thick = squad_efficiency.nlargest(3, "minutes")
    assert (thick.evidence > 0.5).all()


def test_shrinkage_is_a_weighted_average(squad_efficiency):
    s = squad_efficiency
    rebuilt = s.evidence * s.efficiency_raw + (1 - s.evidence) * s.league_baseline
    assert rebuilt.values == pytest.approx(s.efficiency.values, abs=1e-9)


# --- the stabilisation estimate ------------------------------------------

def test_stabilisation_point_is_plausible(dea, processed, players_season):
    path = processed / "player_appearances.parquet"
    if not path.exists():
        pytest.skip("appearance table not built")

    weights = __import__("ahp").measure_weights()
    roles = [r for r in weights if (players_season.role == r).any()]
    scales = {
        r: players_season[
            (players_season.role == r) & players_season.frontier
        ][OUTPUTS].mean().to_dict()
        for r in roles
    }

    result = dea.stabilisation_minutes(
        pd.read_parquet(path), players_season, weights, scales
    )
    assert result is not None, "the estimate should be makeable from this data"
    k, half_minutes, r_half = result
    assert 0 < r_half < 1, "a split-half correlation outside (0, 1) is nonsense"
    assert 50 < k < 5000, f"stabilisation point of {k:.0f} minutes is implausible"
    assert half_minutes > 0


def test_reliability_formula_matches_the_shrinkage_weight(squad_efficiency, dea):
    """evidence = minutes / (minutes + K) must imply a single consistent K."""
    s = squad_efficiency[squad_efficiency.minutes > 0]
    implied = s.minutes * (1 - s.evidence) / s.evidence
    assert implied.std() < 1e-6, "the shrinkage is not using one K"
    assert implied.mean() > 0
