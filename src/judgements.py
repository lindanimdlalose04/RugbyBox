"""Pairwise comparisons for the Analytic Hierarchy Process.

Saaty's 1 to 9 scale. A value of 3 in ("a", "b") means a is moderately more
important than b; a fraction such as 1/3 means b is the more important.
Only the upper triangle is stated, the reciprocals follow.

Goal weights reflect a mid-season league fixture with a congested run of
games ahead: winning the fixture leads, but player workload still constrains
selection and the wage budget constrains it less.

Position weights were set by first ranking the four measures for each
position, then converting the gaps between ranks into comparison values.
"""

GOALS = {
    ("performance", "workload"): 3,   # strength moderately beats protecting players
    ("performance", "cost"): 5,       # strength strongly beats saving money
    ("workload", "cost"): 2,          # protecting players slightly beats saving money
}

MEASURES = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]

CRITERIA = {
    # tackles, breaks, metres, turnovers
    "prop": {
        ("metres_carried", "line_breaks"): 1 / 2,
        ("metres_carried", "tackles_made"): 1 / 3,
        ("metres_carried", "turnovers_won"): 2,
        ("line_breaks", "tackles_made"): 1 / 2,
        ("line_breaks", "turnovers_won"): 3,
        ("tackles_made", "turnovers_won"): 5,
    },
    # tackles, turnovers, breaks, metres
    "hooker": {
        ("metres_carried", "line_breaks"): 1 / 2,
        ("metres_carried", "tackles_made"): 1 / 5,
        ("metres_carried", "turnovers_won"): 1 / 3,
        ("line_breaks", "tackles_made"): 1 / 3,
        ("line_breaks", "turnovers_won"): 1 / 2,
        ("tackles_made", "turnovers_won"): 2,
    },
    # tackles, metres, breaks, turnovers
    "lock": {
        ("metres_carried", "line_breaks"): 2,
        ("metres_carried", "tackles_made"): 1 / 2,
        ("metres_carried", "turnovers_won"): 3,
        ("line_breaks", "tackles_made"): 1 / 3,
        ("line_breaks", "turnovers_won"): 2,
        ("tackles_made", "turnovers_won"): 5,
    },
    # tackles, turnovers, breaks, metres
    "loose_forward": {
        ("metres_carried", "line_breaks"): 1 / 2,
        ("metres_carried", "tackles_made"): 1 / 5,
        ("metres_carried", "turnovers_won"): 1 / 3,
        ("line_breaks", "tackles_made"): 1 / 3,
        ("line_breaks", "turnovers_won"): 1 / 2,
        ("tackles_made", "turnovers_won"): 2,
    },
    # breaks, tackles, metres, turnovers
    "scrum_half": {
        ("metres_carried", "line_breaks"): 1 / 3,
        ("metres_carried", "tackles_made"): 1 / 2,
        ("metres_carried", "turnovers_won"): 2,
        ("line_breaks", "tackles_made"): 2,
        ("line_breaks", "turnovers_won"): 5,
        ("tackles_made", "turnovers_won"): 3,
    },
    # breaks, metres, tackles, turnovers
    "fly_half": {
        ("metres_carried", "line_breaks"): 1 / 2,
        ("metres_carried", "tackles_made"): 2,
        ("metres_carried", "turnovers_won"): 3,
        ("line_breaks", "tackles_made"): 3,
        ("line_breaks", "turnovers_won"): 5,
        ("tackles_made", "turnovers_won"): 2,
    },
    # breaks, tackles, metres, turnovers
    "centre": {
        ("metres_carried", "line_breaks"): 1 / 3,
        ("metres_carried", "tackles_made"): 1 / 2,
        ("metres_carried", "turnovers_won"): 2,
        ("line_breaks", "tackles_made"): 2,
        ("line_breaks", "turnovers_won"): 5,
        ("tackles_made", "turnovers_won"): 3,
    },
    # metres, breaks, tackles, turnovers
    "back_three": {
        ("metres_carried", "line_breaks"): 2,
        ("metres_carried", "tackles_made"): 3,
        ("metres_carried", "turnovers_won"): 5,
        ("line_breaks", "tackles_made"): 2,
        ("line_breaks", "turnovers_won"): 3,
        ("tackles_made", "turnovers_won"): 2,
    },
}