"""Stage H: test how reliably the workload promise holds.

The selection assumes each player will be used roughly as they have been.
Match involvement is uncertain, so the fixture is played out many times with
minutes drawn at random around each player's recent average, and the share of
outcomes that breach the workload target is reported.

Run from the project root:  python src\\08_simulate.py
"""

import numpy as np
import pandas as pd

PROCESSED = "data/processed"
TARGET_WORKLOAD = 2875
REPLICATIONS = 10_000
SPREAD = 0.30          # how much a player's minutes vary, as a share of the mean
SEED = 46290303


def simulate(squad: pd.DataFrame, label: str, rng) -> None:
    mean = squad.workload.to_numpy()
    # Minutes vary around the recent average, never below zero.
    draws = rng.normal(mean, mean * SPREAD, size=(REPLICATIONS, len(mean)))
    totals = np.clip(draws, 0, None).sum(axis=1)

    breaches = (totals > TARGET_WORKLOAD).mean()
    print(f"=== {label} ===")
    print(f"planned workload     {squad.workload.sum():,.0f}")
    print(f"average simulated    {totals.mean():,.0f}")
    print(f"5th to 95th          {np.percentile(totals, 5):,.0f} "
          f"to {np.percentile(totals, 95):,.0f}")
    print(f"breaches the target  {breaches * 100:.1f}% of the time")
    print()


def main() -> None:
    rng = np.random.default_rng(SEED)
    for name, label in [
        ("squad_weighted", "weighted squad"),
        ("squad_preemptive", "pre-emptive squad"),
    ]:
        squad = pd.read_csv(f"{PROCESSED}/{name}.csv")
        simulate(squad, label, rng)

    print(f"{REPLICATIONS:,} replications, minutes varying by {SPREAD:.0%} "
          f"around each player's recent average")


if __name__ == "__main__":
    main()