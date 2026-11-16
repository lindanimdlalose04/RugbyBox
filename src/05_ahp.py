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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from ahp import CR_LIMIT, priorities  # noqa: E402
from judgements import CRITERIA, GOALS, MEASURES  # noqa: E402

OUT = cfg.PROCESSED


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