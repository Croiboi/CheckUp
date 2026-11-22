"""Season results and NBA roster data for team profiles."""

from itertools import takewhile
from statistics import mean


def season_stats(games, team):
    """Summarize completed regular-season games in chronological order."""
    results = []
    for game in games:
        is_home = game["home_team"] == team
        if not is_home and game["away_team"] != team:
            continue
        home, away = float(game["home_pts"]), float(game["away_pts"])
        scored, allowed = (home, away) if is_home else (away, home)
        if scored == allowed:
            continue
        results.append({
            "date": game["date"],
            "opponent": game["away_team"] if is_home else game["home_team"],
            "venue": "Home" if is_home else "Away",
            "result": "W" if scored > allowed else "L",
            "scored": int(scored),
            "allowed": int(allowed),
        })
    if not results:
        return None
    wins = sum(game["result"] == "W" for game in results)
    latest = results[-1]["result"]
    streak = sum(1 for _ in takewhile(lambda game: game["result"] == latest, reversed(results)))
    recent = results[-10:]
    recent_wins = sum(game["result"] == "W" for game in recent)
    return {
        "record": f"{wins}–{len(results) - wins}",
        "win_pct": wins / len(results),
        "streak": f"{latest}{streak}",
        "recent_record": f"{recent_wins}–{len(recent) - recent_wins}",
        "recent_count": len(recent),
        "points_for": mean(game["scored"] for game in results),
        "points_against": mean(game["allowed"] for game in results),
        "results": recent[::-1],
    }


def fetch_roster(team, season):
    """Return the roster listed by NBA Stats for the selected season."""
    from nba_api.stats.endpoints.commonteamroster import CommonTeamRoster
    from nba_api.stats.static import teams

    team_info = teams.find_team_by_abbreviation(team)
    if not team_info:
        return []
    roster = CommonTeamRoster(team_id=team_info["id"], season=season, timeout=12)
    return (roster.get_data_frames()[0][["PLAYER_ID", "NUM", "PLAYER", "POSITION"]]
            .fillna("—")
            .rename(columns={"NUM": "Jersey", "PLAYER": "Player", "POSITION": "Position"})
            .to_dict("records"))


def fetch_player_averages(team, season):
    """Return regular-season per-game averages with the selected team only."""
    from nba_api.stats.endpoints.leaguedashplayerstats import LeagueDashPlayerStats
    from nba_api.stats.static import teams

    team_id = teams.find_team_by_abbreviation(team)["id"]
    response = LeagueDashPlayerStats(
        team_id_nullable=team_id, season=season, per_mode_detailed="PerGame", timeout=12,
    )
    rows = response.get_data_frames()[0]
    team_rows = rows.loc[rows["TEAM_ID"].eq(team_id)]
    return team_rows.set_index("PLAYER_ID")[["GP", "MIN", "PTS", "REB", "AST"]].to_dict("index")
