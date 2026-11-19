# Changelog

Notable changes to the RugbyBox DSS, newest first. Versions follow
[semantic versioning](https://semver.org) and are tagged `dss-vX.Y.Z`.

This project is finished and resting. New work happens in `fantasy/`.

## Unreleased

### Moved

- The project now lives in `dss/` inside the RugbyBox repository, beside
  Fantasy Rugby Box, which grew out of it. Every file was renamed rather than
  copied, so its history follows it. Run it from this folder.
- The store reader, `src/rb.py`, became the shared package
  `shared/rugbystore`, which Fantasy Rugby Box uses too. The two fetch stages
  now import it from there. Nothing else inside the project changed.

### Found

- Two of the four efficiency inputs, `line_breaks` and `turnovers_won`, are
  corrupted in the source: across this competition 84% of non-zero
  `line_breaks` values are an exact copy of another column. Found while
  building Fantasy Rugby Box. Recorded in the README; not corrected here.

## 1.1.0, 2026-11-16

Revised after assessment. Tagged `dss-v1.1.0`.

This commit was first pushed under a message meant for another project,
"Add the optimiser; confirm the budget binds on the optimum". It was
relabelled to describe what it contains. The content did not change.

### Changed

- **The efficiency measure, which changes results.** Plain CCR let each
  player choose flattering weights, which put five of 41 players on the
  frontier, four with under 240 minutes. Weights are now restricted around
  the AHP weights, players are scored by cross-efficiency, and thin evidence
  is shrunk toward the league average, with the shrinkage point estimated
  from split-half reliability at 500 minutes.
- The performance target moves from 11.1 to 9.95 to match the new scale.
  Three players in the recommended squad change, and the weighted and
  pre-emptive squads now agree.
- The simulation reports the breach rate under four spread assumptions and
  uses common random numbers, since the headline figure was close to
  circular.

### Added

- `src/config.py`, holding constraints and targets that had been copied into
  three files
- `requirements.txt`, with pinned versions
- 77 tests, where there were none
- `src/export_excel.py`, which fills the Solver workbook from the pipeline
  so the two builds cannot drift apart unnoticed. The original workbook is
  kept as `model/Rugby-Box_Solver_first_build.xlsx`.

### Fixed

- `check_conflict.py` printed one of its figures as a hard-coded number
  rather than solving for it
- Non-optimal solves returned a number rather than raising

## 1.0.0

The version submitted and assessed for ITRI 628 Decision Support Systems,
North-West University, 2026. Tagged `dss-v1.0.0`, commit `4ef8bb0`.

Data envelopment analysis, the analytic hierarchy process, a scoring model,
weighted and pre-emptive goal programming, and a Monte Carlo workload
simulation, built twice: in Excel with Solver and in Python with PuLP.
