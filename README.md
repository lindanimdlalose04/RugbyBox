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
| Performance | 9.95 | 9.96 (met) | 9.96 (met) |
| Workload | 2 875 min | 2 855 min (met) | 2 855 min (met) |
| Cost | £130 000 | £141 875 (over by £11 875) | £141 875 (over by £11 875) |

- **The conflict lands entirely on the budget.** Performance and workload can
  both be met. Neither can be met inside £130 000, so the squad overspends by
  £11 875, which is 9.1% of the matchday budget. That is the price of this
  fixture, and it is the whole decision.
- **The two methods agree completely.** Weighted and pre-emptive return the
  same 23 players. Cost carries the lowest goal weight and is also the last
  pre-emptive priority, so both approaches sacrifice the same goal. When the
  ordering and the weighting point the same way, the choice between the two
  formulations does not matter, which is itself worth knowing.
- **Where the conflict starts.** Holding workload and budget as hard limits,
  the best achievable performance is 9.58. Any target above that forces a
  sacrifice on one of the other two goals. The target of 9.95 is set 42% of
  the way from that breaking point to the unconstrained best of 10.46.
- **The workload promise is fragile.** Both squads sit only a few minutes
  under the workload ceiling on paper. Over 10 000 simulated matches, with
  each player's minutes varying around his recent average, the weighted
  squad breaches the ceiling 48% of the time. The headroom is not real
  protection. Read that figure for what it is: the goal programme pushes
  workload up against its target by design, so a symmetric spread around the
  resulting plan breaches it roughly half the time almost regardless of how
  wide the spread is. Stage H now reports the same squad across four spread
  assumptions, from 5% to 60%, and the breach rate only moves from 42% to
  53%. The simulation confirms that the plan has no real margin; it does not
  measure how volatile match involvement actually is.
### Recommended squad

| Position | Players |
|---|---|
| Props (5) | Thomas du Toit, Beno Obano, Archie Griffin, Francois van Wyk, Billy Sela |
| Hookers (2) | Dan Frost, Tom Dunn |
| Locks (3) | Ewan Richards, Quinn Roux, Will Jeanes |
| Loose forwards (4) | Miles Reid, Alfie Barbeary, Sam Underhill, Guy Pepper |
| Scrumhalves (2) | Tom Carr-Smith, Bernard van der Linde |
| Flyhalves (2) | Finn Russell, Ciaran Donoghue |
| Centres (2) | Louie Hennessey, Cameron Redpath |
| Back three (3) | Henry Arundell, Santiago Carreras, Tom de Glanville |

Fourteen forwards and nine backs (a six-two bench split), with all twelve
hard constraints satisfied.

Will Jeanes is worth a word, because he is the one selection that cannot be
justified on form. He has a single appearance behind him. The model no longer
claims he is good: stage C shrinks his score to 0.605, which is the average
for a lock across the league, because 52 minutes is not evidence of anything.
He is picked as the third lock at £3 232, half the price of the next cheapest,
on a squad that is already £11 875 over budget. That is cheap cover rather
than a judgement on the player, and a coach can accept or overrule it knowing
exactly which it is. In the earlier version of this model he reached the
frontier outright at 1.000 and was selected as though he were elite.

## Approach

Five methods, each feeding the next.

| Stage | Method | Produces |
|---|---|---|
| 1 | Data envelopment analysis | Efficiency of each player against every player in his position across the league, with restricted weights, cross-efficiency and shrinkage by evidence |
| 2 | Analytic hierarchy process | Goal weights (performance 0.648, workload 0.230, cost 0.122) and per-position measure weights, all with consistency ratios well under 0.10 |
| 3 | Scoring model | A volume-based ranking, blended with efficiency into one selection value |
| 4 | Goal programming | The matchday 23 as a binary goal programme, solved weighted and pre-emptive |
| 5 | Monte Carlo simulation | How reliably the workload goal holds when match involvement is uncertain |

Efficiency (output per minute) and the scoring model (total output across
the season) deliberately measure different things: the correlation between
them across the 41-player pool is -0.04. Dan Frost tops both, which is why he
has the highest selection value in the pool.

### How the efficiency measure is kept honest

A plain CCR programme with one input and four outputs lets every player
choose the weighting that shows him best. With that much freedom, being top
of the position on any single rate is enough to reach the frontier, and the
shortest spells are where a freak rate is most likely. The first version of
this model put five of 41 players on the frontier at exactly 1.000, four of
them with under 240 minutes, and its scores correlated -0.61 with minutes
played. Three corrections now sit on top of the programme, each switchable
from `src/config.py` so its effect can be shown rather than asserted.

1. **Restricted weights.** Outputs are first normalised by the position's
   peer mean, which puts measures recorded in metres and in counts on one
   scale without changing any score, since DEA is invariant to units. Each
   measure's share of the weighting is then held within 50% of that
   position's AHP weight. No single measure can carry a whole score. This is
   also what finally connects stage D to stage C: the AHP weights now shape
   the efficiency measure rather than only the scoring model.
2. **Cross-efficiency.** Every player is scored under every peer's optimal
   weights as well as his own, and the average is taken. This removes the
   self-flattering weighting and leaves no ties: all 41 scores are now
   distinct, against five tied at 1.000 before.
3. **Shrinkage by evidence.** A score is blended toward the league average
   for the position by `minutes / (minutes + K)`. K is the point at which a
   player's rate is half signal and half noise, estimated from the data by
   split-half reliability rather than asserted: splitting each player's
   appearances at random gives a half-sample correlation of 0.38 at 303
   minutes, so K is 500 minutes. The target is the league average rather
   than the club's own, because the club's average is inflated by the same
   thin-evidence players the shrinkage is meant to correct.

What this did and did not fix is worth stating plainly. The weighting
problem is solved: the ties are gone and no measure can dominate. The
small-sample inflation is solved: a one-appearance player now sits at the
league average for his position instead of on the frontier. What remains is
a correlation of -0.45 between minutes and efficiency, and that one is not an
artefact. The squad's raw per-minute rates already correlate -0.54 with
minutes before any DEA is applied, while the same measure across 345
established league players correlates -0.07. In other words this squad's
heavily used players really do produce less per minute than its fringe
players, and the measure is reporting that rather than inventing it.

## Two builds of the same model

The models were built and solved in Excel with Solver
(`model/Rugby-Box_Solver.xlsx`, one sheet per stage) and solved a second
time, independently, in Python with PuLP and the CBC solver.

On the original efficiency measure the two builds were compared directly.
The pre-emptive results agreed exactly. The weighted results did not: CBC
found a squad with a lower weighted objective (0.0087 against Excel's
0.0090), swapping Beno Obano for Sam Underhill and coming in about £4 100
cheaper. Excel Solver most likely stopped early under its integer optimality
tolerance.

That comparison is a record of the first build. The original workbook is
kept as `model/Rugby-Box_Solver_first_build.xlsx`.

When stage C was revised, the workbook silently fell out of step: it still
held the plain CCR scores, so the two builds were solving different problems
while appearing to agree. That is the hazard of filling a workbook by hand
from exported figures. It is now filled from the pipeline instead, with

    python src/export_excel.py

which writes the Data, DEA, both goal programming and Simulation sheets, and
rewrites the Solver model on the DEA sheet for the restricted-weight
programme. The AHP sheet is untouched because the judgements have not
changed, and the Scoring sheet is untouched because its positional bests
come from the same data and its measure weights already read live from the
AHP sheet.

Three tests in `tests/test_workbook.py` now check that the workbook agrees
with the pipeline: the same players and figures on the Data sheet, the same
goal targets, the same selected 23, and a DEA sheet whose weights respect
their bands and reproduce a fresh solve. Drift of the kind described above
fails the suite rather than going unnoticed.

The workbook opens on the solution rather than on a blank sheet, so the goal
sheets already show the squad in the table above. Running Solver should
confirm those numbers rather than change them. What the workbook does not
do is cross-efficiency: that needs one linear programme per player across
the whole league, which is reasonable in Python and not in Excel. The DEA
sheet demonstrates the restricted-weight programme for a single player, and
the efficiency figures on the Data sheet come from the pipeline.

## Running it

Requires Python 3.11+.

    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt

Versions are pinned, because the results depend on them: the weighted
solution below differs between Excel Solver and CBC, so the solver behind a
figure is part of the figure. Every stage that solves anything prints the
solver it used as its first line.

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

Excel workbook, run after stage 07:

    python src/export_excel.py        # fill the Solver workbook from the pipeline

Two smaller helpers write the same figures to CSV, for reading outside Excel:

    python src/export_data.py         # one position's DEA peer group
    python src/export_scoring.py      # season totals and positional bests

Tests:

    .venv\Scripts\pytest

They check the things that would otherwise break in silence: that both solved
squads satisfy all twelve structural constraints, that the derived minutes
hold to the 2.3 minute accuracy claimed below, that the cost model really
does preserve each published position average, that the AHP arithmetic
matches a matrix worked by hand, that the restricted efficiency weights stay
inside their bands and no peer is made to look more than fully efficient,
that the pre-emptive run never buys a lower priority at the expense of a
higher one, and that the Excel workbook still agrees with the pipeline.

`src/config.py` holds the squad structure, the three goal targets and every
stated assumption. Change a constraint there and the goal programme and both
diagnostics move together; they previously held separate copies.

## Notes on the data

Match records come from the rugbydata parquet store that backs the
`rugbypy` package (Apache-2.0). The files are read directly from the store
rather than through the package, so the fetch is explicit and reproducible.

Two measures are derived rather than recorded:

- **Minutes played** is missing for roughly half of all appearances. It is
  rebuilt from carries divided by the recorded per-minute carrying rate.
  Checked against the appearances inside the season window where both are
  present, the mean absolute error is 2.3 minutes. Reconstruction only ever
  runs on rows inside that window; across every season held in the raw file
  the same check gives 3.0 minutes.
- **Individual salary** is not published. It is modelled from position
  averages in the Premiership Rugby salary cap report, scaled by each
  player's share of playing time.

## Known limitations

- The efficiency measure covers carrying, defensive and breakdown
  contribution per minute. It does not cover distribution, so it
  systematically understates half-backs and set-piece specialists.
- A player with very few minutes is still scored, just conservatively. The
  shrinkage places him at the league average for his position, which is an
  assumption, not a measurement: it says only that nothing is known about
  him. The `evidence` column records how much of each score is the player's
  own, and anything below about 0.25 should be read as a placeholder.
- The three corrections in stage C address the weighting and the sample
  size. They do not give a confidence interval. Bootstrapping the scores
  would put an honest band around each one and is the natural next step.
- The efficiency measure and the scoring model are blended with a fixed
  ALPHA of 0.35. That weighting is a judgement and has not been tested by
  sensitivity analysis.
- Salary data is from the 2022/23 season and is applied to a 2025-26 squad.
- Three squad players never appeared in a specialist position and are
  excluded from selection.
- The simulation varies each player's minutes independently. In reality a
  heavy game for one player often means a light one for his replacement, so
  the true breach risk may be somewhat lower.

## Acknowledgements

Match data: [rugbypy](https://github.com/seanyboi/rugbypy), Apache-2.0.
Methods follow Taylor, *Introduction to Management Science*, 13th edition.
