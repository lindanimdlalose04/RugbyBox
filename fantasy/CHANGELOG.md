# Changelog

Notable changes, newest first. Versions follow [semantic
versioning](https://semver.org). The project stays on `0.x` until it is
something a stranger could rely on.

Because results depend on data that is updated outside this project, each
release also records the date of the data snapshot it was built against.

This project lives in the RugbyBox repository, where each project is
versioned on its own. Its releases are tagged `fantasy-vX.Y.Z`.

## Unreleased

### Added

- The game is published to GitHub Pages at https://lindanimdlalose04.github.io/RugbyBox/, by a workflow that
  uploads `web/` whenever it changes on `main`.

### Fixed

- The page only worked inside Claude's artifact viewer, which quietly adds a
  page header and a rule keeping hidden elements hidden. Served as it was,
  the player-picker overlay covered the screen on load, the machine-team
  legend was always visible, the action buttons stayed at full time, and
  phones got a shrunken desktop page. It is now a complete document that
  works on any host, with tests that keep it that way.
- On phones, shirt labels were cut off: at 375px wide, three position names
  and 51 of 330 surnames. Shirts are now wider on small screens and the
  labels slightly smaller, so no position name is cut and only the three
  longest surnames end in an ellipsis. On the smallest phones an empty
  shirt's label wraps onto two lines instead.
- After the whistle, the bank card kept saying "Blow the whistle when you
  are ready". It now says it is full time.
- The site failed to republish: the publishing workflow used out-of-date
  versions of GitHub's actions, and the publish step could not find the
  package the upload step had just made. All four actions are upgraded
  together to their current versions.

## 0.2.0, 2026-11-19

Data as of 2026-11-16. Tagged `fantasy-v0.2.0`.

The first release. A squad can be built and played against the optimiser
through a static web page.

There is no separate 0.1.0. It was planned for the optimiser on its own, and
the optimiser and the interface were finished together, so the two planned
milestones ship as this one release.

### Moved

- The project now lives in the RugbyBox repository under `fantasy/`, beside
  the DSS it grew from, instead of in a repository of its own. Two
  repositories built from the same data made it too easy to commit to the
  wrong one, and it happened. The full history came across. See
  `docs/decisions/0001-one-repository-for-both-projects.md` at the
  repository root.
- The store reader is no longer a copy in `src/`. Both projects now use the
  one in `shared/rugbystore`, and its tests moved with it.

### Added

- Repository scaffold, documentation and decision records
- The parquet store reader, carried over unchanged from RugbyBox
- `src/rules.py`, the scoring system and squad rules as a validated object,
  with point values tuned against 18 499 real appearances so that every
  position is worth picking

### Decided

- This project uses its own scoring system rather than a published game's
  (`docs/decisions/0003`)
- Prices are modelled from projected points, with a CSV input kept as the
  interface so another source can be swapped in (`docs/decisions/0002`)
- Corrupted source fixtures are rejected at fixture level on two signatures,
  costing about 7% of appearances (`docs/decisions/0004`)

- `src/01_fetch.py` and `src/02_clean.py`, the pipeline, producing 4 077
  appearances across 93 fixtures with a recorded data snapshot date
- A column integrity check that stops the pipeline if any column being
  scored looks like a copy of another
- `src/03_project.py`, expected points per player, kept as three separate
  numbers: a rate shrunk toward its position baseline, an availability
  share, and the two multiplied. The shrinkage point is estimated from the
  data at 4.3 appearances, from a split-half reliability of 0.57.
- `src/04_price.py`, modelled prices on a convex curve, with checks on every
  run that the budget binds and that price and projection do not cancel
- `src/05_optimise.py`, the squad and captain as one integer programme, with
  the budget's effect measured on the optimum rather than on a greedy proxy
- `src/06_export_web.py`, which solves the squad at 20 budget levels and
  writes them beside the page
- `web/index.html`, the interface, in three rooms. A welcome with no numbers
  on it. A pitch where you fill fifteen shirts inside a budget, with form
  shown as stars, and are then scored against the optimiser's best team. And
  an engine room holding the budget curve, the rules, every player's figures
  and the model's blind spots.
- The exporter now ships the whole player pool, one canonical name per club
  (the source spells them several ways), and a one-to-five star rating ranked
  inside each position

### Verified

- The budget binds on the optimum: the best squad within 100 shares only 2 of
  15 players with the best squad at any price, and gives up 108.7 projected
  points, 23.6% of what is available.
- Solving the captain jointly with the squad is worth 3.0 points over picking
  the squad first and the captain second.
- The marginal value of budget falls from 5.39 points per unit to 1.28, as a
  binding constraint should.
- The chosen squad survives a one-opt check: no swap of a selected player for
  an unselected one in the same position improves it.

### Found

- **`line_breaks` and `turnovers_won` are unusable.** 84% of non-zero
  `line_breaks` values are an exact copy of another column, usually
  `carries`, and only 1 fixture in 93 is free of it. Both are dropped from
  the scoring system. The breakdown is consequently invisible to the model.
- Per-minute rates in count columns on 7 fixtures elsewhere in the store,
  none inside the current window.
- One appearance recording two red cards, which cannot happen.
- **This affects RugbyBox**, whose efficiency analysis uses both corrupted
  columns as two of its four outputs, over the same competition and season.

### Changed

- The first interface put the trade-off curve and the scoring table on the
  opening screen. It was accurate and overwhelming. The numbers moved behind
  a tab and the opening screen became an invitation to play.

- Tackles raised from 1.5 to 2.0 points, rebalancing the positions after the
  loss of turnovers. Best-to-worst position ratio is 1.91.
- The first guard, which rejected whole fixtures on a duplicated pair, is
  replaced. It discarded 28% of appearances and still missed the problem.

## Planned

- `0.3.0` transfer planning over several gameweeks
- `0.4.0` a risk setting, for a high floor rather than a high average
- `1.0.0` usable by someone who did not write it
