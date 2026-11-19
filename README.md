# RugbyBox

Rugby selection problems, solved with real match data and optimisation.

This repository holds two projects built on the same data. One is a game you
can play. The other is the decision support system it grew out of.

| Project | What it is | State | Latest |
|---|---|---|---|
| [**Fantasy Rugby Box**](fantasy/README.md) | Pick a fantasy fifteen on a budget, then play it against the best team an optimiser can find | Active | `fantasy-v0.2.0` |
| [RugbyBox DSS](dss/README.md) | Selects a club's matchday 23 under competing performance, workload and budget goals. Built for ITRI 628, North-West University | Finished, resting | `dss-v1.1.0` |

Start with **Fantasy Rugby Box**. The DSS is where the idea came from, and it
is kept here, complete and runnable, for anyone who wants to see the method
it started with.

## Find your way around

    fantasy/            Fantasy Rugby Box, the active project
      src/              the pipeline, as numbered stages
      web/              the game, a static page
      docs/             method, data and the project's decisions
      tests/

    dss/                the RugbyBox DSS, as assessed and then revised
      src/              DEA, AHP, scoring, goal programming, simulation
      model/            the Excel Solver workbook
      tests/

    shared/             code both projects use
      rugbystore/       the reader for the rugbydata parquet store

    docs/               decisions about the repository as a whole
    run_tests.py        runs every project's tests

Each project has its own README explaining how to run it, its own changelog,
and its own version tags.

## Set up once

Requires Python 3.11+. One environment serves every project:

    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt

That also installs the shared code, so any project can use
`from rugbystore import get`.

Then go into a project's folder and follow its README:

    cd fantasy

## Tests

Every project's tests, each run in its own folder:

    python run_tests.py

They have to run separately: both projects have a module called `config`,
and one test run would only load one of them.

## Versions

Each project is versioned on its own, with tags prefixed by its folder name,
following [semantic versioning](https://semver.org).

| Tag | Marks |
|---|---|
| `fantasy-v0.2.0` | First release of Fantasy Rugby Box: a playable game against the optimiser |
| `dss-v1.1.0` | The DSS revised after assessment: tests, a corrected efficiency measure, a workbook filled from the pipeline |
| `dss-v1.0.0` | The DSS exactly as submitted and assessed for ITRI 628 |

To see any of them as it was, for example the assessed DSS:

    git checkout dss-v1.0.0

## How it fits together

Both projects read the same source: the parquet store behind
[rugbypy](https://github.com/seanyboi/rugbypy), Apache-2.0, through
`shared/rugbystore`. Both turn it into a selection problem and solve it as an
integer programme. They differ in what they optimise. The DSS weighs three
goals a coach cares about and prices the compromise between them. Fantasy
Rugby Box maximises points under a budget, for a player.

Two problems in the source data were found while building Fantasy Rugby Box
and matter to both. Two columns, `line_breaks` and `turnovers_won`, hold
copies of other columns, so neither can be trusted. Fantasy Rugby Box does
not use them. The DSS does, as two of the four inputs to its efficiency
analysis, and its README says so. See
`fantasy/docs/decisions/0004-guarding-against-corrupted-source-rows.md`.

Why the projects share a repository, rather than one each, is recorded in
`docs/decisions/0001-one-repository-for-both-projects.md`.
