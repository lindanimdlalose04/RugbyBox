"""What the interface is given.

The page has no server, so every answer it can give has to be in this file.
These tests check the shape of it, and that the caveats the decision records
require are actually carried through to the page rather than only written
down in the repository.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from rules import DEFAULT  # noqa: E402

WEB = ROOT / "web"


@pytest.fixture(scope="module")
def exporter():
    spec = importlib.util.spec_from_file_location(
        "export_web", SRC / "06_export_web.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def payload():
    path = WEB / "data.js"
    if not path.exists():
        pytest.skip("web data not built; run stage 06")
    text = path.read_text(encoding="utf-8")
    body = text.split("window.FRB_DATA = ", 1)[1].rsplit(";", 1)[0]
    return json.loads(body)


# --- the file the page loads ----------------------------------------------

def test_the_data_is_a_script_not_a_json_file():
    """A page opened off disk can load a script but cannot fetch a file."""
    text = (WEB / "data.js").read_text(encoding="utf-8")
    assert text.lstrip().startswith("//")
    assert "window.FRB_DATA" in text


def test_the_page_loads_the_data_file():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<script src="data.js">' in html


def test_the_page_renders_without_the_data(payload):
    """A missing data file must not throw; the page simply does nothing."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert "if (!D) { return; }" in html


# --- the scenarios --------------------------------------------------------

def test_every_scenario_holds_a_legal_squad(payload):
    for scenario in payload["scenarios"]:
        squad = scenario["squad"]
        assert len(squad) == DEFAULT.squad_size, scenario["budget"]
        assert sum(p["captain"] for p in squad) == 1, scenario["budget"]
        assert scenario["cost"] <= scenario["budget"] + 1e-6


def test_every_scenario_fills_every_quota(payload):
    for scenario in payload["scenarios"]:
        counts = {}
        for player in scenario["squad"]:
            counts[player["role"]] = counts.get(player["role"], 0) + 1
        assert counts == dict(DEFAULT.quota), scenario["budget"]


def test_more_budget_never_scores_less(payload):
    """A bigger budget cannot make the best squad worse."""
    scenarios = payload["scenarios"]
    for earlier, later in zip(scenarios, scenarios[1:]):
        assert later["budget"] > earlier["budget"]
        assert later["points"] >= earlier["points"] - 1e-6, (
            f"{later['budget']} scores less than {earlier['budget']}"
        )


def test_the_budget_range_brackets_the_default(payload):
    budgets = [s["budget"] for s in payload["scenarios"]]
    assert min(budgets) < payload["default_budget"] < max(budgets)


def test_no_scenario_beats_the_unconstrained_squad(payload):
    ceiling = payload["unlimited"]["points"]
    for scenario in payload["scenarios"]:
        assert scenario["points"] <= ceiling + 1e-6


# --- what the page must say -----------------------------------------------

def test_the_caveats_are_carried_to_the_page(payload):
    """Decision 0002 requires the page to say what this is.

    A squad list looks equally authoritative whether or not its prices are
    real, so these cannot stay only in the repository.
    """
    joined = " ".join(payload["caveats"]).lower()
    assert len(payload["caveats"]) >= 3
    assert "own scoring system" in joined
    assert "not advice" in joined
    assert "modelled" in joined
    assert "breakdown" in joined, "the missing breakdown has to be disclosed"
    assert "fixture difficulty" in joined


def test_the_data_date_travels_with_the_numbers(payload):
    """A figure without its data date cannot be reproduced."""
    assert payload["meta"]["data_as_of"]
    assert payload["meta"]["data_as_of"] != "unknown"


def test_the_scoring_system_is_shown(payload):
    points = payload["rules"]["points"]
    assert points["tries"] == DEFAULT.points["tries"]
    assert "line_breaks" not in points, "a corrupted column must not be shown as scored"
    assert "turnovers_won" not in points


def test_positions_carry_their_quotas(payload):
    assert len(payload["positions"]) == len(DEFAULT.quota)
    assert sum(p["quota"] for p in payload["positions"]) == DEFAULT.squad_size


# --- the shirt numbers ----------------------------------------------------

def test_the_shirt_numbers_make_a_real_fifteen():
    """The quota happens to be a standard XV, so the page numbers it as one."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    start = html.index("var SHIRTS")
    block = html[start:html.index("};", start)]
    numbers = [int(n) for n in __import__("re").findall(r"\b(\d+)\b", block)]
    assert sorted(numbers) == list(range(1, 16)), (
        "every shirt from 1 to 15 should be used exactly once"
    )


# --- the pool the game picks from -----------------------------------------

def test_the_whole_pool_is_shipped_for_team_building(payload):
    """The front of the page lets you pick your own fifteen, so it needs everyone."""
    assert len(payload["players"]) == payload["meta"]["players_considered"]
    ids = [p["id"] for p in payload["players"]]
    assert len(set(ids)) == len(ids)


def test_every_machine_pick_is_in_the_pool(payload):
    pool = {p["id"] for p in payload["players"]}
    for scenario in payload["scenarios"]:
        assert {p["id"] for p in scenario["squad"]} <= pool


def test_stars_run_from_one_to_five_in_every_position(payload):
    """Stars rank a player inside his own position, so each has its five-star men."""
    by_role = {}
    for player in payload["players"]:
        assert 1 <= player["stars"] <= 5
        by_role.setdefault(player["role"], set()).add(player["stars"])
    for role, seen in by_role.items():
        assert seen == {1, 2, 3, 4, 5}, role


def test_more_stars_never_means_a_worse_projection(payload):
    by_role = {}
    for p in payload["players"]:
        by_role.setdefault(p["role"], []).append(p)
    for role, group in by_role.items():
        group.sort(key=lambda p: p["projected"])
        stars = [p["stars"] for p in group]
        assert stars == sorted(stars), role


def test_each_club_has_one_name(payload):
    """The source spells clubs several ways; the page must not."""
    assert len(payload["clubs"]) == 10
    names = {c["id"]: c["name"] for c in payload["clubs"]}
    for player in payload["players"]:
        assert player["team"] == names[player["team_id"]]


def test_the_page_has_a_kit_for_every_club(payload):
    html = (WEB / "index.html").read_text(encoding="utf-8")
    start = html.index("var KIT")
    block = html[start:html.index("};", start)]
    for club in payload["clubs"]:
        assert club["short"] + ":" in block, f"no shirt colours for {club['short']}"


def test_the_page_opens_on_a_welcome_not_on_numbers():
    """The maths lives behind a door. The first screen is an invitation."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    home = html[html.index('id="view-home"'):html.index('id="view-play"')]
    assert "hidden" not in home.split(">", 1)[0], "the welcome must be the visible view"
    assert 'id="view-play" class="wrap play" hidden' in html
    assert 'id="view-engine" class="wrap engine" hidden' in html
    for word in ("projected", "optimis", "integer", "%"):
        assert word not in home.lower(), f"the welcome screen mentions {word!r}"


def test_the_game_budgets_have_solved_squads(payload):
    """Shoestring, classic and big spender each need the machine's answer."""
    import re
    html = (WEB / "index.html").read_text(encoding="utf-8")
    budgets = {float(b) for b in re.findall(r'data-budget="(\d+)"', html)}
    solved = {s["budget"] for s in payload["scenarios"]}
    assert budgets and budgets <= solved


# --- ready to be served as a website --------------------------------------

def test_the_page_is_a_complete_document():
    """GitHub Pages serves the file as it is, with nothing added.

    Without a doctype the browser falls back to quirks mode, and without a
    viewport tag a phone renders a shrunken desktop page.
    """
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert html.lstrip().lower().startswith("<!doctype html>")
    assert '<meta charset="utf-8">' in html
    assert 'name="viewport"' in html
    assert "</head>" in html and "<body>" in html and "</html>" in html


def test_hidden_things_stay_hidden_outside_claude():
    """The picker overlay, the legend and the action buttons all set their own
    display, which beats the browser's default for the hidden attribute. The
    page has to restate the rule itself, or the overlay covers the screen."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    style = html[html.index("<style>"):html.index("</style>")]
    assert "[hidden]{display:none!important}" in style
    # Last in the sheet, so it wins even where !important is not honoured.
    tail = style.rstrip().splitlines()[-1]
    assert tail.strip() == "[hidden]{display:none!important}"


def test_the_page_only_loads_what_it_can_reach_when_hosted():
    """Every local file is referenced relatively, so it works under any path,
    including the /RugbyBox/ prefix GitHub Pages adds."""
    import re
    html = (WEB / "index.html").read_text(encoding="utf-8")
    for src in re.findall(r'(?:src|href)="([^"#]+)"', html):
        if src.startswith(("https://", "data:", "mailto:")):
            continue
        assert not src.startswith("/"), f"{src} would break under /RugbyBox/"
        assert (WEB / src).exists(), f"{src} is referenced but not shipped"
