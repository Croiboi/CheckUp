"""API tests. Run with: python -m unittest test_api  (or python -m pytest -q)"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ["CHECKUP_NOW"] = "2026-11-22T11:00:00+00:00"

import api  # noqa: E402
import elo  # noqa: E402
import team_profile  # noqa: E402


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = api.app.test_client()

    def get(self, url):
        r = self.c.get(url)
        return r.status_code, r.get_json()

    def test_meta_lists_all_thirty_teams(self):
        status, meta = self.get("/api/meta")
        self.assertEqual(status, 200)
        self.assertEqual(len(meta["teams"]), 30)

    def test_slate_features_the_closest_game_and_percentages_total_100(self):
        _, slate = self.get("/api/slate")
        self.assertTrue(slate["games"])
        for g in slate["games"]:
            self.assertAlmostEqual(g["home"]["pct"] + g["away"]["pct"], 100.0, places=1)
        gap = lambda g: abs(g["home"]["pct"] - 50)  # noqa: E731
        featured = next(g for g in slate["games"] if g["id"] == slate["featuredId"])
        self.assertEqual(gap(featured), min(gap(g) for g in slate["games"]))

    def test_team_schedule_stays_inside_the_14_day_window(self):
        _, data = self.get("/api/team/NYK/schedule")
        self.assertTrue(0 < len(data["games"]) <= 14)
        self.assertTrue(all(0 < g["pct"] < 100 for g in data["games"]))

    def test_matchup_matches_the_elo_module(self):
        _, m = self.get("/api/matchup?a=NYK&b=BOS&form=1")
        model = api.report()
        home = "BOS" if m["game"] and m["a"]["tag"] == "Away" else "NYK"
        away = "NYK" if home == "BOS" else "BOS"
        expected = elo.predict_matchup(model["ratings"], model["form"], home, away, False, True, model["selected"])
        p_a = expected["away_prob"] if home == "BOS" else expected["home_prob"]
        self.assertAlmostEqual(m["a"]["pct"], round(p_a * 100, 1), places=1)
        self.assertAlmostEqual(m["a"]["pct"] + m["b"]["pct"], 100.0, places=1)

    def test_swapping_teams_swaps_probabilities(self):
        _, one = self.get("/api/matchup?a=NYK&b=BOS")
        _, two = self.get("/api/matchup?a=BOS&b=NYK")
        self.assertEqual(one["a"]["pct"], two["b"]["pct"])

    def test_bad_input_gets_clear_errors(self):
        self.assertEqual(self.get("/api/matchup?a=NYK&b=NYK")[0], 400)
        self.assertEqual(self.get("/api/team/ZZZ/schedule")[0], 404)
        status, body = self.get("/api/nope")
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_roster_is_ranked_by_scoring_and_top_three_come_from_it(self):
        original = (team_profile.fetch_roster, team_profile.fetch_player_averages)
        team_profile.fetch_roster = lambda t, s: [
            {"PLAYER_ID": i, "Jersey": str(i), "Player": f"P{i}", "Position": "G"} for i in range(1, 6)]
        team_profile.fetch_player_averages = lambda t, s: {
            1: {"GP": 9, "MIN": 30, "PTS": 10, "REB": 1, "AST": 1}, 2: {"GP": 9, "MIN": 30, "PTS": 25, "REB": 1, "AST": 1},
            3: {"GP": 9, "MIN": 30, "PTS": 18, "REB": 1, "AST": 1}, 4: {"GP": 9, "MIN": 30, "PTS": 12, "REB": 1, "AST": 1}}
        api._cache.clear()
        try:
            _, r = self.get("/api/team/BOS/roster")
            self.assertEqual([p["name"] for p in r["topScorers"]], ["P2", "P3", "P4"])
            self.assertEqual(r["players"][-1]["name"], "P5")  # no stats: last
        finally:
            team_profile.fetch_roster, team_profile.fetch_player_averages = original
            api._cache.clear()

    def test_unavailable_upstream_is_reported_not_raised(self):
        api._cache.clear()
        _, r = self.get("/api/team/NYK/roster")  # nba_api may be missing or offline
        self.assertIn("rosterUnavailable", r)

    def test_spa_fallback_serves_index_but_never_files_outside_dist(self):
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp) / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("<div id=root></div>")
            (Path(tmp) / "secret.txt").write_text("nope")
            old, api.DIST = api.DIST, dist
            try:
                self.assertIn("root", self.c.get("/teams/NYK").get_data(as_text=True))
                self.assertNotIn("nope", self.c.get("/..%2fsecret.txt").get_data(as_text=True))
                self.assertEqual(self.c.get("/api/anything").status_code, 404)
            finally:
                api.DIST = old


if __name__ == "__main__":
    unittest.main()
