"""Stage C: relative efficiency of each squad player within their position.

Data envelopment analysis, with three corrections to the plain CCR model.

The plain model has one input and four outputs, and lets each player choose
the weighting of those outputs that shows him most favourably. With four
outputs and a single input that freedom is close to unlimited: being best in
the position on any one rate is enough to reach the frontier. Applied to
players with very different amounts of playing time it produces a measure
that moves against minutes played, because a short spell is where a freak
rate is most likely. Measured on this squad, the plain score correlates
-0.61 with minutes.

The three corrections, each switchable from config.py so the effect of any
one of them can be shown:

  1. Outputs are normalised by the position's peer mean, then each output's
     share of a player's weighting is held within a band of that position's
     AHP weight. No single measure can carry a whole score any more.
     Normalising first makes the bands meaningful across measures recorded in
     different units, and leaves the unrestricted score unchanged, since DEA
     is invariant to the units of each output.

  2. Every player is scored under every peer's optimal weights as well as his
     own, and the average is taken. Cross-efficiency removes the
     self-flattering weighting and breaks the ties at 1.000.

  3. The score is shrunk toward the position mean by minutes of evidence,
     using minutes / (minutes + K). K is the point at which a player's rate
     is half signal and half noise, estimated from the data by split-half
     reliability rather than asserted.

Peer groups are formed within role and across the competition, since a club
squad holds too few players in any one position to discriminate between them.

Run from the project root:  python src\\04_dea.py
"""

import os
import sys

import numpy as np
import pandas as pd
import pulp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from ahp import measure_weights  # noqa: E402

PROCESSED = cfg.PROCESSED

INPUT = "minutes"
OUTPUTS = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]

# Splits used when estimating the stabilisation point. More splits steady the
# estimate; it converges well before this many.
SPLIT_REPEATS = 50


# --- the efficiency programme --------------------------------------------

def solve_weights(player, peers, bounds):
    """Optimal output weights for one player, in multiplier form.

    Outputs are already normalised, so the weights are comparable across
    measures and `bounds` can restrict each one's share directly.

    Returns the player's own score and the weights that produced it.
    """
    prob = pulp.LpProblem("dea", pulp.LpMaximize)
    u = {r: pulp.LpVariable(f"u_{r}", lowBound=0) for r in OUTPUTS}

    prob += pulp.lpSum(u[r] * player[r] for r in OUTPUTS)

    # With a single input the normalisation fixes the input weight directly,
    # so the usual scaling constraint folds into the peer constraints.
    v = 1.0 / player[INPUT]

    # No peer may be made to look more than fully efficient.
    for _, peer in peers.iterrows():
        prob += (
            pulp.lpSum(u[r] * peer[r] for r in OUTPUTS) <= v * peer[INPUT],
            f"peer_{peer.player_id}",
        )

    # Each measure's share of the weighting stays near its AHP weight. The
    # AHP weights themselves satisfy every band, so this is always feasible.
    if bounds is not None:
        total = pulp.lpSum(u[r] for r in OUTPUTS)
        for r, (lo, hi) in bounds.items():
            prob += u[r] >= lo * total, f"share_min_{r}"
            prob += u[r] <= hi * total, f"share_max_{r}"

    cfg.solve(prob, f"DEA for {player.get('player_id', '?')}")
    score = min(pulp.value(prob.objective) or 0.0, 1.0)
    return score, np.array([u[r].value() or 0.0 for r in OUTPUTS])


def share_bounds(role, weights, tolerance):
    """The band each measure's weighting share must stay inside."""
    if tolerance is None:
        return None
    return {
        r: (w * (1 - tolerance), min(w * (1 + tolerance), 1.0))
        for r, w in weights[role].items()
    }


def role_scores(group, role, scale, weights):
    """Own and cross-efficiency scores for every player in one position.

    `group` is the whole peer set for the role: the league players eligible to
    define the frontier, together with any squad player being evaluated. Every
    member constrains every programme, so each cross-efficiency is bounded by
    one and the comparison is like for like.
    """
    scale = pd.Series(scale).replace(0, np.nan)

    norm = group.copy()
    for r in OUTPUTS:
        norm[r] = (group[r] / scale[r]).fillna(0.0)

    bounds = share_bounds(role, weights, cfg.VIRTUAL_WEIGHT_TOLERANCE)

    own, weight_rows = {}, []
    for _, player in norm.iterrows():
        score, u = solve_weights(player, norm, bounds)
        own[player.player_id] = score
        weight_rows.append(u)

    if not cfg.USE_CROSS_EFFICIENCY:
        return own, None

    # E[j, k] = efficiency of player k judged by player j's weights.
    # With a single input, v_j = 1 / x_j, so E[j, k] = (u_j . y_k) x_j / x_k.
    u_matrix = np.vstack(weight_rows)               # peers x outputs
    y_matrix = norm[OUTPUTS].to_numpy()             # players x outputs
    minutes = norm[INPUT].to_numpy()

    weighted = u_matrix @ y_matrix.T                # peers x players
    ratio = minutes[:, None] / minutes[None, :]     # x_j / x_k
    cross = np.clip(weighted * ratio, 0.0, 1.0)

    mean_cross = cross.mean(axis=0)
    return own, dict(zip(norm.player_id, mean_cross))


# --- how much evidence is a rate worth? ----------------------------------

def composite_rate(frame, weights_by_role, scale_by_role):
    """One per-minute number per player, weighted the way the AHP weights it."""
    out = np.zeros(len(frame))
    for r in OUTPUTS:
        scale = frame.role.map(lambda x: scale_by_role[x][r]).to_numpy()
        w = frame.role.map(lambda x: weights_by_role[x][r]).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            rate = np.where(frame[INPUT] > 0, frame[r] / frame[INPUT], 0.0)
        out += w * np.divide(rate, scale, out=np.zeros_like(rate), where=scale > 0)
    return out


def stabilisation_minutes(appearances, players, weights_by_role, scale_by_role):
    """Minutes at which a player's rate is half signal and half noise.

    Each player's appearances are split at random into two halves and the
    composite rate computed in each. The correlation between the halves is how
    much of a half-sample rate is real. Spearman-Brown then gives K, the
    minutes at which reliability reaches one half, from

        reliability(m) = m / (m + K)

    Returns (K, mean half-sample minutes, half-sample correlation), or None if
    there is not enough data to make the estimate.
    """
    known = players[["player_id", "role"]].dropna(subset=["role"])
    # Only roles whose scale was computed this run can be put on a common
    # footing, so anything else is left out of the estimate.
    known = known[known.role.isin(scale_by_role)]

    usable = appearances[appearances[INPUT] > 0].merge(
        known, on="player_id", how="inner"
    )
    counts = usable.groupby("player_id").size()
    eligible = set(counts[counts >= 4].index)
    usable = usable[usable.player_id.isin(eligible)]
    if len(eligible) < 30:
        return None

    rng = np.random.default_rng(cfg.SPLIT_HALF_SEED)
    correlations, half_minutes = [], []

    for _ in range(SPLIT_REPEATS):
        side = rng.integers(0, 2, size=len(usable))
        halves = []
        for which in (0, 1):
            part = usable[side == which]
            totals = part.groupby(["player_id", "role"], as_index=False)[
                [INPUT, *OUTPUTS]
            ].sum()
            totals["rate"] = composite_rate(totals, weights_by_role, scale_by_role)
            halves.append(totals.set_index("player_id"))

        a, b = halves
        shared = a.index.intersection(b.index)
        # Both halves must carry real playing time for the pair to mean anything.
        shared = shared[(a.loc[shared, INPUT] > 0) & (b.loc[shared, INPUT] > 0)]
        if len(shared) < 30:
            continue

        correlations.append(np.corrcoef(a.loc[shared, "rate"], b.loc[shared, "rate"])[0, 1])
        half_minutes.append(
            pd.concat([a.loc[shared, INPUT], b.loc[shared, INPUT]]).mean()
        )

    if not correlations:
        return None

    r_half = float(np.mean(correlations))
    m_half = float(np.mean(half_minutes))
    if not (0 < r_half < 1):
        return None

    # reliability(m_half) = r_half = m_half / (m_half + K)
    return m_half * (1 - r_half) / r_half, m_half, r_half


# --- stage ----------------------------------------------------------------

def main() -> None:
    print(cfg.solver_banner())
    df = pd.read_parquet(f"{PROCESSED}/players_season.parquet")
    for c in OUTPUTS:
        df[c] = df[c].fillna(0)

    weights = measure_weights()
    squad = df[df.in_squad & df.role.notna()].copy()

    tol = cfg.VIRTUAL_WEIGHT_TOLERANCE
    restriction = (
        f"each share within +/-{tol:.0%} of its AHP weight"
        if tol is not None else "none (plain CCR)"
    )
    print(f"weight restrictions: {restriction}")
    print(f"cross-efficiency:    {'on' if cfg.USE_CROSS_EFFICIENCY else 'off'}")
    print(f"scoring {len(squad)} squad players")
    print()

    own_scores, cross_scores, scales = {}, {}, {}
    league_mean, league_corr = {}, []

    for role, group in squad.groupby("role"):
        peers = df[(df.role == role) & df.frontier & (df[INPUT] > 0)]
        # Every evaluated player belongs to the set that constrains it.
        pool = pd.concat(
            [peers, group[~group.player_id.isin(set(peers.player_id))]],
            ignore_index=True,
        )
        scales[role] = pool[OUTPUTS].mean().to_dict()

        print(f"  {role:<14} peer set {len(pool):>3}", end="", flush=True)
        own, cross = role_scores(pool, role, scales[role], weights)
        own_scores.update(own)
        if cross:
            cross_scores.update(cross)

        # What a typical player in this position manages across the league,
        # counting only those with enough appearances to be worth believing.
        # A thin-evidence player is shrunk toward this rather than toward the
        # club's own average, which the same thin-evidence players inflate.
        scored = cross if cross else own
        established = pool[pool.frontier]
        values = established.player_id.map(scored).dropna()
        league_mean[role] = float(values.mean())
        league_corr.append(
            pd.DataFrame({
                "minutes": established.set_index("player_id")[INPUT],
                "score": established.player_id.map(scored).to_numpy(),
            })
        )

        on_front = sum(1 for p in group.player_id if own.get(p, 0) >= 0.9999)
        print(f"   fully efficient {on_front}/{len(group)}"
              f"   league mean {league_mean[role]:.3f}")

    squad["efficiency_own"] = squad.player_id.map(own_scores)
    squad["efficiency_cross"] = (
        squad.player_id.map(cross_scores) if cross_scores else np.nan
    )
    raw = squad.efficiency_cross if cross_scores else squad.efficiency_own
    squad["efficiency_raw"] = raw

    # --- shrink toward the role mean by minutes of evidence ---------------
    k = cfg.STABILISATION_MINUTES
    note = f"assumed {k:,.0f}"
    if cfg.ESTIMATE_STABILISATION:
        path = f"{PROCESSED}/player_appearances.parquet"
        if os.path.exists(path):
            est = stabilisation_minutes(
                pd.read_parquet(path), df, weights, scales
            )
            if est is not None:
                k, m_half, r_half = est
                note = (f"estimated {k:,.0f} from split-half reliability "
                        f"{r_half:.2f} at {m_half:,.0f} half-sample minutes")
        else:
            note += " (no appearance table; run stage 03 first)"

    print()
    print(f"stabilisation point: {note}")

    weight = squad.minutes / (squad.minutes + k)
    baseline = squad.role.map(league_mean)
    squad["evidence"] = weight
    squad["league_baseline"] = baseline
    squad["efficiency"] = weight * squad.efficiency_raw + (1 - weight) * baseline

    league = pd.concat(league_corr, ignore_index=True).dropna()
    print(f"shrinking toward the league average for the position, across "
          f"{len(league)} established players")
    print(f"  that reference set's own minutes bias: "
          f"corr {league.minutes.corr(league.score):+.3f}")

    squad.to_parquet(f"{PROCESSED}/squad_efficiency.parquet")

    # --- checkpoint --------------------------------------------------------
    print()
    print("--- checkpoint ---")
    print(f"scored:           {squad.efficiency.notna().sum()}")
    print(f"mean efficiency:  {squad.efficiency.mean():.3f}")
    print(f"range:            {squad.efficiency.min():.3f} "
          f"to {squad.efficiency.max():.3f}")
    print()
    print("does the measure still reward not playing?")
    for label, col in [
        ("own weights only (plain CCR)", "efficiency_own"),
        ("cross-efficiency", "efficiency_cross"),
        ("after shrinkage (used downstream)", "efficiency"),
    ]:
        if squad[col].notna().any():
            r = squad.minutes.corr(squad[col])
            ties = int((squad[col] >= 0.9999).sum())
            print(f"  {label:<36} corr with minutes {r:+.3f}   "
                  f"tied at 1.000: {ties}")
    print()
    cols = ["name", "role", "appearances", "minutes",
            "efficiency_own", "efficiency_cross", "evidence", "efficiency"]
    print("most efficient:")
    print(squad.nlargest(8, "efficiency")[cols].round(3).to_string(index=False))
    print()
    print("least efficient:")
    print(squad.nsmallest(5, "efficiency")[cols].round(3).to_string(index=False))
    print()
    print("thinnest evidence:")
    print(squad.nsmallest(5, "minutes")[cols].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
