"""Leading scorers over each team's latest completed games."""

from collections import defaultdict, deque
from datetime import date

import pandas as pd


def recent_team_games(games, limit=5):
    """Pick each team's latest games from the same results used for Elo."""
    recent = defaultdict(lambda: deque(maxlen=limit))
    for game in games:
        for team in (game["home_team"], game["away_team"]):
            recent[team].append(game)
    return recent


def fetch_logs(season, start, end):
    from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog

    return LeagueGameLog(
        league_id="00",
        season=season,
        season_type_all_star="Regular Season",
        player_or_team_abbreviation="P",
        date_from_nullable=date.fromisoformat(start).strftime("%m/%d/%Y"),
        date_to_nullable=date.fromisoformat(end).strftime("%m/%d/%Y"),
        timeout=15,
    ).get_data_frames()[0]


def find_leaders(recent, logs):
    """Rank by points in the window, counting missed games as zero."""
    stats = ["PTS", "REB", "AST"]
    columns = ["GAME_ID", "TEAM_ABBREVIATION", "PLAYER_ID", "PLAYER_NAME", *stats]
    rows = logs[columns].dropna().drop_duplicates().copy()
    rows["GAME_ID"] = rows["GAME_ID"].astype(str).str.zfill(10)
    rows = rows.loc[~rows.duplicated(
        ["TEAM_ABBREVIATION", "GAME_ID", "PLAYER_ID"], keep=False
    )]
    leaders = {}

    for team, games in recent.items():
        points_by_game = {
            game["game_id"].zfill(10): float(
                game["home_pts"] if game["home_team"] == team else game["away_pts"]
            )
            for game in games
        }
        team_rows = rows.loc[
            rows["TEAM_ABBREVIATION"].eq(team) & rows["GAME_ID"].isin(points_by_game)
        ]
        # Compare box scores with final team totals to catch partial or lagging logs.
        box_totals = team_rows.groupby("GAME_ID")["PTS"].sum()
        complete_ids = [
            game_id for game_id, points in points_by_game.items()
            if box_totals.get(game_id) == points
        ]
        if not complete_ids:
            continue
        team_rows = team_rows.loc[team_rows["GAME_ID"].isin(complete_ids)]
        totals = team_rows.groupby(["PLAYER_ID", "PLAYER_NAME"])[stats].sum().reset_index()
        leader = totals.sort_values(["PTS", "PLAYER_NAME"], ascending=[False, True]).iloc[0]
        leaders[team] = {
            "name": leader["PLAYER_NAME"],
            "player_id": int(leader["PLAYER_ID"]),
            "games": len(complete_ids),
            "window": len(games),
            "points": leader["PTS"] / len(complete_ids),
            "rebounds": leader["REB"] / len(complete_ids),
            "assists": leader["AST"] / len(complete_ids),
        }
    return leaders
