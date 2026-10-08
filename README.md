# RugbyBox

Multi-criteria selection of a rugby matchday squad under competing
performance, workload and budget goals.

ITRI 628 Decision Support Systems, North-West University.

## The problem

A Gallagher Premiership club must name a matchday 23 from its available
squad. The selection is constrained by the laws of the game, which fix the
positional composition and require trained front-row cover, and pulled in
three directions by the coaching staff: field the strongest side, hold
accumulated player workload below a safe ceiling, and stay inside the
matchday wage budget. No squad satisfies all three.

## Approach

Five methods, each feeding the next.

| Stage | Method | Produces |
|---|---|---|
| 1 | Data envelopment analysis | Efficiency of each player within their position |
| 2 | Analytic hierarchy process | Goal weights and per-position measure weights |
| 3 | Scoring model | An independent ranking, cross-checked against the efficiency ranking |
| 4 | Goal programming | The matchday 23, solved weighted and pre-emptive |
| 5 | Monte Carlo simulation | How reliably the workload goal holds under uncertain match involvement |

## Running it

Requires Python 3.11+.

    pip install pandas pyarrow numpy pulp openpyxl

    python src/01_fetch_squad.py     # club squad pool for the season
    python src/02_fetch_league.py    # league-wide comparison set (~15 min)
    python src/03_clean.py           # modelling table
    python src/04_dea.py             # efficiency scores
    python src/05_ahp.py             # weights

Diagnostics, run as needed:

    python src/check_access.py       # confirms the data store is reachable
    python src/check_feasibility.py  # bounds each goal's achievable range

## Notes on the data

Match records come from the rugbydata parquet store that backs the
`rugbypy` package (Apache-2.0). The files are read directly from the store
rather than through the package, so that the fetch is explicit and
reproducible.

Two measures are derived rather than recorded. Minutes played is absent for
roughly half of all appearances and is reconstructed from carries divided by
the recorded per-minute carrying rate; validated against the subset where
both are present, mean absolute error is 2.5 minutes. Individual salary is
not published and is modelled from position averages in the Premiership
Rugby salary cap report, scaled by each player's share of playing time.

## Known limitations

- The efficiency measure covers carrying, defensive and breakdown
  contribution per minute. It does not cover distribution, so it
  systematically understates half-backs and set-piece specialists.
- Salary data is from the 2022/23 season and is applied to a 2025-26 squad.
- Three squad players never appeared in a specialist position and are
  excluded from selection.

## Acknowledgements

Match data: [rugbypy](https://github.com/seanyboi/rugbypy), Apache-2.0.
