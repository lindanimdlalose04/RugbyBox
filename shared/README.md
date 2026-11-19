# Shared code

Code used by more than one project in this repository. Anything here is
installed once, from the repository root, and then importable from any
project:

    pip install -r requirements.txt

## `rugbystore`

Reads the parquet store behind [rugbypy](https://github.com/seanyboi/rugbypy):
match, player, team, competition and venue files, with retries for the host's
rate limiting.

    from rugbystore import get

    teams = get("team", "team_registry")

Used by `dss/` and `fantasy/`. It started life as `src/rb.py` in the DSS and
was copied into Fantasy Rugby Box when that began as its own repository. Once
both projects lived here, the two copies were reduced to this one, so a fix
reaches both.

## Tests

    cd shared
    pytest                 # offline
    pytest --network       # also read the live store

## What belongs here

Only code that two projects genuinely use. A helper that one project happens
to need stays in that project until a second one needs it too. Other
candidates already exist, such as the position labels and the minutes
reconstruction, which both projects define separately; they move here when
either copy next needs to change.
