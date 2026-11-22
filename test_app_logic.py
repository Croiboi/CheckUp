"""Run with: python -m pytest -q"""
from datetime import datetime, timezone
from pathlib import Path

import pytest

import data_service
import elo
import ui
from teams import TEAMS

CSV = Path(__file__).with_name("nba_2026_27.csv")
NOW = datetime(2026, 11, 22, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def model():
    return elo.fit_current_state(elo.load_games(CSV))


def sched_game(gid, home, away, tip, status=1):
    return {"game_id": gid, "home": home, "away": away, "tipoff_utc": tip, "status": status}


def test_probabilities_sum_to_100_for_every_pair(model):
    ratings, form = model
    for a in TEAMS:
        for b in TEAMS:
            if a == b:
                continue
            for neutral in (False, True):
                for use_form in (False, True):
                    r = elo.predict_matchup(ratings, form, a, b, neutral, use_form)
                    assert 0 < r["home_prob"] < 1
                    assert r["home_prob"] + r["away_prob"] == pytest.approx(1.0)
                    pct_a = round(r["home_prob"] * 100, 1)
                    assert round(pct_a + round(100 - pct_a, 1), 1) == 100.0


def test_swapping_dropdown_order_keeps_real_home_team(model):
    ratings, form = model
    games = [sched_game("0022600500", "BOS", "NYK", "2026-12-01T00:30:00+00:00")]
    g1 = data_service.next_game(games, "NYK", "BOS", NOW)
    g2 = data_service.next_game(games, "BOS", "NYK", NOW)
    assert g1 == g2 and g1["home"] == "BOS"
    p = elo.predict_matchup(ratings, form, g1["home"], g1["away"])
    q = elo.predict_matchup(ratings, form, g2["home"], g2["away"])
    assert p == q
    assert p["home_prob"] > elo.predict_matchup(
        ratings, form, "BOS", "NYK", neutral=True)["home_prob"]


def test_next_game_skips_past_started_and_preseason():
    games = [
        sched_game("0022600001", "NYK", "BOS", "2026-11-01T00:00:00+00:00", status=3),
        sched_game("0012600001", "NYK", "BOS", "2026-11-25T00:00:00+00:00"),
        sched_game("0022600900", "BOS", "NYK", "2027-01-10T00:00:00+00:00"),
        sched_game("0022600800", "NYK", "BOS", "2026-12-20T00:00:00+00:00"),
    ]
    assert data_service.next_game(games, "BOS", "NYK", NOW)["game_id"] == "0022600800"


def test_tipoff_is_shown_in_eastern_time():
    g = sched_game("x", "BOS", "NYK", "2026-11-25T00:30:00+00:00")
    assert data_service.format_tipoff(g) == ("Tue, Nov 24, 2026", "7:30 PM EST")


def test_parse_schedule_handles_utc_and_eastern_fields():
    payload = {"leagueSchedule": {"gameDates": [{"games": [
        {"gameId": "1", "gameStatus": 1, "gameDateTimeUTC": "2026-11-25T00:30:00Z",
         "homeTeam": {"teamTricode": "BOS"}, "awayTeam": {"teamTricode": "NYK"}},
        {"gameId": "2", "gameStatus": 1, "gameDateTimeEst": "2026-11-24T19:30:00Z",
         "homeTeam": {"teamTricode": "BOS"}, "awayTeam": {"teamTricode": "NYK"}},
        {"gameId": "3", "gameStatus": 1, "gameDateTimeUTC": "2026-11-25T00:30:00Z",
         "homeTeam": {"teamTricode": ""}, "awayTeam": {"teamTricode": "NYK"}},
    ]}]}}
    parsed = data_service.parse_schedule(payload)
    assert len(parsed) == 2
    assert data_service.format_tipoff(parsed[0]) == data_service.format_tipoff(parsed[1])


def test_missing_schedule_still_allows_simulation(model, tmp_path):
    def boom():
        raise TimeoutError("timed out")
    s = data_service.load_schedule(fetch=boom, cache_file=tmp_path / "none.json")
    assert s.games == [] and s.fetched_at is None and s.error
    assert data_service.next_game(s.games, "NYK", "BOS", NOW) is None
    ratings, form = model
    for neutral in (False, True):
        r = elo.predict_matchup(ratings, form, "NYK", "BOS", neutral, True)
        assert r["home_prob"] + r["away_prob"] == pytest.approx(1.0)


def test_timeout_keeps_last_saved_schedule(tmp_path):
    payload = {"leagueSchedule": {"gameDates": [{"games": [
        {"gameId": "2", "gameStatus": 1, "gameDateTimeUTC": "2026-12-01T00:30:00Z",
         "homeTeam": {"teamTricode": "BOS"}, "awayTeam": {"teamTricode": "NYK"}}]}]}}
    cache = tmp_path / "s.json"
    ok = data_service.load_schedule(fetch=lambda: payload, cache_file=cache)
    assert not ok.stale and len(ok.games) == 1

    def boom():
        raise TimeoutError("timed out")
    stale = data_service.load_schedule(fetch=boom, cache_file=cache)
    assert stale.stale and stale.games == ok.games and stale.fetched_at == ok.fetched_at


# ---------------------------------------------------------- venue resolution
def test_resolve_home_away_scheduled_game_ignores_dropdown_order_and_venue():
    g = sched_game("0022600500", "BOS", "NYK", "2026-12-01T00:30:00+00:00")
    for a, b in (("NYK", "BOS"), ("BOS", "NYK")):
        for venue in ("a_home", "b_home", "neutral"):
            assert data_service.resolve_home_away(g, a, b, venue) == ("BOS", "NYK", False)


def test_resolve_home_away_hypothetical_modes():
    assert data_service.resolve_home_away(None, "NYK", "BOS", "a_home") == ("NYK", "BOS", False)
    assert data_service.resolve_home_away(None, "NYK", "BOS", "b_home") == ("BOS", "NYK", False)
    assert data_service.resolve_home_away(None, "NYK", "BOS", "neutral") == ("NYK", "BOS", True)


def test_neutral_court_removes_the_home_edge_for_real_teams(model):
    ratings, form = model
    s = {"home_bonus": 50, "carryover": 1.0, "form_weight": 2.0}
    home_court = elo.predict_matchup(ratings, form, "NYK", "BOS", False, False, s)
    neutral = elo.predict_matchup(ratings, form, "NYK", "BOS", True, False, s)
    flipped = elo.predict_matchup(ratings, form, "BOS", "NYK", True, False, s)
    assert home_court["home_prob"] > neutral["home_prob"]
    assert neutral["home_prob"] + flipped["home_prob"] == pytest.approx(1.0)
    assert neutral["home_prob"] == pytest.approx(neutral["p_elo"])


# ------------------------------------------------------------------ UI strings
def _side(name, abbr, pct, tag="HOME", color="#F58426"):
    return {"name": name, "abbr": abbr, "pct": pct, "tag": tag, "color": color,
            "rating": 1512.4, "form": 3.25}


def test_split_percentages_always_total_exactly_100():
    for i in range(0, 1001):
        a, b = ui.split_percentages(i / 1000)
        assert round(a + b, 1) == 100.0


def test_hero_html_is_one_markdown_safe_block_with_both_probabilities():
    a, b = ui.split_percentages(0.5437)
    out = ui.hero_html(_side("New York Knicks", "NYK", a), _side("Boston Celtics", "BOS", b, "AWAY"))
    assert "\n" not in out and "$" not in out
    assert "54.4%" in out and "45.6%" in out and "VS" in out and 'role="img"' in out
    assert out.count('class="card"') == 2


def test_dynamic_text_is_escaped():
    bar = ui.top_bar_html("Nov 21, 2026", "<script>alert(1)</script>", "stale")
    assert "<script>" not in bar and "&lt;script&gt;" in bar
    assert "<script>" not in ui.schedule_strip_html(reason="<b>x</b>")


def test_breakdown_greys_out_form_when_off_and_steps_chain():
    on = ui.breakdown_html("A", "B", 1520, 1490,
                           [("Elo", 0.55, True), ("Home", 0.60, True), ("Form", 0.62, True)], True)
    off = ui.breakdown_html("A", "B", 1520, 1490,
                            [("Elo", 0.55, True), ("Home", 0.60, True), ("Form", 0.62, False)], False)
    assert "+5.0 pts" in on and "+2.0 pts" in on
    assert 'class="off"' in off and "Recent form is off" in off and "Recent form is off" not in on


def test_performance_panel_lists_each_model_with_score_and_game_count():
    report = elo.select_model(elo.load_games(CSV))
    out = ui.performance_html(report)
    n = report["models"][0]["games"]
    for m in report["models"]:
        assert m["label"] in out and f"{m['brier']:.4f}" in out
    assert f"{n:,}" in out and "Brier score" in out and "0.2500" in out
    assert "fetch_data.py --history" in out            # one season only -> warns
    assert "Validation" in out and "Test" in out
    assert "<table" in ui.search_html(report) or "mini" in ui.search_html(report)


def test_outside_estimate_comparison_math():
    c = ui.outside_comparison("Detroit Pistons", 0.466, 0.59)
    assert c["gap_pts"] == pytest.approx(-12.4)
    assert c["win"] == pytest.approx(((1 - .466) ** 2, (1 - .59) ** 2))
    assert c["lose"] == pytest.approx((.466 ** 2, .59 ** 2))
    assert "-12.4" in ui.outside_html("Detroit Pistons", 0.466, 0.59)


def test_distinct_colors_swaps_lookalikes_only():
    assert ui.distinct_colors("#CE1141", "#CE1141")[1] == ui.NEUTRAL_ACCENT
    assert ui.distinct_colors("#F58426", "#11A851") == ("#F58426", "#11A851")


def test_format_updated_is_eastern_time():
    assert data_service.format_updated(datetime(2026, 11, 22, 20, 12, tzinfo=timezone.utc)) \
        == "Nov 22, 3:12 PM EST"
