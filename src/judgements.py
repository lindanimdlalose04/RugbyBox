"""Pairwise comparisons for the Analytic Hierarchy Process.

Saaty's 1 to 9 scale. A value of 3 in ("a", "b") means a is moderately more
important than b; use a fraction such as 1/3 when b is the more important.
Only the upper triangle is stated, the reciprocals follow.
"""

# How much the selection committee weighs each goal against the others.
GOALS = {
    ("performance", "workload"): 3,
    ("performance", "cost"): 5,
    ("workload", "cost"): 2,
}

MEASURES = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]

# How much each measure matters for each position.
CRITERIA = {
    role: {
        ("metres_carried", "line_breaks"): 1,
        ("metres_carried", "tackles_made"): 1,
        ("metres_carried", "turnovers_won"): 1,
        ("line_breaks", "tackles_made"): 1,
        ("line_breaks", "turnovers_won"): 1,
        ("tackles_made", "turnovers_won"): 1,
    }
    for role in [
        "prop", "hooker", "lock", "loose_forward",
        "scrum_half", "fly_half", "centre", "back_three",
    ]
}
