"""Model tests. Run with: python -m pytest -q

The multi-season data here is SYNTHETIC (known home advantage, team strengths that
drift between seasons). It checks the logic of the backtest, not real NBA behavior.
"""
import copy
import hashlib
import random
from datetime import date, timedelta
from functools import lru_cache
from math import sqrt
from pathlib import Path

import pytest

import elo
from teams import TEAMS

CSV = Path(__file__).with_name("nba_2026_27.csv")


@lru_cache(maxsize=None)
def _synthetic(seasons=6, seed=7, home_adv_pts=2.5, persistence=0.7):
    rng = random.Random(seed)
    teams = list(TEAMS)
    sd = 110
    strength = {t: rng.gauss(0, sd) for t in teams}
    games, gid = [], 0
    for s in range(seasons):
        if s:
            strength = {t: persistence * v + rng.gauss(0, sd * sqrt(1 - persistence ** 2))
                        for t, v in strength.items()}
        start = date(2019 + s, 10, 22)
        for day in range(82):
            order = teams[:]
            rng.shuffle(order)
            for i in range(0, 30, 2):
                home, away = order[i], order[i + 1]
                margin = int(round(rng.gauss((strength[home] - strength[away]) / 23
                                             + home_adv_pts, 12))) or 1
                gid += 1
                games.append({"game_id": f"{gid:010d}",
                              "date": (start + timedelta(days=2 * day)).isoformat(),
                              "home_team": home, "away_team": away,
                              "home_pts": str(110 + margin), "away_pts": "110"})
    return tuple(games)


def synth(**kw):
    return [dict(g) for g in _synthetic(**kw)]


def game(day, home, away, home_pts, away_pts, gid):
    return {"game_id": gid, "date": day, "home_team": home, "away_team": away,
            "home_pts": str(home_pts), "away_pts": str(away_pts)}


# ------------------------------------------------------------------ Brier score
def test_brier_known_values():
    assert elo.brier([0.5, 0.5], [1, 0]) == 0.25
    assert elo.brier([1.0, 0.0], [1, 0]) == 0
    assert elo.brier([0.8], [0]) == pytest.approx(0.64)


# --------------------------------------------------------- no peeking at the future
def test_prediction_for_a_game_ignores_later_results():
    games = synth()
    cut = 1500
    altered = copy.deepcopy(games)
    for g in altered[cut + 1:]:                       # reverse every later result
        g["home_pts"], g["away_pts"] = g["away_pts"], g["home_pts"]
    a = elo.simulate(games, 40, 0.75)
    b = elo.simulate(altered, 40, 0.75)
    assert a["gaps"][:cut + 1] == b["gaps"][:cut + 1]
    assert a["form_diffs"][:cut + 1] == b["form_diffs"][:cut + 1]
    assert a["gaps"][cut + 5:] != b["gaps"][cut + 5:]  # sanity: later games do change


def test_game_does_not_use_its_own_result():
    games = synth()
    flipped = copy.deepcopy(games)
    flipped[800]["home_pts"], flipped[800]["away_pts"] = "90", "130"
    a, b = elo.simulate(games), elo.simulate(flipped)
    assert a["gaps"][800] == b["gaps"][800]
    assert a["form_diffs"][800] == b["form_diffs"][800]


def test_splits_are_chronological_and_do_not_overlap():
    games = synth()
    report = elo.select_model(games)
    sp = report["splits"]
    assert sp["warmup"]["games"] + sp["validation"]["games"] + sp["test"]["games"] == len(games)
    assert sp["warmup"]["end"] <= sp["validation"]["start"]
    assert sp["validation"]["end"] <= sp["test"]["start"]
    assert sp["test"]["end"] == games[-1]["date"]
    assert all(m["games"] == sp["test"]["games"] for m in report["models"])


def test_choosing_settings_never_looks_at_the_test_period():
    games = synth()
    n = len(games)
    _, test_lo = elo.split_indices(n)
    scrambled = copy.deepcopy(games)
    for g in scrambled[test_lo:]:
        g["home_pts"], g["away_pts"] = g["away_pts"], g["home_pts"]
    a, b = elo.select_model(games), elo.select_model(scrambled)
    assert a["selected"] == b["selected"]
    assert a["search"] == b["search"]
    assert [m["brier"] for m in a["models"]] != [m["brier"] for m in b["models"]]


# ------------------------------------------------------------ season carryover
def test_carryover_moves_ratings_toward_1500_at_new_season_only():
    games = [game("2026-11-01", "AAA", "BBB", 110, 100, "1"),    # A wins: 1510 / 1490
             game("2026-11-03", "AAA", "BBB", 100, 110, "2"),    # same season, no reset
             game("2027-11-01", "AAA", "BBB", 110, 100, "3")]    # new season
    same = elo.simulate(games, home_bonus=0, carryover=1.0)
    half = elo.simulate(games, home_bonus=0, carryover=0.5)
    assert same["gaps"][1] == half["gaps"][1] == pytest.approx(20)   # untouched mid-season
    assert half["gaps"][2] == pytest.approx(0.5 * same["gaps"][2])   # halfway to 1500
    assert elo.simulate(games, 0, 0.0)["gaps"][2] == 0               # full reset


def test_last_five_form_resets_in_a_new_season():
    games = [game("2026-11-01", "AAA", "BBB", 130, 100, "1"),
             game("2027-11-01", "AAA", "BBB", 110, 100, "2")]
    assert elo.simulate(games)["form_diffs"] == [0, 0]


# ---------------------------------------------------- selection on synthetic data
def test_selection_recovers_known_home_advantage_and_regression():
    report = elo.select_model(synth())
    sel = report["selected"]
    assert sel["home_bonus"] in elo.BONUS_GRID and sel["home_bonus"] >= 30   # true ~57
    assert sel["carryover"] < 1.0                     # strengths drift between seasons
    elo_m, home_m, form_m = report["models"]
    assert home_m["brier"] < elo_m["brier"]           # home court helps when it exists
    assert [m["key"] for m in report["models"]] == ["elo", "home", "form"]
    assert set(report["search"]["bonus"]) == set(elo.BONUS_GRID)
    assert set(report["search"]["carryover"]) == set(elo.CARRYOVER_GRID)


def test_no_home_advantage_selects_a_small_bonus():
    report = elo.select_model(synth(home_adv_pts=0.0, seed=11))
    assert report["selected"]["home_bonus"] <= 20


# ----------------------------------------------------------- predictions / venue
def test_neutral_court_and_venue_symmetry():
    ratings, form = {"AAA": 1560.0, "BBB": 1480.0}, {"AAA": [5, 3], "BBB": [-2]}
    s = {"home_bonus": 50, "carryover": 1.0, "form_weight": 2.0}
    n1 = elo.predict_matchup(ratings, form, "AAA", "BBB", True, False, s)
    n2 = elo.predict_matchup(ratings, form, "BBB", "AAA", True, False, s)
    assert n1["home_prob"] + n2["home_prob"] == pytest.approx(1.0)   # same game, either label
    home = elo.predict_matchup(ratings, form, "AAA", "BBB", False, False, s)
    assert home["home_prob"] > n1["home_prob"]
    assert home["home_bonus"] == 50 and n1["home_bonus"] == 0
    on = elo.predict_matchup(ratings, form, "AAA", "BBB", False, True, s)
    assert on["form_adjustment"] == pytest.approx(2.0 * (4.0 - (-2.0)))
    assert on["home_prob"] == pytest.approx(on["p_with_form"])
    assert home["p_with_form"] == pytest.approx(on["home_prob"])


def test_unknown_team_gets_start_rating():
    r = elo.predict_matchup({}, {}, "AAA", "BBB", neutral=True)
    assert r["home_prob"] == pytest.approx(0.5)


# ------------------------------------------------------------------- data loading
def test_load_history_merges_dedupes_and_never_modifies_current_csv(tmp_path):
    before = hashlib.sha256(CSV.read_bytes()).hexdigest()
    hist = tmp_path / "data"
    hist.mkdir()
    rows = elo.load_games(CSV)
    old = dict(rows[0], game_id="0022100001", date="2021-10-19")
    dup = dict(rows[0])                                  # same id as a current-season game
    for name, items in (("nba_2021_22.csv", [old]), ("nba_2026_27.csv", [dup])):
        with (hist / name).open("w", newline="") as f:
            w = elo.csv.DictWriter(f, fieldnames=list(old))
            w.writeheader()
            w.writerows(items)
    merged = elo.load_history(current_csv=CSV, history_dir=hist)
    ids = [g["game_id"] for g in merged]
    assert len(ids) == len(set(ids)) == len(rows) + 1
    assert merged[0]["game_id"] == "0022100001"
    assert hashlib.sha256(CSV.read_bytes()).hexdigest() == before


def test_current_season_alone_still_produces_a_report():
    report = elo.select_model(elo.load_games(CSV))
    assert report["game_count"] == len(elo.load_games(CSV))
    assert all(0 < m["brier"] < 1 for m in report["models"])
