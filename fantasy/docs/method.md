# Method

Three problems, solved in order. Each is written up here as it is built.

## 1. Projecting points

**Status: built, in `src/03_project.py`.**

Historical appearances are converted into fantasy points by the rules, then
turned into a forecast of the next gameweek. The forecast is kept as three
separate numbers, because they answer different questions and fail in
different ways.

**Points per appearance** is what a player scores when he plays. A mean over
two appearances is mostly noise, so it is shrunk toward what a typical player
in that position manages:

    projection = w * his own mean + (1 - w) * position baseline
    w          = appearances / (appearances + K)

K is the number of appearances at which a record is half signal and half
noise. It is estimated rather than asserted, by splitting each player's
appearances at random into two halves and correlating the mean of one against
the other. On this competition the halves correlate 0.57 at 5.6 appearances
each, which puts K at 4.3.

The baseline is taken only from players with six or more appearances. A
baseline set by the same thin records it is meant to correct would not
correct anything, which is the error RugbyBox made in shrinking toward a club
average inflated by its own fringe players.

**Availability** is how often he plays at all, as a share of his club's
fixtures rather than the competition's, since clubs have played different
numbers of games.

**Projected points** is the two multiplied.

Keeping them apart matters. A replacement who scores well in twenty minutes
has a high rate and low availability, and a squad full of such players scores
nothing. One number would hide that.

Scoring per appearance rather than per minute also avoids the trap that
caught RugbyBox. There, output per minute correlated -0.61 with minutes
played, so the measure rewarded barely playing. Here the raw rate correlates
+0.30 with appearances: better players play more and score more, which is the
right direction.

Fixture difficulty is not in yet. The same player is worth more against a
weak defence, and that needs a team rating, which is its own small model.

## 2. Pricing

**Status: built, in `src/04_price.py`.**

This project has its own scoring system and so no published price list.
Prices are modelled from projected points.

The shape matters more than the scale. If price rose in step with points the
best players would be affordable, the budget would never bind, and the
optimiser would be a ranking exercise. The mapping is therefore convex, so
each extra projected point costs more than the last.

The curve was chosen by sweeping it against three things: a cheapest legal
squad well under budget, a strongest squad well over it, and enough spread in
value for money among the better players for the choice between them to
matter. A cubic curve gives 60, 160 and 34% against a budget of 100. A
gentler curve of 1.6 looked reasonable but left the price and the projection
very nearly cancelling, so every good player was the same value for money.

Two things are checked on every run rather than assumed:

- **the budget binds**, by pricing the strongest squad the quotas allow and
  confirming it costs more than the budget
- **prices are not circular.** Projected points both set the price and are
  what the optimiser maximises, so an error moves the two together. The
  spread of value for money across players is what stops them cancelling,
  and the stage fails if it collapses.

## 3. Picking the squad

**Status: built, in `src/05_optimise.py`.**

A binary integer programme. One variable per player, one if selected, plus a
second set for the captaincy.

Maximise total projected points, subject to:

- exactly the squad size the rules specify
- total price at or below the budget
- each position's quota satisfied exactly
- no more than the permitted number of players from any one club
- exactly one captain, who must be in the squad, scoring a multiple

This is a knapsack with side constraints. It is small, 367 players and twice
that many binary variables, and CBC solves it in well under a second.

The captain is solved jointly rather than picked afterwards, because
doubling one player's points changes what he is worth to the squad. On this
data that is worth **3.0 points**: picking the squad first and the captain
second gives 348.2, and solving both together gives 351.2. Small, but it is
the difference between a correct model and one that happens to agree.

### The budget is a real constraint

Checked on every run by solving twice, with the budget and without it:

| | Points | Cost |
|---|---|---|
| Best squad, no budget | 459.9 | 160.1 |
| Best squad within 100 | 351.2 | 100.0 |

The two share only **2 of 15 players**, and the budget costs 108.7 projected
points, 23.6% of what is theoretically available. The stage fails if the two
squads ever come out the same, because that would mean the optimiser was
ranking rather than choosing.

Note that this is the real test, and it is stronger than the one in stage D.
That stage compares the budget against a greedy best-per-position squad,
which is only a lower bound. This compares the actual optimum with and
without the constraint.

### What money buys

Sweeping the budget in equal steps gives the exchange rate between money and
points:

| Budget | Points | Per extra unit |
|---|---|---|
| 70 | 229.9 | |
| 100 | 351.2 | 3.01 |
| 130 | 415.7 | 1.93 |
| 160 | 459.4 | 1.28 |

The marginal value falls from 5.39 points per unit at the bottom to 1.28 at
the top, which is what a binding budget should look like.

The steps must be equal for this to be readable. A first version swept 0.8,
0.9, 1.0, 1.1, 1.25 and 1.5 times the budget and reported the raw gain at
each, which made a diminishing return look like a rising one: a wider step
buys more in total while buying less per unit.

## 3a. Showing it

**Status: built, in `src/06_export_web.py` and `web/index.html`.**

The interface has no server behind it. Every answer it can give is solved in
advance: the budget is swept across twenty levels and the optimal squad
recorded at each. That keeps it deployable as a static site.

It is split in two on purpose. A first version opened on the trade-off curve
and the scoring table, which was accurate and overwhelming. The front is now
a game: a welcome with no numbers on it, then a pitch with fifteen empty
shirts and a budget. Form is shown as one to five stars, ranked inside each
position so a good prop is a five-star prop even though props score less than
fly halves. When the fifteen is full, it is scored against the optimiser's
best team at the same budget. The optimiser is the opponent, which is the
most direct way to show what an optimum is: over 900 randomly completed teams
none beat it, and a rule-of-thumb fill reaches 88% to 95% of it.

The maths lives in a second room, the engine room: the pipeline, the budget
curve, the rules, every player's figures, and the blind spots.

Three statements are on the page because the decision records require them.
That this is a practice league with its own scoring and not advice for a real
competition, which is said on the welcome screen in plain words. That prices
are modelled. And that the breakdown is invisible, because the two columns
that would have measured it are corrupted. A test asserts they reach the page.

## 4. Planning transfers

**Status: not started.**

This is the part that distinguishes the project from a weekly knapsack.

Transfers are a limited resource over a season. Spending one now to chase a
favourable fixture costs the flexibility to react to an injury later. Picking
the best squad each week independently is therefore not the same as playing
well across a season, and will usually be worse.

Treated as a multi-period problem over a rolling horizon of several
gameweeks: state is the current squad and the transfers banked, and the
decision each week is which transfers to spend. Solved as a dynamic
programme, or as one integer programme spanning the horizon.

## 5. Risk

**Status: not started.**

The highest expected score is not always the right target. A team built from
players with volatile returns can have a high mean and a poor floor, which
loses head-to-head leagues.

Two ways to express the alternative, both standard: a chance constraint, so
the squad must exceed some score in a stated proportion of simulated
outcomes, or a mean-variance objective trading expected points against their
variance. Which is preferable depends on whether the user is playing a
league or chasing an overall rank, so it is exposed as a setting rather than
chosen for them.

Any simulation used here must be validated against data the optimiser has not
already fitted to. Simulating the output of an optimiser and reporting how
often it breaches a constraint it was pushed against produces a number that
looks like a finding and is close to circular. RugbyBox made exactly that
mistake; see `docs/lineage.md`.

## What the rules object has to supply

The maths above is the same for any rugby fantasy game. These are the
parameters that differ, and they live in one place so none of them leaks into
the code:

    squad size, budget, position quotas, club cap,
    transfer allowance, captain multiplier,
    points per scoring event
