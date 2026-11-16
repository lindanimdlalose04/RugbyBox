"""Write the Python results into the Excel Solver workbook.

The workbook is the second, independent build of the same model. It was
previously filled by hand from exported CSVs, which is why it fell out of
step with the Python pipeline when stage C was revised. This writes it
directly instead, so the two builds can be re-synchronised with one command.

What it writes:

  Data              the 41 selectable players, with the efficiency and
                    scoring components shown separately and the selection
                    value as a formula over them
  DEA               the restricted-weight efficiency programme for one
                    player, laid out for Solver
  GP Weighted       the three goal targets, the goal weights, and the
                    solution found in Python
  GP Pre-emptive_   the same
  Simulation        the workload ceiling and the spread

What it leaves alone: the AHP sheet, which is unchanged because the
judgements are unchanged, and the Scoring sheet, whose positional bests come
from the same data and whose weights already read live from the AHP sheet.

The Solver model definitions are stored in the workbook as hidden defined
names. openpyxl preserves them, but it cannot edit them, so the DEA sheet's
model is rewritten afterwards directly in the saved file.

Run from the project root, after stage 07:  python src\\export_excel.py
"""

import json
import os
import re
import shutil
import sys
import zipfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfg  # noqa: E402
from ahp import measure_weights  # noqa: E402

WORKBOOK = "model/Rugby-Box_Solver.xlsx"

OUTPUTS = ["metres_carried", "line_breaks", "tackles_made", "turnovers_won"]
SHORT = ["Metres", "Breaks", "Tackles", "Turnovers"]

# The position and player the DEA sheet demonstrates. One player is enough to
# show the method; the pipeline does all 41 against their own peer groups.
DEA_ROLE = "hooker"
DEA_PLAYER = "Dan Frost"

# Sheet positions, counted from zero, as the Solver defined names index them.
SHEET_INDEX = {
    "Data": 0, "AHP": 1, "Scoring": 2, "DEA": 3,
    "GP Weighted": 4, "GP Pre-emptive_": 5, "Simulation": 6,
}

FIRST_DATA_ROW = 4          # Data sheet, first player
FIRST_GP_ROW = 5            # GP sheets, first player


# --- sheet writers --------------------------------------------------------

def unmerge(ws):
    """Merged cells refuse writes, and the notes columns carry several."""
    for rng in list(ws.merged_cells.ranges):
        ws.unmerge_cells(str(rng))


def write_data(ws, players):
    """The 41 selectable players, with the blend shown rather than hidden."""
    unmerge(ws)
    ws["A1"] = "Processed data. Written by src/export_excel.py, do not edit by hand."

    headers = ["name", "role", "value", "workload", "cost",
               "efficiency", "score", "evidence", "appearances", "minutes"]
    for col, text in enumerate(headers, start=1):
        ws.cell(3, col, text)

    ws["L1"] = "Blend (ALPHA)"
    ws["M1"] = cfg.ALPHA
    ws["L2"] = "value = ALPHA x efficiency + (1 - ALPHA) x score"
    ws["L3"] = "evidence: how much of the efficiency score is the player's own"

    by_name = players.set_index("name")
    order = [ws.cell(r, 1).value for r in range(FIRST_DATA_ROW, FIRST_DATA_ROW + len(players))]

    for i, name in enumerate(order):
        r = FIRST_DATA_ROW + i
        p = by_name.loc[name]
        ws.cell(r, 1, name)
        ws.cell(r, 2, p.role)
        ws.cell(r, 3, f"=$M$1*F{r}+(1-$M$1)*G{r}")
        ws.cell(r, 4, float(p.workload))
        ws.cell(r, 5, float(p.cost))
        ws.cell(r, 6, float(p.efficiency))
        ws.cell(r, 7, float(p.score))
        ws.cell(r, 8, float(p.evidence))
        ws.cell(r, 9, int(p.appearances))
        ws.cell(r, 10, float(p.minutes))

    return order


def clear(ws):
    unmerge(ws)
    for row in ws.iter_rows():
        for c in row:
            c.value = None


def write_dea(ws, league, weights):
    """The restricted-weight efficiency programme, laid out for Solver."""
    role, tol = DEA_ROLE, cfg.VIRTUAL_WEIGHT_TOLERANCE

    pool = league[
        (league.role == role) & league.frontier & (league.minutes > 0)
    ].copy()
    squad_here = league[
        (league.role == role) & league.in_squad & (league.minutes > 0)
    ]
    pool = pd.concat(
        [pool, squad_here[~squad_here.player_id.isin(set(pool.player_id))]],
        ignore_index=True,
    ).sort_values("name").reset_index(drop=True)

    target = pool[pool.name == DEA_PLAYER]
    if target.empty:
        raise SystemExit(f"{DEA_PLAYER} is not in the {role} pool")
    target = target.iloc[0]
    scale = pool[OUTPUTS].mean()

    clear(ws)
    ws["A1"] = f"Efficiency of {DEA_PLAYER} against every {role} in the competition"
    ws["A2"] = ("Each player may weight the four measures to suit himself, but no "
                "weighting may make any player look more than fully efficient, and "
                "no single measure may carry the score.")

    # --- the weights Solver chooses ---
    ws["A4"] = "THE MEASURE WEIGHTS SOLVER CHOOSES"
    ws["I4"] = "Tolerance"
    ws["J4"] = tol
    ws["K4"] = "Each share may sit this far either side of the AHP weight."

    for col, text in enumerate(
        ["Measure", "Weight", "AHP weight", "Share", "Min share", "Max share",
         "Slack low", "Slack high"], start=1):
        ws.cell(5, col, text)

    _, u = solve_demo(pool, target, scale, weights, role, tol)
    for i, (short, measure) in enumerate(zip(SHORT, OUTPUTS)):
        r = 6 + i
        ws.cell(r, 1, short)
        ws.cell(r, 2, float(u[i]))                       # changing cell
        ws.cell(r, 3, float(weights[role][measure]))
        ws.cell(r, 4, f"=B{r}/SUM($B$6:$B$9)")
        ws.cell(r, 5, f"=C{r}*(1-$J$4)")
        ws.cell(r, 6, f"=MIN(C{r}*(1+$J$4),1)")
        ws.cell(r, 7, f"=B{r}-E{r}*SUM($B$6:$B$9)")      # must be >= 0
        ws.cell(r, 8, f"=F{r}*SUM($B$6:$B$9)-B{r}")      # must be >= 0

    ws["K6"] = "Share is shown for reading only. Solver works on the two slacks,"
    ws["K7"] = "which say the same thing without dividing by a changing cell."

    # --- the common scale ---
    ws["A11"] = "PUTTING THE FOUR MEASURES ON ONE SCALE"
    ws["A12"] = ("Metres run into the hundreds and turnovers into single figures, so a "
                 "share of the weighting only means something once each measure is "
                 "divided by what a typical player in the position manages.")
    ws["A13"] = "Peer mean"
    for i, measure in enumerate(OUTPUTS):
        ws.cell(13, 3 + i, float(scale[measure]))
        ws.cell(12, 3 + i, SHORT[i])

    # --- the player ---
    ws["A15"] = "THE PLAYER BEING EVALUATED"
    head = (["Name", "Minutes"] + SHORT + [f"n.{s}" for s in SHORT] + ["Score"])
    for col, text in enumerate(head, start=1):
        ws.cell(16, col, text)

    ws.cell(17, 1, target["name"])
    ws.cell(17, 2, float(target.minutes))
    for i, measure in enumerate(OUTPUTS):
        ws.cell(17, 3 + i, float(target[measure]))
        ws.cell(17, 7 + i, f"={chr(ord('C') + i)}17/{chr(ord('C') + i)}$13")
    ws.cell(17, 11, "=SUMPRODUCT(G17:J17,$B$6:$B$9)")

    ws["A19"] = "Efficiency score (Solver maximises this)"
    ws["B19"] = "=K17"

    # --- the peer group ---
    first = 23
    ws["A21"] = f"EVERY {role.upper()} IN THE COMPETITION"
    ws["A22"] = "No weighting may make any of them look more than fully efficient."
    for col, text in enumerate(head + ["Limit"], start=1):
        ws.cell(22, col, text)

    for i, (_, peer) in enumerate(pool.iterrows()):
        r = first + i
        ws.cell(r, 1, peer["name"])
        ws.cell(r, 2, float(peer.minutes))
        for j, measure in enumerate(OUTPUTS):
            ws.cell(r, 3 + j, float(peer[measure]))
            ws.cell(r, 7 + j, f"={chr(ord('C') + j)}{r}/{chr(ord('C') + j)}$13")
        ws.cell(r, 11, f"=SUMPRODUCT(G{r}:J{r},$B$6:$B$9)")
        ws.cell(r, 12, f"=B{r}/$B$17")

    last = first + len(pool) - 1
    # Kept out of column A, which holds names: anything reading the peer table
    # finds its end by the first blank name.
    ws.cell(21, 14, "Constraint: every score in column K must stay at or below "
                    "its limit in column L.")
    return first, last, len(pool)


def solve_demo(pool, target, scale, weights, role, tol):
    """Re-solve the demonstration in Python so the sheet opens on the answer."""
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("dea", f"{here}/04_dea.py")
    dea = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dea)

    norm = pool.copy()
    for measure in OUTPUTS:
        norm[measure] = (pool[measure] / scale[measure]).fillna(0.0)
    row = norm[norm.name == target["name"]].iloc[0]
    bounds = dea.share_bounds(role, weights, tol)
    return dea.solve_weights(row, norm, bounds)


def write_goal_sheet(ws, order, selected, preemptive: bool):
    """Targets, weights and the solution Python found."""
    unmerge(ws)
    goals = json.load(open(f"{cfg.PROCESSED}/weights.json"))["goals"]

    for i, (name, target) in enumerate([
        ("Performance", cfg.TARGET_PERFORMANCE),
        ("Workload", cfg.TARGET_WORKLOAD),
        ("Cost", cfg.TARGET_COST),
    ]):
        r = 51 + i
        ws.cell(r, 2, target)
        ws.cell(r, 6, round(goals[name.lower()], 4))

    chosen = set(selected.name)
    for i, name in enumerate(order):
        ws.cell(FIRST_GP_ROW + i, 6, 1 if name in chosen else 0)

    # Deviations, so the sheet opens showing the solution rather than zeros.
    totals = {
        "performance": selected.value.sum(),
        "workload": selected.workload.sum(),
        "cost": selected.cost.sum(),
    }
    for i, goal in enumerate(("performance", "workload", "cost")):
        _, target = cfg.UNWANTED[goal]
        gap = target - totals[goal]
        ws.cell(51 + i, 4, max(gap, 0.0))      # under
        ws.cell(51 + i, 5, max(-gap, 0.0))     # over

    note = ("Pre-emptive: run Solver three times, minimising B55, then C55, then "
            "D55, holding each earlier result as a constraint."
            if preemptive else
            "Weighted: one run, minimising B55.")
    ws["I5"] = note
    ws["I6"] = (f"Targets come from src/config.py. Performance is {cfg.TARGET_PERFORMANCE}, "
                f"set from check_feasibility and check_conflict.")


def write_simulation(ws):
    ws["B3"] = cfg.TARGET_WORKLOAD
    ws["B4"] = cfg.SIM_SPREAD


# --- the Solver model on the DEA sheet ------------------------------------

def rewrite_dea_solver(path, first, last):
    """Point the DEA sheet's Solver model at the new layout.

    The model lives in hidden defined names scoped to the sheet. openpyxl
    keeps them but offers no way to change them, so the saved file is edited
    directly. Two constraints now: the peer limits, and the weight shares.
    """
    sheet = SHEET_INDEX["DEA"]
    wanted = {
        "solver_opt": "DEA!$B$19",
        "solver_adj": "DEA!$B$6:$B$9",
        "solver_num": "2",
        "solver_typ": "1",                       # maximise
        "solver_eng": "2",                       # Simplex LP
        "solver_neg": "1",                       # weights stay non-negative
        "solver_lhs1": f"DEA!$K${first}:$K${last}",
        "solver_rel1": "1",                      # <=
        "solver_rhs1": f"DEA!$L${first}:$L${last}",
        "solver_lhs2": "DEA!$G$6:$H$9",
        "solver_rel2": "3",                      # >=
        "solver_rhs2": "0",
    }

    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    xml = parts["xl/workbook.xml"].decode("utf-8")

    def replace(match):
        name = match.group("name")
        sid = match.group("sid")
        if sid is not None and int(sid) == sheet and name in wanted:
            seen.add(name)
            return f'{match.group("open")}{wanted[name]}</definedName>'
        return match.group(0)

    pattern = re.compile(
        r'(?P<open><definedName name="(?P<name>solver_[^"]+)"'
        r'(?: localSheetId="(?P<sid>\d+)")?[^>]*>)[^<]*</definedName>'
    )
    seen = set()
    xml = pattern.sub(replace, xml)

    missing = [n for n in wanted if n not in seen]
    if missing:
        block = "".join(
            f'<definedName name="{n}" localSheetId="{sheet}" hidden="1">'
            f'{wanted[n]}</definedName>'
            for n in missing
        )
        if "<definedNames>" in xml:
            xml = xml.replace("<definedNames>", "<definedNames>" + block, 1)
        else:
            xml = xml.replace("<sheets>", "<definedNames>" + block + "</definedNames><sheets>", 1)

    parts["xl/workbook.xml"] = xml.encode("utf-8")
    # calcChain no longer matches the rewritten formulas; Excel rebuilds it.
    parts.pop("xl/calcChain.xml", None)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, blob in parts.items():
            if name == "[Content_Types].xml":
                blob = blob.replace(
                    b'<Override PartName="/xl/calcChain.xml" '
                    b'ContentType="application/vnd.openxmlformats-officedocument.'
                    b'spreadsheetml.calcChain+xml"/>', b"")
            z.writestr(name, blob)

    return missing


def main() -> None:
    import openpyxl

    if not os.path.exists(f"{cfg.PROCESSED}/squad_weighted.csv"):
        raise SystemExit("run stage 07 first; there is nothing to export")

    league = pd.read_parquet(f"{cfg.PROCESSED}/players_season.parquet")
    for c in OUTPUTS:
        league[c] = league[c].fillna(0)

    players = cfg.selectable(pd.read_parquet(f"{cfg.PROCESSED}/squad_value.parquet"))
    weighted = pd.read_csv(f"{cfg.PROCESSED}/squad_weighted.csv")
    preemptive = pd.read_csv(f"{cfg.PROCESSED}/squad_preemptive.csv")
    weights = measure_weights()

    # Taken once only. A second run must not overwrite the original build
    # with a copy of its own output.
    backup = WORKBOOK.replace(".xlsx", "_first_build.xlsx")
    if os.path.exists(backup):
        print(f"original build already kept at {backup}")
    else:
        shutil.copyfile(WORKBOOK, backup)
        print(f"original build kept at {backup}")

    wb = openpyxl.load_workbook(WORKBOOK)
    order = write_data(wb["Data"], players)
    first, last, n_peers = write_dea(wb["DEA"], league, weights)
    write_goal_sheet(wb["GP Weighted"], order, weighted, preemptive=False)
    write_goal_sheet(wb["GP Pre-emptive_"], order, preemptive, preemptive=True)
    write_simulation(wb["Simulation"])
    wb.save(WORKBOOK)

    added = rewrite_dea_solver(WORKBOOK, first, last)

    print()
    print("--- written ---")
    print(f"Data              {len(order)} players, value as a formula over "
          f"efficiency and score")
    print(f"DEA               {DEA_PLAYER} against {n_peers} {DEA_ROLE}s, "
          f"rows {first} to {last}")
    print(f"GP Weighted       target {cfg.TARGET_PERFORMANCE}, "
          f"{len(weighted)} players selected")
    print(f"GP Pre-emptive_   target {cfg.TARGET_PERFORMANCE}, "
          f"{len(preemptive)} players selected")
    print(f"Simulation        ceiling {cfg.TARGET_WORKLOAD:,}, "
          f"spread {cfg.SIM_SPREAD:.0%}")
    print(f"Solver model on the DEA sheet rewritten"
          f"{', added ' + ', '.join(sorted(added)) if added else ''}")
    print()
    print("Left alone: AHP (judgements unchanged) and Scoring (reads the AHP "
          "sheet live, and its positional bests come from the same data).")


if __name__ == "__main__":
    main()
