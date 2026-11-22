"""Schedule lookup, caching, and result refresh for the dashboard."""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

SCHEDULE_URL = "https://stats.nba.com/stats/scheduleleaguev2"
CACHE_FILE = Path(__file__).with_name("schedule_cache.json")
SEASON = "2026-27"
EASTERN = ZoneInfo("America/New_York")
SCHEDULE_WINDOW_DAYS = 14


@dataclass
class Schedule:
    games: list
    fetched_at: datetime | None   # when this data was downloaded (UTC)
    stale: bool = False           # True if the live request failed
    error: str | None = None


def fetch_schedule_payload(timeout=15):
    import requests
    from nba_api.stats.library.http import NBAStatsHTTP

    response = requests.get(
        SCHEDULE_URL,
        params={"LeagueID": "00", "Season": SEASON},
        headers=NBAStatsHTTP.headers,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def _tipoff_utc(game):
    utc = game.get("gameDateTimeUTC")
    if utc:
        return datetime.fromisoformat(utc.replace("Z", "+00:00"))
    est = game.get("gameDateTimeEst")  # Eastern wall-clock time
    if est:
        naive = datetime.fromisoformat(est.replace("Z", ""))
        return naive.replace(tzinfo=EASTERN).astimezone(timezone.utc)
    return None


def parse_schedule(payload):
    """Flatten the NBA schedule JSON into small dicts."""
    games = []
    for day in payload["leagueSchedule"]["gameDates"]:
        for g in day.get("games", []):
            home = (g.get("homeTeam") or {}).get("teamTricode")
            away = (g.get("awayTeam") or {}).get("teamTricode")
            tipoff = _tipoff_utc(g)
            if not home or not away or tipoff is None:
                continue
            games.append({
                "game_id": str(g.get("gameId", "")),
                "tipoff_utc": tipoff.isoformat(),
                "home": home,
                "away": away,
                "neutral": g.get("isNeutral") in (True, "true", "True", "1"),
                "status": int(g.get("gameStatus", 1)),  # 1 = not started
            })
    return games


def _read_cache(cache_file):
    data = json.loads(Path(cache_file).read_text(encoding="utf-8"))
    return data["games"], datetime.fromisoformat(data["fetched_at"])


def _write_cache(cache_file, games, fetched_at):
    tmp = Path(cache_file).with_suffix(".tmp")
    tmp.write_text(json.dumps({"fetched_at": fetched_at.isoformat(), "games": games}))
    os.replace(tmp, cache_file)


def load_schedule(fetch=fetch_schedule_payload, cache_file=CACHE_FILE):
    """Live schedule if possible; otherwise the last saved copy; otherwise empty."""
    try:
        games = parse_schedule(fetch())
        now = datetime.now(timezone.utc)
        try:
            _write_cache(cache_file, games, now)
        except OSError:
            pass
        return Schedule(games, now)
    except Exception as exc:  # timeout, HTTP error, bad JSON...
        error = f"{type(exc).__name__}: {exc}"
        try:
            games, fetched_at = _read_cache(cache_file)
            return Schedule(games, fetched_at, stale=True, error=error)
        except Exception:
            return Schedule([], None, stale=True, error=error)


def upcoming_games(games, team=None, now=None, *, days=SCHEDULE_WINDOW_DAYS):
    """Return scheduled games by tipoff, optionally filtered by team and time."""
    now = now or datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days) if days is not None else None
    upcoming = []
    for game in games:
        if game["status"] != 1 or (team is not None and team not in (game["home"], game["away"])):
            continue
        if game["game_id"].startswith("001"):
            continue
        tipoff = datetime.fromisoformat(game["tipoff_utc"])
        if tipoff > now and (cutoff is None or tipoff <= cutoff):
            upcoming.append((tipoff, game))
    return [game for _, game in sorted(upcoming, key=lambda item: item[0])]


def next_game(games, team_a, team_b, now=None):
    """Return the next scheduled meeting between the two teams."""
    return next(
        (game for game in upcoming_games(games, team_a, now, days=None)
         if team_b in (game["home"], game["away"])),
        None,
    )


def format_tipoff(game):
    dt = datetime.fromisoformat(game["tipoff_utc"]).astimezone(EASTERN)
    hour = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt:%a, %b %d, %Y}", f"{hour}:{dt:%M} {ampm} {dt.tzname()}"


def refresh_results(csv_path, season=SEASON):
    """Re-download completed games. Leaves the old CSV untouched on any failure."""
    from fetch_data import fetch_season, to_one_row_per_game
    games = to_one_row_per_game(fetch_season(season))
    tmp = Path(csv_path).with_suffix(".tmp")
    games.to_csv(tmp, index=False)
    os.replace(tmp, csv_path)
    return len(games)


def refresh_history():
    """Download any past seasons not cached yet (cached ones are skipped)."""
    from fetch_data import fetch_history
    return fetch_history()


def format_updated(moment):
    """'Nov 22, 3:12 PM EST' for a datetime, in Eastern Time."""
    local = moment.astimezone(EASTERN)
    return (f"{local:%b} {local.day}, {local.hour % 12 or 12}:{local:%M} "
            f"{'AM' if local.hour < 12 else 'PM'} {local.tzname()}")


def resolve_home_away(game, team_a, team_b, venue="a_home"):
    """Who is home, whatever order the dropdowns are in.

    A scheduled game decides it. Without one, `venue` is "a_home", "b_home" or
    "neutral" (neutral keeps team_a first but applies no home bonus).
    Returns (home, away, neutral).
    """
    if game:
        return game["home"], game["away"], game.get("neutral", False)
    if venue == "b_home":
        return team_b, team_a, False
    return team_a, team_b, venue == "neutral"
