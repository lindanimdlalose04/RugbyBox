"""The Excel workbook must stay in step with the Python pipeline.

The workbook is the second, independent build. It fell silently out of step
once already, when stage C was revised and the workbook kept the figures from
the earlier efficiency measure, so the two builds were quietly solving
different problems. These tests catch that. Re-sync with:

    python src/export_excel.py
"""

import numpy as np
import pandas as pd
import pytest

openpyxl = pytest.importorskip("openpyxl")

WORKBOOK = "model/Rugby-Box_Solver.xlsx"
FIRST_DATA_ROW, FIRST_GP_ROW, N_PLAYERS = 4, 5, 41
FIRST_PEER_ROW = 23


def peer_rows(ws):
    """The peer table runs from its first row until the first blank name."""
    rows = []
    r = FIRST_PEER_ROW
    while ws.cell(r, 1).value is not None:
        rows.append(r)
        r += 1
    return rows


@pytest.fixture(scope="module")
def wb(request):
    root = request.path.parents[1]
    path = root / WORKBOOK
    if not path.exists():
        pytest.skip("workbook not present")
    return openpyxl.load_workbook(path)


@pytest.fixture(scope="module")
def data_rows(wb, cfg, squad_value):
    """The Data sheet, paired with the pipeline's own figures."""
    ws = wb["Data"]
    players = cfg.selectable(squad_value).set_index("name")
    rows = []
    for r in range(FIRST_DATA_ROW, FIRST_DATA_ROW + N_PLAYERS):
        name = ws.cell(r, 1).value
        assert name in players.index, f"{name!r} on the Data sheet is not selectable"
        rows.append((r, name, ws, players.loc[name]))
    return rows


def test_data_sheet_lists_the_selectable_players(data_rows, cfg, squad_value):
    names = {name for _, name, _, _ in data_rows}
    assert names == set(cfg.selectable(squad_value).name)


def test_data_sheet_figures_match_the_pipeline(data_rows):
    for r, name, ws, p in data_rows:
        assert ws.cell(r, 2).value == p.role, name
        assert ws.cell(r, 4).value == pytest.approx(p.workload, abs=1e-6), name
        assert ws.cell(r, 5).value == pytest.approx(p.cost, abs=1e-4), name
        assert ws.cell(r, 6).value == pytest.approx(p.efficiency, abs=1e-9), name
        assert ws.cell(r, 7).value == pytest.approx(p.score, abs=1e-9), name


def test_the_blend_formula_reproduces_the_selection_value(wb, data_rows, cfg):
    """Column C is a formula over the two components, not a pasted number."""
    alpha = wb["Data"]["M1"].value
    assert alpha == pytest.approx(cfg.ALPHA)
    for r, name, ws, p in data_rows:
        formula = ws.cell(r, 3).value
        assert isinstance(formula, str) and formula.startswith("="), name
        rebuilt = alpha * ws.cell(r, 6).value + (1 - alpha) * ws.cell(r, 7).value
        assert rebuilt == pytest.approx(p.value, abs=1e-9), name


@pytest.mark.parametrize("sheet", ["GP Weighted", "GP Pre-emptive_"])
def test_goal_targets_match_config(wb, cfg, sheet):
    ws = wb[sheet]
    assert ws["B51"].value == pytest.approx(cfg.TARGET_PERFORMANCE)
    assert ws["B52"].value == pytest.approx(cfg.TARGET_WORKLOAD)
    assert ws["B53"].value == pytest.approx(cfg.TARGET_COST)


@pytest.mark.parametrize(
    "sheet,csv", [("GP Weighted", "weighted"), ("GP Pre-emptive_", "preemptive")]
)
def test_selection_on_the_sheet_matches_the_solved_squad(
    wb, data_rows, sheet, csv, weighted, preemptive
):
    """The sheet should open already showing the answer."""
    solved = {"weighted": weighted, "preemptive": preemptive}[csv]
    ws = wb[sheet]
    picked = {
        name for i, (_, name, _, _) in enumerate(data_rows)
        if ws.cell(FIRST_GP_ROW + i, 6).value
    }
    assert picked == set(solved.name)


@pytest.mark.parametrize("sheet", ["GP Weighted", "GP Pre-emptive_"])
def test_sheet_totals_reproduce_the_solved_squad(wb, data_rows, sheet, cfg):
    """Evaluate the SUMPRODUCTs the sheet computes, and compare."""
    ws = wb[sheet]
    alpha = wb["Data"]["M1"].value
    sel, value, workload, cost = [], [], [], []
    for i, (r, _, data, _) in enumerate(data_rows):
        sel.append(ws.cell(FIRST_GP_ROW + i, 6).value or 0)
        value.append(alpha * data.cell(r, 6).value + (1 - alpha) * data.cell(r, 7).value)
        workload.append(data.cell(r, 4).value)
        cost.append(data.cell(r, 5).value)

    assert sum(sel) == cfg.SQUAD_SIZE
    assert float(np.dot(value, sel)) >= cfg.TARGET_PERFORMANCE - 1e-6
    assert float(np.dot(workload, sel)) <= cfg.TARGET_WORKLOAD + 1e-6


@pytest.mark.parametrize("sheet", ["GP Weighted", "GP Pre-emptive_"])
def test_structural_constraints_hold_on_the_sheet(wb, data_rows, sheet, cfg):
    ws = wb[sheet]
    roles = [p.role for _, _, _, p in data_rows]
    sel = [ws.cell(FIRST_GP_ROW + i, 6).value or 0 for i in range(len(data_rows))]

    for role, lo in cfg.ROLE_MIN.items():
        assert sum(s for s, r in zip(sel, roles) if r == role) >= lo, role
    forwards = sum(s for s, r in zip(sel, roles) if r in cfg.FORWARD_ROLES)
    assert cfg.FORWARDS_MIN <= forwards <= cfg.FORWARDS_MAX
    assert sum(s for s, r in zip(sel, roles) if r in cfg.FRONT_ROW_ROLES) >= cfg.FRONT_ROW_MIN


# --- the DEA demonstration sheet -----------------------------------------

def test_dea_sheet_weights_respect_the_share_bands(wb, cfg):
    ws = wb["DEA"]
    u = np.array([ws.cell(r, 2).value for r in range(6, 10)])
    ahp = np.array([ws.cell(r, 3).value for r in range(6, 10)])
    tol = ws["J4"].value

    assert tol == pytest.approx(cfg.VIRTUAL_WEIGHT_TOLERANCE)
    assert (u >= 0).all()
    shares = u / u.sum()
    for share, w in zip(shares, ahp):
        assert w * (1 - tol) - 1e-9 <= share <= min(w * (1 + tol), 1.0) + 1e-9


def test_dea_sheet_respects_every_peer_limit(wb):
    """No weighting may make a peer look more than fully efficient."""
    ws = wb["DEA"]
    u = np.array([ws.cell(r, 2).value for r in range(6, 10)])
    scale = np.array([ws.cell(13, 3 + i).value for i in range(4)])
    player_minutes = ws.cell(17, 2).value

    rows = peer_rows(ws)
    assert len(rows) > 10, "the peer group looks empty"

    for r in rows:
        raw = np.array([ws.cell(r, 3 + i).value for i in range(4)])
        score = float(np.dot(raw / scale, u))
        limit = ws.cell(r, 2).value / player_minutes
        assert score <= limit + 1e-6, ws.cell(r, 1).value


def test_the_evaluated_player_constrains_his_own_problem(wb):
    """Without his own row the score would not be bounded by one."""
    ws = wb["DEA"]
    names = [ws.cell(r, 1).value for r in peer_rows(ws)]
    assert ws.cell(17, 1).value in names


def test_dea_sheet_objective_matches_a_fresh_solve(wb, dea, cfg, players_season):
    """Re-solve the demonstration and compare with the figure on the sheet."""
    ws = wb["DEA"]
    u = np.array([ws.cell(r, 2).value for r in range(6, 10)])
    scale = np.array([ws.cell(13, 3 + i).value for i in range(4)])
    raw = np.array([ws.cell(17, 3 + i).value for i in range(4)])
    on_sheet = float(np.dot(raw / scale, u))

    rows = peer_rows(ws)
    pool = pd.DataFrame({
        "player_id": [ws.cell(r, 1).value for r in rows],
        "name": [ws.cell(r, 1).value for r in rows],
        "minutes": [ws.cell(r, 2).value for r in rows],
    })
    for i, measure in enumerate(dea.OUTPUTS):
        pool[measure] = [ws.cell(r, 3 + i).value / scale[i] for r in rows]

    target = pool[pool.name == ws.cell(17, 1).value].iloc[0]
    weights = __import__("ahp").measure_weights()
    bounds = dea.share_bounds("hooker", weights, cfg.VIRTUAL_WEIGHT_TOLERANCE)
    fresh, _ = dea.solve_weights(target, pool, bounds)

    assert on_sheet == pytest.approx(fresh, abs=1e-4)


def test_solver_model_is_still_attached(request):
    """The Solver setup lives in hidden defined names and is easy to lose."""
    import re
    import zipfile

    path = request.path.parents[1] / WORKBOOK
    with zipfile.ZipFile(path) as z:
        xml = z.read("xl/workbook.xml").decode("utf-8")

    names = {}
    for m in re.finditer(
        r'<definedName name="(solver_[^"]+)"(?: localSheetId="(\d+)")?[^>]*>'
        r'([^<]*)</definedName>', xml
    ):
        if m.group(2) == "3":                       # the DEA sheet
            names[m.group(1)] = m.group(3)

    assert names.get("solver_opt") == "DEA!$B$19"
    assert names.get("solver_adj") == "DEA!$B$6:$B$9"
    assert names.get("solver_num") == "2"
    assert names.get("solver_lhs2") == "DEA!$G$6:$H$9"
    assert names.get("solver_rel2") == "3"          # >=
    assert names.get("solver_rhs2") == "0"
    assert len(re.findall(r'name="solver_', xml)) > 150
