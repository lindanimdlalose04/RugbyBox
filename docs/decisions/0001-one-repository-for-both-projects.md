# 1. One repository for both projects

- **Status:** accepted
- **Date:** 2026-11-19
- **Supersedes:** `fantasy/docs/decisions/0001-fresh-repository-with-a-lineage-note.md`

## Context

Fantasy Rugby Box began as a separate repository, built on the RugbyBox
DSS's data layer. The reasoning was sound: different questions, different
readers, and the DSS was finished and assessed while the new project was
growing.

It went wrong within days. Both projects lived in sibling folders that looked
alike and were built from the same data, and a commit written for one was made
in the other. Nothing was lost, but the assessed repository picked up a commit
labelled with the other project's work, and that project was left with its
newest work uncommitted. The cause was not carelessness: two repositories
growing from one source, worked on by one person in one terminal, will keep
producing that mistake.

Three ways to set the projects out were considered.

**Two repositories, with the finished one archived.** Archiving makes pushes
to the old one fail, which stops the specific mistake. But it does not remove
the confusion of two places, and it would have frozen the DSS completely,
when it is better described as resting.

**One repository, the DSS on a branch.** A branch is invisible from the
repository's front page and easy to forget, and the DSS is worth finding: it
is where the idea came from, and it is assessed work.

**One repository, each project in its own folder.** Everything is visible
from one place, labelled, and versioned separately.

## Decision

One repository, named RugbyBox, laid out as:

    fantasy/   Fantasy Rugby Box, the active project
    dss/       the RugbyBox DSS, finished and resting
    shared/    code both projects use
    docs/      decisions about the repository as a whole

Each project keeps its own README, changelog and requirements, and is run from
its own folder. Each is versioned on its own with prefixed tags, which is the
usual convention when one repository holds several projects:
`fantasy-v0.2.0`, `dss-v1.0.0`, `dss-v1.1.0`.

Code moves into `shared/` only when two projects genuinely use it. Today that
is the reader for the rugbydata store, which existed as two identical copies.

Both histories were kept. The DSS moved into `dss/` as a rename, so its
history follows its files. Fantasy Rugby Box's history was rewritten so that
every earlier commit already held its files under `fantasy/`, then merged in.
The assessed DSS commit, `4ef8bb0`, was not touched.

## Consequences

One place to work, and one place to look. The mistake that prompted this
cannot recur, because there is nowhere else to commit to.

The projects cannot share one test run: both have a module named `config`,
and whichever loads first would serve both. Each project's tests run from its
own folder, and `run_tests.py` at the root runs every suite separately and
sums the results.

The DSS's two fetch stages now import the shared reader instead of their own
copy. That is the only change made inside `dss/` beyond the move.

The old `fantasy-rugby-box` repository is redundant once this is pushed, and
is deleted.

Revisit if a project grows a separate audience that would be better served by
its own repository, for example if Fantasy Rugby Box ever ships as a product
with its own issues and contributors.
