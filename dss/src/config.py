"""Single source of truth for paths, the laws of the game, and the goal targets.

Anything duplicated across stages, and every assumption the README offers up
for sensitivity analysis, lives here. The selection constraints in particular
were previously restated in three files, so a change to one of them could
leave the diagnostics describing a model that no longer existed.

Nothing in this module reads or writes data. Import it, do not run it.
"""

import pulp

# --- paths ---------------------------------------------------------------

RAW = "data/raw"
PROCESSED = "data/processed"
PLAYER_CACHE = f"{RAW}/players"

# --- the club and the season window --------------------------------------

CLUB_ID = "821a6e9b"                      # Bath Rugby
COMPETITION = "Gallagher Premiership"
SEASON_START = "2025-09-01"
SEASON_END = "2026-06-30"

# --- the laws of the game -------------------------------------------------
# A matchday 23 and the positional cover a team sheet must carry. These are
# hard constraints: no goal may override them.

SQUAD_SIZE = 23
FORWARDS_MIN, FORWARDS_MAX = 13, 14
FRONT_ROW_MIN = 5                         # trained front-row cover

ROLE_MIN = {
    "hooker": 2, "prop": 3, "lock": 3, "loose_forward": 4,
    "scrum_half": 2, "fly_half": 2, "centre": 2, "back_three": 3,
}

FORWARD_ROLES = {"hooker", "prop", "lock", "loose_forward"}
FRONT_ROW_ROLES = {"hooker", "prop"}

# --- goal targets ---------------------------------------------------------
# Each target is placed inside the range a legal squad can actually reach.
# Those ranges come from check_feasibility.py, which solves for the extreme
# of each measure under the structural constraints alone; check_conflict.py
# then finds the performance level at which the three begin to compete. The
# values recorded below were read off those two reports, so re-run both after
# changing the player pool or any constraint above.
#
#   performance   a legal squad can reach 7.91 to 10.46. Holding workload
#                 and cost as hard limits, the best reachable is 9.58. The
#                 target sits above that breaking point on purpose, so the
#                 goal programme has to price a real conflict rather than
#                 report an easy win. The rule used is to place it 42% of
#                 the way from the breaking point to the maximum:
#                     9.58 + 0.42 * (10.46 - 9.58) = 9.95
#                 Performance is a sum of selection values, so this number
#                 only means anything on the scale that produced it. Stage C
#                 was revised to restrict the efficiency weights, score by
#                 cross-efficiency and shrink thin evidence toward the league
#                 average, which moved the whole scale down. The previous
#                 target of 11.1 belonged to the old scale and is now beyond
#                 anything a legal squad can reach. Re-run check_feasibility
#                 and check_conflict after any change to stage C or stage E,
#                 and reset this with the rule above.
#   workload      achievable 2 370 to 3 990 minutes. A mid-season ceiling
#                 for a congested run of fixtures.
#   cost          achievable £109 231 to £170 228. The matchday wage budget
#                 for one fixture.

TARGET_PERFORMANCE = 9.95
TARGET_WORKLOAD = 2875
TARGET_COST = 130_000

# The miss that matters for each goal, and the target it is measured against.
# Overshooting on performance and undershooting on workload or cost are both
# welcome, so neither is penalised.
UNWANTED = {
    "performance": ("under", TARGET_PERFORMANCE),
    "workload": ("over", TARGET_WORKLOAD),
    "cost": ("over", TARGET_COST),
}

GOAL_NAMES = ("performance", "workload", "cost")

# The column each goal is measured over.
GOAL_COLUMN = {"performance": "value", "workload": "workload", "cost": "cost"}

# --- stated assumptions ---------------------------------------------------
# Each of these is a judgement rather than a measurement. They are gathered
# here so a sensitivity analysis can sweep them without hunting through the
# pipeline.

FRONTIER_MIN_APPS = 3      # appearances before a player may define the frontier
WORKLOAD_FIXTURES = 3      # recent fixtures counted towards accumulated workload
COST_DISPERSION = 0.6      # 0 flat position average, 1 strictly proportional to minutes
ALPHA = 0.35               # weight on efficiency against volume in selection value

# --- efficiency measurement (stage C) ------------------------------------
# With one input and four outputs, an unrestricted CCR programme lets each
# player choose the weighting that flatters him, so a short spell carrying one
# strong rate reaches the frontier. Three corrections are applied.

# 1. Virtual weight restrictions (Wong and Beasley). Each output's share of a
#    player's weighted total is held within this band of the position's AHP
#    weight, so no single measure can carry the whole score. 0.5 means each
#    share may sit between half and one and a half times its AHP weight.
#    Set to None to disable and recover the unrestricted CCR score.
VIRTUAL_WEIGHT_TOLERANCE = 0.5

# 2. Cross-efficiency. Every player is scored under every peer's optimal
#    weights as well as his own, and the average is taken. This removes the
#    self-flattering weighting and breaks the ties at 1.000.
USE_CROSS_EFFICIENCY = True

# 3. Credibility shrinkage toward the role mean. The weight placed on a
#    player's own score is minutes / (minutes + STABILISATION_MINUTES). The
#    stabilisation point is estimated from the data by split-half reliability
#    (see stage C); the value below is the fallback when that estimate cannot
#    be made, and ESTIMATE_STABILISATION turns the estimate off.
ESTIMATE_STABILISATION = True
STABILISATION_MINUTES = 400
SPLIT_HALF_SEED = 20260915
SIM_SPREAD = 0.30          # variation in a player's minutes, as a share of the mean
SIM_REPLICATIONS = 10_000
SIM_SEED = 46290303


# --- shared model construction -------------------------------------------

class SolverError(RuntimeError):
    """Raised when a solve does not reach a proven optimal solution."""


def selection_vars(players):
    """One binary variable per selectable player."""
    return {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in players.index}


def add_structure(prob, x, players):
    """The constraints that hold whatever the goals say.

    Twelve in total: the squad size, the forward count either side, front-row
    cover, and a minimum for each of the eight roles.
    """
    prob += pulp.lpSum(x.values()) == SQUAD_SIZE, "squad_size"

    forwards = pulp.lpSum(
        x[i] for i in players.index if players.loc[i, "role"] in FORWARD_ROLES
    )
    prob += forwards >= FORWARDS_MIN, "forwards_min"
    prob += forwards <= FORWARDS_MAX, "forwards_max"

    prob += pulp.lpSum(
        x[i] for i in players.index if players.loc[i, "role"] in FRONT_ROW_ROLES
    ) >= FRONT_ROW_MIN, "front_row_cover"

    for role, lo in ROLE_MIN.items():
        members = [i for i in players.index if players.loc[i, "role"] == role]
        prob += pulp.lpSum(x[i] for i in members) >= lo, f"min_{role}"

    return prob


def selectable(players):
    """Players who can be chosen at all: classified into a role, and priced."""
    return players[players.role.notna() & players.cost.notna()].reset_index(drop=True)


def picked(players, x):
    """The rows chosen by a solved selection model."""
    return players.loc[[i for i in players.index if x[i].value() > 0.5]]


def solve(prob, label=""):
    """Solve, and refuse to return anything but a proven optimal solution.

    Silently carrying on from an infeasible or unbounded solve is how a model
    comes to report numbers that mean nothing, so this raises instead.
    """
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    name = pulp.LpStatus[status]
    if name != "Optimal":
        raise SolverError(
            f"{label or prob.name}: solver returned {name!r}, not 'Optimal'. "
            f"Check the constraints before trusting any figure from this run."
        )
    return prob


def solver_banner() -> str:
    """One line naming the solver behind the figures in a run."""
    cbc = pulp.PULP_CBC_CMD(msg=False)
    path = getattr(cbc, "path", None) or "bundled CBC"
    return f"solver: CBC via PuLP {pulp.__version__} ({path})"
