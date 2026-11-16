"""Analytic Hierarchy Process arithmetic.

Priorities are the normalised row geometric means of a pairwise comparison
matrix, which is easier to reproduce by hand than the eigenvector method and
gives effectively the same answer. Every matrix is checked for consistency
before its weights are used.

This lives apart from stage D so that stage C can use the same weights
without depending on a file stage D has not written yet. Stage D remains the
place where the weights are reported and saved.
"""

import numpy as np

# Saaty's random index: the consistency of a randomly filled matrix of size n.
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32}
CR_LIMIT = 0.10


def priorities(names, comparisons):
    """Weights and consistency ratio for one pairwise comparison matrix.

    Only the upper triangle of `comparisons` need be stated; the reciprocals
    are filled in. Returns (weights, lambda_max, consistency index,
    consistency ratio).
    """
    n = len(names)
    matrix = np.ones((n, n))
    for (a, b), value in comparisons.items():
        i, j = names.index(a), names.index(b)
        matrix[i, j] = value
        matrix[j, i] = 1 / value

    weights = np.prod(matrix, axis=1) ** (1 / n)
    weights = weights / weights.sum()

    lambda_max = float(np.mean((matrix @ weights) / weights))
    ci = (lambda_max - n) / (n - 1)
    cr = ci / RANDOM_INDEX[n] if RANDOM_INDEX[n] else 0.0
    return weights, lambda_max, ci, cr


def measure_weights():
    """The four measure weights for each position, keyed by role.

    Derived from the judgements rather than read back from stage D's output,
    so stage C can call this before stage D has run.
    """
    from judgements import CRITERIA, MEASURES

    return {
        role: dict(zip(MEASURES, priorities(MEASURES, comparisons)[0]))
        for role, comparisons in CRITERIA.items()
    }
