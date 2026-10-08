"""Stage D: derive goal and criterion weights by the Analytic Hierarchy Process.

Priorities are taken as the normalised row geometric means of each pairwise
comparison matrix, which is more transparent to reproduce by hand than the
eigenvector method and gives effectively the same result. Each matrix is
checked for consistency before its weights are used.

Run from the project root:  python src\\05_ahp.py
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judgements import CRITERIA, GOALS, MEASURES  # noqa: E402

OUT = "data/processed"

# Saaty's random index: the consistency of a randomly filled matrix of size n.
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32}
CR_LIMIT = 0.10


def priorities(names, comparisons):
    """Weights and consistency ratio for one pairwise comparison matrix."""
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


def report(label, names, comparisons):
    w, lam, ci, cr = priorities(names, comparisons)
    verdict = "ok" if cr < CR_LIMIT else "INCONSISTENT"
    print(f"{label:<16} CR {cr:.4f}  {verdict}")
    for name, weight in zip(names, w):
        print(f"    {name:<18} {weight:.4f}")
    return dict(zip(names, w.tolist())), cr


def main() -> None:
    os.makedirs(OUT, exist_ok=True)

    print("=== goal weights ===")
    goal_names = ["performance", "workload", "cost"]
    goal_weights, goal_cr = report("goals", goal_names, GOALS)

    print()
    print("=== criterion weights by position ===")
    criterion_weights, failures = {}, []
    for role, comparisons in CRITERIA.items():
        weights, cr = report(role, MEASURES, comparisons)
        criterion_weights[role] = weights
        if cr >= CR_LIMIT:
            failures.append(role)
        print()

    json.dump(
        {"goals": goal_weights, "criteria": criterion_weights},
        open(f"{OUT}/weights.json", "w"),
        indent=2,
    )

    print("--- checkpoint ---")
    if goal_cr >= CR_LIMIT:
        print(f"goal matrix INCONSISTENT at CR {goal_cr:.4f}, revise before use")
    if failures:
        print(f"inconsistent position matrices: {', '.join(failures)}")
    if goal_cr < CR_LIMIT and not failures:
        print("all matrices consistent, weights written to weights.json")


if __name__ == "__main__":
    main()