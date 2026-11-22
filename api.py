"""CheckUp JSON API: a thin layer over the existing prediction and data modules.

elo.py, data_service.py, team_profile.py, player_watch.py and teams.py are used
as-is. This file only decides what to cache and how to shape the JSON, mirroring
the decisions app.py makes for Streamlit.

Run:  python api.py          (API on http://127.0.0.1:8000)
After `npm run build` in frontend/, the same process also serves the built site.
"""

import os
import threading
import time
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory

import data_service
import elo
import player_watch
import team_profile
import ui
from teams import NAME_TO_ABBR, TEAMS

ROOT = Path(__file__).parent
DIST = ROOT / "frontend" / "dist"
CSV_PATH = elo.DEFAULT_CSV

app = Flask(__name__, static_folder=None)


def now():
    """Current UTC time. CHECKUP_NOW=2026-11-22T15:00:00+00:00 pins it for testing."""
    pinned = os.environ.get("CHECKUP_NOW")
    return datetime.fromisoformat(pinned) if pinned else datetime.now(timezone.utc)


# ------------------------------------------------------------------- caching
_lock = threading.RLock()
_cache = {}


def cached(key, ttl, build):
    with _lock:
        hit = _cache.get(key)
        if hit and (ttl is None or time.time() - hit[0] < ttl):
            return hit[1]
    value = build()
    with _lock:
        _cache[key] = (time.time(), value)
    return value


def fingerprint():
    files = elo.history_files() + ([CSV_PATH] if CSV_PATH.exists() else [])
    return tuple((str(p), p.stat().st_mtime) for p in files)


def report():
    def build():
        return elo.select_model(elo.load_history(CSV_PATH))
    return cached(("report", fingerprint()), None, build)


def schedule():
    if os.getenv("VERCEL"):
        try:
            games, fetched_at = data_service._read_cache(data_service.CACHE_FILE)
            return data_service.Schedule(games, fetched_at)
        except (OSError, ValueError, KeyError, TypeError):
            pass

    return cached("schedule", 1800, data_service.load_schedule)


def player_leaders():
    def build():
        try:
            games = elo.load_games(CSV_PATH)
            recent = player_watch.recent_team_games(games)
            start = min(g["date"] for tg in recent.values() for g in tg)
            logs = player_watch.fetch_logs(data_service.SEASON, start, games[-1]["date"])
            return player_watch.find_leaders(recent, logs), None
        except Exception as exc:
            return {}, type(exc).__name__
    return cached(("leaders", CSV_PATH.stat().st_mtime_ns if CSV_PATH.exists() else 0), 900, build)


def roster_for(team):
    def build():
        try:
            return team_profile.fetch_roster(team, data_service.SEASON), False
        except Exception:
            return [], True
    return cached(("roster", team), 900, build)


def averages_for(team):
    def build():
        try:
            return team_profile.fetch_player_averages(team, data_service.SEASON), False
        except Exception:
            return {}, True
    return cached(("averages", team), 900, build)


# ------------------------------------------------------------------- helpers
def use_form():
    return request.args.get("form") == "1"


def team_or_404(abbr):
    abbr = abbr.upper()
    if abbr not in TEAMS:
        abort(404, description="Unknown team")
    return abbr


def team_json(abbr):
    return {"abbr": abbr, "name": TEAMS[abbr][0], "color": TEAMS[abbr][1]}


def predict(team, home, away, neutral, form_on):
    model = report()
    result = elo.predict_matchup(model["ratings"], model["form"], home, away, neutral,
                                 form_on, model["selected"])
    return result, result["home_prob"] if team == home else result["away_prob"]


def eastern_day(game):
    return datetime.fromisoformat(game["tipoff_utc"]).astimezone(data_service.EASTERN).date()


def tipoff_json(game):
    day, time_ = data_service.format_tipoff(game)
    return {"day": day, "time": time_, "utc": game["tipoff_utc"]}


def through_label():
    return datetime.strptime(report()["latest_date"], "%Y-%m-%d").strftime("%b %d, %Y")


def leader_json(leader):
    if not leader:
        return None
    return {"name": leader["name"], "playerId": leader.get("player_id"),
            "points": leader["points"], "rebounds": leader["rebounds"],
            "assists": leader["assists"], "games": leader["games"], "window": leader["window"]}


# ----------------------------------------------------------------------- meta
@app.get("/api/meta")
def meta():
    games = elo.load_history(CSV_PATH)
    latest = max((game["date"] for game in games), default=None)
    results_through = (
        datetime.strptime(latest, "%Y-%m-%d").strftime("%b %d, %Y")
        if latest else "No results yet"
    )

    schedule_status = {"label": "Schedule unavailable", "state": "none"}
    try:
        _, fetched_at = data_service._read_cache(data_service.CACHE_FILE)
        schedule_status = {
            "label": f"Saved schedule · {data_service.format_updated(fetched_at)}",
            "state": "stale",
        }
    except (OSError, ValueError, KeyError, TypeError):
        pass

    return jsonify({
        "teams": [team_json(a) for a in sorted(TEAMS, key=lambda a: TEAMS[a][0])],
        "resultsThrough": results_through,
        "schedule": schedule_status,
        "season": data_service.SEASON,
        "windowDays": data_service.SCHEDULE_WINDOW_DAYS,
    })


# ---------------------------------------------------------------------- home
@app.get("/api/slate")
def slate():
    sched = schedule()
    upcoming = [g for g in data_service.upcoming_games(sched.games, now=now(), days=None)
                if g["home"] in TEAMS and g["away"] in TEAMS]
    if not upcoming:
        return jsonify({"games": [], "reason": "No upcoming games are listed."
                        if sched.games else "Schedule data is unavailable."})
    day = eastern_day(upcoming[0])
    todays = [g for g in upcoming if eastern_day(g) == day]
    today = now().astimezone(data_service.EASTERN).date()
    games = []
    for g in todays:
        home, away, neutral = data_service.resolve_home_away(g, g["home"], g["away"])
        _, p_home = predict(home, home, away, neutral, use_form())
        home_pct, away_pct = ui.split_percentages(p_home)
        games.append({"id": g["game_id"], "tipoff": tipoff_json(g), "neutral": neutral,
                      "away": {**team_json(away), "pct": away_pct},
                      "home": {**team_json(home), "pct": home_pct}, "_gap": abs(p_home - .5)})
    featured = min(games, key=lambda g: g["_gap"])["id"]
    for g in games:
        g.pop("_gap")
    return jsonify({"title": "Today’s games" if day == today else "Next game day",
                    "date": day.strftime("%a, %b %d"), "featuredId": featured, "games": games})


# ------------------------------------------------------------ team schedule
@app.get("/api/team/<abbr>/schedule")
def team_schedule(abbr):
    team = team_or_404(abbr)
    sched = schedule()
    rows = []
    for g in data_service.upcoming_games(sched.games, team, now()):
        home, away, neutral = data_service.resolve_home_away(g, team, team)
        opponent = away if team == home else home
        if opponent not in TEAMS:
            continue
        _, p = predict(team, home, away, neutral, use_form())
        rows.append({"id": g["game_id"], "tipoff": tipoff_json(g), "opponent": team_json(opponent),
                     "venue": "Neutral" if neutral else "Home" if team == home else "Away",
                     "pct": ui.split_percentages(p)[0]})
    reason = None
    if not rows:
        reason = ("No scheduled games in the next 14 days." if sched.games
                  else "The NBA schedule is unavailable right now.")
    return jsonify({"team": team_json(team), "through": through_label(), "games": rows, "reason": reason})


# ------------------------------------------------------------------- matchup
def find_game(a, b, game_id):
    sched = schedule()
    if game_id:
        for g in data_service.upcoming_games(sched.games, a, now(), days=None):
            if g["game_id"] == game_id and b in (g["home"], g["away"]):
                return g
    return data_service.next_game(sched.games, a, b, now())


@app.get("/api/matchup")
def matchup():
    a, b = team_or_404(request.args.get("a", "")), team_or_404(request.args.get("b", ""))
    if a == b:
        abort(400, description="Choose two different teams")
    venue = request.args.get("venue", "a_home")
    if venue not in ("a_home", "b_home", "neutral"):
        venue = "a_home"
    form_on = use_form()
    model, sched = report(), schedule()
    game = find_game(a, b, request.args.get("game"))
    home, away, neutral = data_service.resolve_home_away(game, a, b, venue)
    result, p_a = predict(a, home, away, neutral, form_on)
    pct_a, pct_b = ui.split_percentages(p_a)
    color_a, color_b = ui.distinct_colors(TEAMS[a][1], TEAMS[b][1])

    def side(abbr, pct, color):
        return {**team_json(abbr), "color": color, "pct": pct,
                "tag": "Neutral" if neutral else "Home" if abbr == home else "Away",
                "rating": model["ratings"].get(abbr, elo.START_RATING),
                "form": elo.recent_form(model["form"], abbr)}

    def for_a(p_home_side):
        return p_home_side if a == home else 1 - p_home_side

    steps = [
        ("Elo ratings only", for_a(result["p_elo"]), True),
        ("Neutral court: no home bonus" if neutral
         else f"Home court (+{result['home_bonus']} Elo to {TEAMS[home][0]})",
         for_a(result["p_with_home"]), True),
        (f"Recent form (weight {model['selected']['form_weight']:g})",
         for_a(result["p_with_form"]), form_on),
    ]
    out_steps, previous = [], None
    for label, p, applied in steps:
        pa, pb = ui.split_percentages(p)
        out_steps.append({"label": label, "a": pa, "b": pb, "applied": applied,
                          "delta": None if previous is None else round((p - previous) * 100, 1)})
        if applied:
            previous = p
    shift = (result["p_with_form"] - result["p_with_home"]) * 100
    leaders, leaders_error = player_leaders()
    return jsonify({
        "a": side(a, pct_a, color_a), "b": side(b, pct_b, color_b),
        "game": ({**tipoff_json(game), "id": game["game_id"],
                  "homeName": "Neutral court" if game.get("neutral") else TEAMS[game["home"]][0],
                  "early": datetime.fromisoformat(game["tipoff_utc"])
                  > now() + timedelta(days=data_service.SCHEDULE_WINDOW_DAYS)} if game else None),
        "reason": None if game else ("No upcoming game between these teams on the schedule."
                                     if sched.games else "The NBA schedule is unavailable right now."),
        "venue": venue, "formOn": form_on,
        "formShift": round(shift if a == home else -shift, 1),
        "steps": out_steps,
        "watch": {"error": bool(leaders_error), "a": leader_json(leaders.get(a)),
                  "b": leader_json(leaders.get(b))},
    })


# ---------------------------------------------------------------- team stats
@app.get("/api/team/<abbr>/profile")
def team_stats(abbr):
    team = team_or_404(abbr)
    stats = (team_profile.season_stats(elo.load_games(CSV_PATH), team)
             if CSV_PATH.is_file() else None)
    if stats:
        stats["results"] = [{**g, "opponentName": TEAMS.get(g["opponent"], (g["opponent"],))[0]}
                            for g in stats["results"]]
    return jsonify({"team": team_json(team), "through": through_label(), "stats": stats})


@app.get("/api/team/<abbr>/roster")
def team_roster(abbr):
    team = team_or_404(abbr)
    snapshot = ROOT / "roster_snapshots" / f"{team}.json"
    if snapshot.is_file():
        return jsonify(json.loads(snapshot.read_text(encoding="utf-8")))
    roster, roster_down = roster_for(team)
    averages, averages_down = averages_for(team)
    players = []
    for p in roster:
        pid = int(p["PLAYER_ID"])
        s = averages.get(pid)
        players.append({
            "id": pid, "name": p["Player"], "jersey": str(p["Jersey"]), "position": p["Position"],
            "stats": {k: float(s[k]) for k in ("PTS", "REB", "AST", "MIN", "GP")} if s else None})
    players.sort(key=lambda p: (-(p["stats"]["PTS"] if p["stats"] else -1), p["name"]))
    return jsonify({"team": team_json(team), "players": players,
                    "topScorers": [p for p in players if p["stats"]][:3],
                    "rosterUnavailable": roster_down, "averagesUnavailable": averages_down,
                    "noRoster": not roster and not roster_down})


# ------------------------------------------------------------- model + data
@app.get("/api/performance")
def performance():
    r = report()
    sp = r["splits"]
    warn = None
    if len(r["seasons"]) < 2:
        warn = ("Only the current season is loaded, so the validation period is tiny and the "
                "chosen settings are noisy. Run python fetch_data.py --history to add past seasons.")
    elif sp["test"]["games"] < 500:
        warn = "The test period is small, so differences may be noise."
    models = [{**m, "verdict": None if m["key"] == "elo" else ui._verdict(m["diff_vs_elo"], m["diff_se"]),
               "best": m["brier"] == min(x["brier"] for x in r["models"])} for m in r["models"]]
    rows = lambda d: [{"key": k, "value": v} for k, v in d.items()]  # noqa: E731
    return jsonify({
        "selected": r["selected"], "models": models, "coinFlip": r["coin_flip"], "splits": sp,
        "warning": warn, "gameCount": r["game_count"], "seasons": r["seasons"],
        "bonusAtEdge": r["selected"]["home_bonus"] == max(elo.BONUS_GRID),
        "search": {"bonus": rows(r["search"]["bonus"]), "carryover": rows(r["search"]["carryover"]),
                   "formWeight": rows(r["search"]["form_weight"]), "noForm": r["search"]["no_form"]},
    })


@app.get("/api/data")
def data_status():
    sched = schedule()
    return jsonify({"through": through_label(), "historyFiles": len(elo.history_files()),
                    "scheduleStale": sched.stale, "scheduleFetched": bool(sched.fetched_at),
                    "scheduleError": sched.error})


@app.post("/api/refresh")
def refresh():
    messages = []
    try:
        n = data_service.refresh_results(CSV_PATH)
        messages.append({"kind": "success", "text": f"Current-season results updated ({n:,} games)."})
    except Exception as exc:
        messages.append({"kind": "warning", "text": "Couldn’t update current-season results "
                         f"({type(exc).__name__}); using the last saved CSV."})
    try:
        status = data_service.refresh_history()
        got = [s for s, r in status.items() if r == "downloaded"]
        bad = [s for s, r in status.items() if r.startswith("failed")]
        if got:
            messages.append({"kind": "success", "text": "Downloaded past seasons: " + ", ".join(got)})
        if bad:
            messages.append({"kind": "warning", "text": "Couldn’t download: " + ", ".join(bad)
                             + ". Cached seasons are still in use."})
    except Exception as exc:
        messages.append({"kind": "warning", "text": f"Past-season download skipped ({type(exc).__name__})."})
    with _lock:
        _cache.clear()
    return jsonify({"messages": messages})


# ------------------------------------------------------------- static + SPA
@app.get("/api/logos/<abbr>.svg")
def logo(abbr):
    team_or_404(abbr)
    response = send_from_directory(ROOT / "logos", f"{abbr.upper()}.svg", mimetype="image/svg+xml")
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.errorhandler(404)
@app.errorhandler(400)
def api_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": error.description}), error.code
    return error


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def spa(path):
    if path.startswith("api/"):
        abort(404, description="Unknown endpoint")
    if not DIST.is_dir():
        return ("The React frontend isn't built yet. Run `npm run dev` in frontend/ "
                "(http://localhost:5173) or `npm run build` here.", 404)
    target = DIST / path
    if path and target.is_file() and DIST in target.resolve().parents:
        return send_from_directory(DIST, path)
    return send_from_directory(DIST, "index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8000)), debug=False)
