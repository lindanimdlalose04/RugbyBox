# Where this project came from

Fantasy Rugby Box grew out of the **RugbyBox DSS**, a decision support
system built for ITRI 628 at North-West University in 2026. That project
selected a rugby matchday 23 under three competing goals: field the
strongest side, keep player workload below a safe ceiling, and stay inside
the matchday wage budget.

Both now live in the same repository. The DSS is in `dss/` and is finished:
the tag `dss-v1.0.0` marks the state that was submitted and assessed, and
`dss-v1.1.0` the revision made after assessment. Nothing in `fantasy/`
changes it.

## Two projects, one repository

The two answer different questions for different people. The DSS answers
"which 23 should a coach name this weekend, and what does each compromise
cost", and its reader is an examiner. This project answers "which fifteen
should I pick inside my budget", and its reader is someone playing a game.

They started in separate repositories, for that reason. It did not last.
Both are built from the same data, the folders looked alike, and within
days a commit meant for one was made in the other. They now share one
repository, each in its own folder with its own README, changelog and
version tags, and the code they genuinely share lives once, in `shared/`.
The reasoning is in `docs/decisions/0001-one-repository-for-both-projects.md`
at the repository root, which supersedes this project's own first decision.

## What carried over

**The data layer.** The reader for the parquet store behind `rugbypy`,
with its retries, came across unchanged. It is now shared by both projects
from `shared/rugbystore`.

**The approach to selection.** Choosing a squad under a budget and positional
quotas is an integer programme in both projects. The solver and the general
shape of the model carry over even though every constraint differs.

**Habits worth keeping.** A single `config.py` holding anything shared or
tunable, tests on the things that break in silence, and a README that states
its assumptions and limitations rather than hiding them. The absence of those
is what caused the problems that had to be fixed in RugbyBox late on.

## What did not carry over

**Data envelopment analysis.** RugbyBox used it to measure output per minute
against a league-wide peer group. A fantasy game awards points directly, so
there is no need to infer a quality measure: the scoring system is the
measure.

**The analytic hierarchy process.** It supplied weights for competing goals
and for measures within a position. Fantasy has one objective, points, so
there is nothing to weight.

**Goal programming.** Three competing goals with deviation variables made
sense when performance, workload and cost all mattered and none could be
fully satisfied. Here the budget is a hard constraint, not a goal, and points
are simply maximised.

**The Excel Solver workbook.** It existed to demonstrate the methods in a
second, independent build for assessment. It has no place in a product.

## What RugbyBox is worth reading for

Two findings from that project are worth knowing before repeating its
mistakes.

The first is about small samples. Measuring output per minute and ranking on
it will put players with barely any playing time at the top, because a short
spell is where a freak rate is most likely. Any projection built here needs
shrinking toward a sensible baseline by how much evidence sits behind it.
The DSS's `dss/src/04_dea.py` estimates that baseline from split-half
reliability rather than asserting it.

The second is about validating a model against its own output. RugbyBox
simulated the workload of a squad its optimiser had just pushed up against
the workload ceiling, and reported that the ceiling was breached about half
the time. That number was close to circular: an optimiser puts a plan on its
constraint, so symmetric noise around it breaches roughly half the time
whatever the noise is. If this project ever reports a confidence figure, it
has to come from data the optimiser did not already fit to.
