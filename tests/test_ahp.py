"""The Analytic Hierarchy Process stage.

Two things are worth testing. The arithmetic, against a matrix worked by
hand so the test does not simply agree with the implementation. And the
judgements themselves, which carry a property the write-up should be honest
about: every position matrix was built from a rank order using one recipe, so
they all collapse to the same four weights in a different order.
"""

import json

import numpy as np
import pytest

CR_LIMIT = 0.10


def test_priorities_match_a_hand_worked_matrix(ahp):
    """Saaty's standard 3x3, geometric mean method, computed independently.

    Matrix:  a is 3x b, a is 5x c, b is 3x c.
    Row geometric means: (1*3*5)^(1/3), (1/3*1*3)^(1/3), (1/5*1/3*1)^(1/3)
                       = 2.466212,      1.000000,        0.405480
    Normalised by their sum of 3.871692.
    """
    names = ["a", "b", "c"]
    comparisons = {("a", "b"): 3, ("a", "c"): 5, ("b", "c"): 3}
    w, lambda_max, ci, cr = ahp.priorities(names, comparisons)

    expected = np.array([2.466212, 1.0, 0.405480])
    expected = expected / expected.sum()

    assert w == pytest.approx(expected, rel=1e-5)
    assert w.sum() == pytest.approx(1.0)
    assert lambda_max >= len(names) - 1e-9      # never below n
    assert ci == pytest.approx((lambda_max - 3) / 2)
    assert cr == pytest.approx(ci / 0.58)
    assert cr < CR_LIMIT


def test_a_perfectly_consistent_matrix_has_zero_inconsistency(ahp):
    # Built from an underlying scale, so it is consistent by construction.
    scale = {"a": 8.0, "b": 4.0, "c": 2.0, "d": 1.0}
    names = list(scale)
    comparisons = {
        (i, j): scale[i] / scale[j]
        for n, i in enumerate(names) for j in names[n + 1:]
    }
    w, lambda_max, ci, cr = ahp.priorities(names, comparisons)

    assert lambda_max == pytest.approx(len(names), abs=1e-9)
    assert ci == pytest.approx(0.0, abs=1e-9)
    assert cr == pytest.approx(0.0, abs=1e-9)
    assert w == pytest.approx([8 / 15, 4 / 15, 2 / 15, 1 / 15], rel=1e-9)


def test_reciprocals_are_filled_in(ahp):
    """Only the upper triangle is stated; b over a must follow from a over b."""
    w_ab, *_ = ahp.priorities(["a", "b"], {("a", "b"): 4})
    w_ba, *_ = ahp.priorities(["b", "a"], {("b", "a"): 1 / 4})
    assert w_ab == pytest.approx(w_ba[::-1])
    assert w_ab == pytest.approx([0.8, 0.2])


def test_every_published_matrix_is_consistent(ahp):
    from judgements import CRITERIA, GOALS, MEASURES

    _, _, _, goal_cr = ahp.priorities(["performance", "workload", "cost"], GOALS)
    assert goal_cr < CR_LIMIT

    for role, comparisons in CRITERIA.items():
        _, _, _, cr = ahp.priorities(MEASURES, comparisons)
        assert cr < CR_LIMIT, f"{role} matrix is inconsistent at CR {cr:.4f}"


def test_written_weights_are_a_valid_set(processed):
    weights = json.load(open(processed / "weights.json"))
    assert sum(weights["goals"].values()) == pytest.approx(1.0)
    for role, measures in weights["criteria"].items():
        assert sum(measures.values()) == pytest.approx(1.0), role
        assert all(v > 0 for v in measures.values()), role


def test_position_matrices_collapse_to_one_weight_vector(ahp):
    """A known limitation, pinned so a future change to it is deliberate.

    Every position matrix was generated from a rank ordering of the four
    measures using the same rank-gap recipe, so all eight produce the same
    four weights in a different order. The AHP therefore contributes a
    ranking and nothing more. If the judgements are ever revised into genuine
    pairwise comparisons, this test should be updated to expect several
    distinct weight vectors.
    """
    from judgements import CRITERIA, MEASURES

    vectors = {
        tuple(sorted(round(v, 6) for v in ahp.priorities(MEASURES, c)[0]))
        for c in CRITERIA.values()
    }
    assert len(vectors) == 1, (
        "the position matrices now differ in magnitude as well as order, "
        "which is an improvement: update this test to match"
    )
