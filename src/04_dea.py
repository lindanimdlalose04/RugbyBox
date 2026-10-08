"""Stage C: relative efficiency of each squad player within their position.

One linear programme per player. Each player is free to choose the weighting of
measures that shows them most favourably, subject to that weighting not making
any player in the peer group appear more than fully efficient. The resulting
score is bounded by 1, and a player scoring 1 lies on the efficiency frontier.

Peer groups are formed within role and across the competition, since a club
squad holds too few players in any one position to discriminate between them.

Run from the project root:  python src\\04_dea.py
"""

import pandas as pd
import pulp

PROCESSED = "data/processed"

INPUT = "minutes"
OUTPUTS = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]
# Minutes of evidence required before a player's own rate is taken at face
# value. Below this, the score is blended toward the role average in
# proportion to the evidence available, since a rate computed from one
# appearance is largely noise. A stated assumption, tested by sensitivity.
QUALIFYING_MINUTES = 240

def efficiency(player, peers: pd.DataFrame) -> float:
    """Relative efficiency of one player against their peer group."""
    if player[INPUT] <= 0:
        return float("nan")

    prob = pulp.LpProblem("dea", pulp.LpMaximize)
    u = {r: pulp.LpVariable(f"u_{r}", lowBound=0) for r in OUTPUTS}

    # Weighted output of the player under evaluation.
    prob += pulp.lpSum(u[r] * player[r] for r in OUTPUTS)

    # With a single input the normalisation fixes the input weight directly,
    # so the usual scaling constraint is folded into the peer constraints.
    v = 1.0 / player[INPUT]

    # No peer may be made to look more than fully efficient.
    for _, peer in peers.iterrows():
        if peer[INPUT] <= 0:
            continue
        prob += (
            pulp.lpSum(u[r] * peer[r] for r in OUTPUTS) <= v * peer[INPUT],
            f"peer_{peer.player_id}",
        )

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        return float("nan")
    return min(pulp.value(prob.objective) or 0.0, 1.0)


def main() -> None:
    df = pd.read_parquet(f"{PROCESSED}/players_season.parquet")
    for c in OUTPUTS:
        df[c] = df[c].fillna(0)

    squad = df[df.in_squad & df.role.notna()].copy()
    print(f"scoring {len(squad)} squad players")
    print()

    scores = {}
    for role, group in squad.groupby("role"):
        peers = df[(df.role == role) & df.frontier & (df[INPUT] > 0)]
        # The player under evaluation always constrains their own problem.
        print(f"  {role:<14} peer group {len(peers):>3}", end="")
        for _, player in group.iterrows():
            ref = peers
            if player.player_id not in set(peers.player_id):
                ref = pd.concat([peers, player.to_frame().T], ignore_index=True)
            scores[player.player_id] = efficiency(player, ref)
        on_front = sum(
            1 for p in group.player_id if scores.get(p, 0) >= 0.9999
        )
        print(f"   efficient {on_front}/{len(group)}")

    squad["efficiency_raw"] = squad.player_id.map(scores)

    # Blend toward the role average in proportion to minutes of evidence.
    weight = (squad.minutes / QUALIFYING_MINUTES).clip(upper=1.0)
    role_mean = squad.groupby("role").efficiency_raw.transform("mean")
    squad["efficiency"] = weight * squad.efficiency_raw + (1 - weight) * role_mean

    squad.to_parquet(f"{PROCESSED}/squad_efficiency.parquet")

    print()
    print("--- checkpoint ---")
    print(f"scored:           {squad.efficiency.notna().sum()}")
    print(f"on the frontier:  {(squad.efficiency >= 0.9999).sum()}")
    print(f"mean efficiency:  {squad.efficiency.mean():.3f}")
    print(f"range:            {squad.efficiency.min():.3f} to {squad.efficiency.max():.3f}")
    print()
    cols = ["name", "role", "appearances", "minutes", "efficiency_raw", "efficiency"]
    print("most efficient:")
    print(squad.nlargest(8, "efficiency")[cols].to_string(index=False))
    print()
    print("least efficient:")
    print(squad.nsmallest(5, "efficiency")[cols].to_string(index=False))


if __name__ == "__main__":
    main()