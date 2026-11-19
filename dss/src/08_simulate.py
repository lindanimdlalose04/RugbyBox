"""Stage H: test how reliably the workload promise holds.

The selection assumes each player will be used roughly as they have been.
Match involvement is uncertain, so the fixture is played out many times with
minutes drawn at random around each player's recent average, and the share of
outcomes that breach the workload target is reported.

Read the breach rate with care. The goal programme deliberately pushes
workload up against its target, so a symmetric spread around the resulting
plan will breach it roughly half the time almost regardless of how wide that
spread is. The figure therefore says more about the plan sitting on the
ceiling than about how volatile match involvement really is. SPREAD_SWEEP
re-runs the same squad across a range of assumptions so that sensitivity is
visible rather than implied.

Run from the project root:  python src\\08_simulate.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402

# Spreads re-run for the sensitivity table, as a share of each player's mean.
SPREAD_SWEEP = (0.05, 0.15, cfg.SIM_SPREAD, 0.60)


def totals(mean: np.ndarray, spread: float, rng) -> np.ndarray:
    """Simulated squad workload totals, minutes never falling below zero."""
    draws = rng.normal(mean, mean * spread, size=(cfg.SIM_REPLICATIONS, len(mean)))
    return np.clip(draws, 0, None).sum(axis=1)


def simulate(squad: pd.DataFrame, label: str, seed: int) -> None:
    mean = squad.workload.to_numpy()

    # Each squad is simulated from its own generator seeded identically, so
    # the two are compared under common random numbers rather than under
    # whatever draws happened to come next in a shared stream.
    sims = totals(mean, cfg.SIM_SPREAD, np.random.default_rng(seed))
    breaches = (sims > cfg.TARGET_WORKLOAD).mean()

    print(f"=== {label} ===")
    print(f"planned workload     {squad.workload.sum():,.0f}")
    print(f"target               {cfg.TARGET_WORKLOAD:,}")
    print(f"average simulated    {sims.mean():,.0f}")
    print(f"5th to 95th          {np.percentile(sims, 5):,.0f} "
          f"to {np.percentile(sims, 95):,.0f}")
    print(f"breaches the target  {breaches * 100:.1f}% of the time")
    print()
    print("  how much does that depend on the spread assumption?")
    for spread in SPREAD_SWEEP:
        s = totals(mean, spread, np.random.default_rng(seed))
        mark = "  <- as configured" if spread == cfg.SIM_SPREAD else ""
        print(f"    spread {spread:>5.0%}   sd of total {s.std():>6,.0f}   "
              f"breaches {(s > cfg.TARGET_WORKLOAD).mean() * 100:>5.1f}%{mark}")
    print()


def main() -> None:
    for name, label in [
        ("squad_weighted", "weighted squad"),
        ("squad_preemptive", "pre-emptive squad"),
    ]:
        simulate(pd.read_csv(f"{cfg.PROCESSED}/{name}.csv"), label, cfg.SIM_SEED)

    print(f"{cfg.SIM_REPLICATIONS:,} replications, minutes varying by "
          f"{cfg.SIM_SPREAD:.0%} around each player's recent average")


if __name__ == "__main__":
    main()
