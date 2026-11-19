# Fantasy Rugby Box

Pick a fantasy rugby squad that scores the most points your budget allows,
and plan your transfers more than one week ahead.

> **Early development.** The data layer works. The optimiser and the
> interface are being built. Nothing here is usable yet.

## The problem

Every week thousands of people solve the same constrained selection problem
by eye: pick fifteen players inside a budget, respecting position quotas and
a cap on players from any one club, to score as many points as possible.
Doing it by feel is hard, and doing it well over a whole season is harder,
because transfers are a limited resource. Spending one now to chase a good
fixture costs you the flexibility to react to an injury next month.

That is a knapsack problem followed by a planning problem, and both have
known solutions.

## What it will do

- Pick the optimal squad for a budget and a scoring system
- Choose a captain
- Plan transfers across several gameweeks rather than one at a time
- Offer a risk setting, so you can ask for the highest floor instead of the
  highest expected score

## Status

| Part | State |
|---|---|
| Match data from `rugbydata` | working, carried over from RugbyBox |
| Fetch and clean pipeline | working, 4 077 appearances across 93 fixtures |
| Data quality guards | working, and they found two unusable columns |
| Scoring rules | settled, tuned against 3 821 real appearances |
| Points projection | working, 373 players, shrunk by evidence |
| Player prices | working, modelled, and the budget binds |
| Optimiser | working, picks a squad and a captain |
| Interface | working, `web/index.html`: a game up front, the maths behind |
| Transfer planning | not started |
| Risk setting | not started |

This project uses **its own scoring system**, not any published game's. It is
a tool for demonstrating the method, not a companion to a real competition,
and the squads it picks are not advice for one.

## What it produces today

The best fifteen inside a budget of 100, with a captain, from 367 players:

| Position | Players |
|---|---|
| Props | Joe Heyes, George Kloska |
| Hooker | George McGuigan |
| Locks | Arthur Clark, Ollie Chessum |
| Loose forwards | Chandler Cunningham-South, Will Evans, Ethan Roots |
| Scrum half | Stephen Varney |
| Fly half | George Ford (captain) |
| Centres | Rekeiti Ma'asi-White, Tom Litchfield |
| Back three | Noah Caluori, Ollie Hassell-Collins, Cadan Murley |

351.2 projected points, costing exactly 100.0. Without the budget the best
squad scores 459.9 and costs 160.1, and shares only two of these fifteen
players, so the budget is doing the work rather than decorating the model.

## Running it

Requires Python 3.11+.

    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt

Then, from the project root:

    python src/01_fetch.py     # every player in the competition (~15 min cold)
    python src/02_clean.py     # the appearance table, with the quality guards
    python src/03_project.py   # expected points per player
    python src/04_price.py     # modelled prices, and the budget checks
    python src/05_optimise.py  # the squad, the captain, and what money buys
    python src/06_export_web.py   # solve across budgets for the interface

Then open `web/index.html`. It has three rooms:

- **Welcome.** One line and a button. No numbers.
- **Play.** A pitch with fifteen empty shirts and a budget. Tap a shirt, pick a
  player, with form shown as stars rather than figures. Blow the whistle and
  your fifteen is scored against the best team the optimiser can find.
- **Engine room.** Where the maths lives: how the machine picks, the budget
  curve, the scoring rules, every player's numbers, and what the model cannot
  see.

It needs no server. The optimiser is run for every budget ahead of time and
the answers ship beside the page, so it can be served as a static site.

    .venv\Scripts\pytest       # add --network to also read the live store

## Documentation

| Document | What it covers |
|---|---|
| `docs/method.md` | the maths: objective, constraints, why a MIP |
| `docs/data.md` | where the data comes from and how to refresh it |
| `docs/lineage.md` | where this project came from |
| `docs/decisions/` | why things were built the way they were |
| `CHANGELOG.md` | what changed in each release |

## Where this came from

This grew out of [RugbyBox](https://github.com/lindanimdlalose04/RugbyBox), a
multi-criteria squad selection system built for a university decision support
systems module. That project is finished and frozen. The data layer and the
integer programming approach carry over; the DEA, AHP and goal programming
stages do not. See `docs/lineage.md`.

## Data

Match data comes from the parquet store behind
[rugbypy](https://github.com/seanyboi/rugbypy), Apache-2.0.
