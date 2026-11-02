# RugbyBox

Multi-criteria selection of a rugby matchday squad under competing
performance, workload and budget goals.

ITRI 628 Decision Support Systems, North-West University, 2026.

## The problem

A Gallagher Premiership club must name a matchday 23 from its available
squad. The laws of the game fix the positional make-up of the squad and
require trained front-row cover. The coaching staff then pull the selection
in three directions: field the strongest side, keep accumulated player
workload below a safe ceiling, and stay inside the matchday wage budget. No
squad satisfies all three, so the real decision is which shortfalls to
accept, and in what order.

## Results at a glance

The model does not say which squad is best. It prices the choice.

| Goal | Target | Weighted squad | Pre-emptive squad |
|---|---|---|---|
| Performance | 11.10 | 11.02 (short by 0.08) | 11.11 (met) |
| Workload | 2 875 min | 2 868 min (met) | 2 871 min (met) |
| Cost | £130 000 | £134 410 (over by £4 410) | £150 352 (over by £20 352) |

- **The price of the last bit of strength.** Insisting on the performance
  target (the pre-emptive squad) costs an extra £15 941, which is 12.3% of
  the matchday budget, for a 0.8% gain in squad strength. On that evidence
  the weighted squad is the better buy.
- **Where the conflict starts.** Holding workload and budget as hard limits,
  the best achievable performance is 10.85. Any target above that forces a
  sacrifice on one of the other two goals.
- **The workload promise is fragile.** Both squads sit only a few minutes
  under the workload ceiling on paper. Over 10 000 simulated matches, with
  each player's minutes varying around his recent average, the weighted
  squad breaches the ceiling 48% of the time. The headroom is not real
  protection.
- **The two squads share 19 of 23 players.** The pre-emptive run swaps Joe
  Cokanasiga, Sam Underhill, Will Butt and Will Jeanes for Tom de Glanville,
  Beno Obano, Ollie Lawrence and Ross Molony.

### Recommended squad (weighted)

| Position | Players |
|---|---|
| Props (4) | Thomas du Toit, Archie Griffin, Francois van Wyk, Billy Sela |
| Hookers (2) | Dan Frost, Tom Dunn |
| Locks (3) | Ewan Richards, Quinn Roux, Will Jeanes |
| Loose forwards (5) | Miles Reid, Alfie Barbeary, Sam Underhill, Guy Pepper, Arthur Green |
| Scrumhalves (2) | Bernard van der Linde, Tom Carr-Smith |
| Flyhalves (2) | Finn Russell, Ciaran Donoghue |
| Centres (2) | Cameron Redpath, Will Butt |
| Back three (3) | Henry Arundell, Santiago Carreras, Joe Cokanasiga |

Fourteen forwards and nine backs (a six-two bench split), with all twelve
hard constraints satisfied.

## Approach

Five methods, each feeding the next.

| Stage | Method | Produces |
|---|---|---|
| 1 | Data envelopment analysis | Efficiency of each player against every player in his position across the league |
| 2 | Analytic hierarchy process | Goal weights (performance 0.648, workload 0.230, cost 0.122) and per-position measure weights, all with consistency ratios well under 0.10 |
| 3 | Scoring model | A volume-based ranking, blended with efficiency into one selection value |
| 4 | Goal programming | The matchday 23 as a binary goal programme, solved weighted and pre-emptive |
| 5 | Monte Carlo simulation | How reliably the workload goal holds when match involvement is uncertain |

Efficiency (output per minute) and the scoring model (total output across
the season) deliberately measure different things: the correlation between
them across the 41-player pool is -0.15. Dan Frost tops both, which is why he
has the highest selection value in the pool.

## Two builds of the same model

The models were built and solved in Excel with Solver
(`model/Rugby-Box_Solver.xlsx`, one sheet per stage) and solved a second
time, independently, in Python with PuLP and the CBC solver.

The pre-emptive results agree exactly. The weighted results do not: CBC
finds a squad with a lower weighted objective (0.0087 against Excel's
0.0090), swapping Beno Obano for Sam Underhill and coming in about £4 100
cheaper. Excel Solver most likely stopped early under its integer
optimality tolerance. The figures above are the Python results, because they
are the better solution and anyone can reproduce them from this repository.

## Running it

Requires Python 3.11+.

    pip install pandas pyarrow numpy "pulp<3" openpyxl

Run from the project root, in order:

    python src/01_fetch_squad.py       # club squad pool for the season
    python src/02_fetch_league.py      # league-wide comparison set (~15 min)
    python src/03_clean.py             # modelling table
    python src/04_dea.py               # efficiency scores
    python src/05_ahp.py               # goal and measure weights
    python src/06_scoring.py           # scoring model and selection value
    python src/07_goal_programme.py    # weighted and pre-emptive squads
    python src/08_simulate.py          # workload simulation

The processed data is committed, so stages 04 to 08 run without fetching
anything. Only the per-player fetch cache (`data/raw/players/`) is left out.

Diagnostics, run as needed:

    python src/check_access.py        # confirms the data store is reachable
    python src/check_feasibility.py   # achievable range of each goal
    python src/check_conflict.py      # the performance level where the goals start to conflict

Excel helpers (write the inputs the Solver workbook needs):

    python src/export_data.py         # one position's DEA peer group
    python src/export_scoring.py      # season totals and positional bests

## Notes on the data

Match records come from the rugbydata parquet store that backs the
`rugbypy` package (Apache-2.0). The files are read directly from the store
rather than through the package, so the fetch is explicit and reproducible.

Two measures are derived rather than recorded:

- **Minutes played** is missing for roughly half of all appearances. It is
  rebuilt from carries divided by the recorded per-minute carrying rate.
  Checked against the appearances where both are present, the mean absolute
  error is 2.5 minutes.
- **Individual salary** is not published. It is modelled from position
  averages in the Premiership Rugby salary cap report, scaled by each
  player's share of playing time.

## Known limitations

- The efficiency measure covers carrying, defensive and breakdown
  contribution per minute. It does not cover distribution, so it
  systematically understates half-backs and set-piece specialists.
- Salary data is from the 2022/23 season and is applied to a 2025-26 squad.
- Three squad players never appeared in a specialist position and are
  excluded from selection.
- The simulation varies each player's minutes independently. In reality a
  heavy game for one player often means a light one for his replacement, so
  the true breach risk may be somewhat lower.

## Acknowledgements

Match data: [rugbypy](https://github.com/seanyboi/rugbypy), Apache-2.0.
Methods follow Taylor, *Introduction to Management Science*, 13th edition.
