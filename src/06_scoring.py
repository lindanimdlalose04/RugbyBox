"""Stage E and F: scoring model, and the composite value used for selection.

The efficiency score from stage C measures output per minute, which favours
players used sparingly. The scoring model measures total output across the
season, which favours regular starters. Each measure is expressed as a
fraction of the best total in that position across the competition, then
weighted by the position weights from stage D.

The two are blended into a single selection value. ALPHA controls the
balance and is a stated assumption tested by sensitivity analysis.

Run from the project root:  python src\\06_scoring.py
"""

import json
import os

import numpy as np
import pandas as pd

PROCESSED = "data/processed"
MEASURES = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]

# Weight on efficiency against volume. 0 is volume only, 1 is efficiency only.
ALPHA = 0.35


def main() -> None:
    league = pd.read_parquet(f"{PROCESSED}/players_season.parquet")
    squad = pd.read_parquet(f"{PROCESSED}/squad_efficiency.parquet")
    weights = json.load(open(f"{PROCESSED}/weights.json"))["criteria"]

    for c in MEASURES:
        league[c] = league[c].fillna(0)
        squad[c] = squad[c].fillna(0)

    # Best season total in each position, taken across the competition.
    bench = league[league.frontier].groupby("role")[MEASURES].max()

    # Each measure as a fraction of that best, then weighted and summed.
    score = pd.Series(0.0, index=squad.index)
    for measure in MEASURES:
        best = squad.role.map(bench[measure]).replace(0, np.nan)
        fraction = (squad[measure] / best).clip(upper=1.0).fillna(0)
        weight = squad.role.map({r: w[measure] for r, w in weights.items()})
        score += fraction * weight

    squad["score"] = score
    squad["value"] = ALPHA * squad.efficiency + (1 - ALPHA) * squad.score

    squad.to_parquet(f"{PROCESSED}/squad_value.parquet")
    squad.to_csv(f"{PROCESSED}/squad_value.csv", index=False)

    # --- how the two views compare -------------------------------------
    squad["rank_efficiency"] = squad.efficiency.rank(ascending=False)
    squad["rank_score"] = squad.score.rank(ascending=False)
    squad["rank_gap"] = squad.rank_efficiency - squad.rank_score

    print("--- checkpoint ---")
    print(f"players valued:  {len(squad)}")
    print(f"score range:     {squad.score.min():.3f} to {squad.score.max():.3f}")
    print(f"value range:     {squad.value.min():.3f} to {squad.value.max():.3f}")
    corr = squad.efficiency.corr(squad.score)
    print(f"efficiency vs score correlation: {corr:.3f}")
    print()

    cols = ["name", "role", "appearances", "efficiency", "score", "value"]
    print("highest total contribution (scoring model):")
    print(squad.nlargest(8, "score")[cols].round(3).to_string(index=False))
    print()
    print("highest blended value (what the selection will use):")
    print(squad.nlargest(8, "value")[cols].round(3).to_string(index=False))
    print()
    print("biggest disagreements between the two views:")
    gap = squad.reindex(squad.rank_gap.abs().sort_values(ascending=False).index)
    print(gap.head(6)[cols + ["rank_gap"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()