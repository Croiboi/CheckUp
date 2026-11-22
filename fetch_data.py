import argparse
import time
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder

CURRENT_SEASON = "2026-27"
# Completed seasons used to build multi-season ratings. 2020-21 is skipped on
# purpose: many games had no or limited crowds, which distorts home-court advantage.
HISTORY_SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
HISTORY_DIR = Path(__file__).with_name("data")


def fetch_season(season: str) -> pd.DataFrame:
    """Fetch regular-season NBA results, with one row per team per game."""
    finder = leaguegamefinder.LeagueGameFinder(
        league_id_nullable="00",
        season_nullable=season,
        season_type_nullable="Regular Season",
        timeout=60,
    )
    return finder.get_data_frames()[0]


def to_one_row_per_game(df: pd.DataFrame) -> pd.DataFrame:
    """Keep games with one complete home row and one complete away row."""
    columns = ["GAME_ID", "GAME_DATE", "MATCHUP", "TEAM_ABBREVIATION", "PTS"]
    rows = df[columns].dropna().drop_duplicates()

    home = rows[rows["MATCHUP"].str.contains(" vs. ", regex=False)]
    away = rows[rows["MATCHUP"].str.contains(" @ ", regex=False)]

    home_counts = home.groupby("GAME_ID").size()
    away_counts = away.groupby("GAME_ID").size()
    valid_ids = home_counts[home_counts.eq(1)].index.intersection(
        away_counts[away_counts.eq(1)].index
    )

    skipped_ids = pd.Index(df["GAME_ID"].dropna().unique()).difference(valid_ids)
    if len(skipped_ids):
        print(f"Skipped {len(skipped_ids)} games without a unique home-away pair.")
        print("Example skipped IDs:", ", ".join(map(str, skipped_ids[:5])))

    games = home[home["GAME_ID"].isin(valid_ids)].merge(
        away[away["GAME_ID"].isin(valid_ids)],
        on="GAME_ID",
        suffixes=("_home", "_away"),
        validate="one_to_one",
    )

    if games.empty:
        raise ValueError("The API returned no games with a valid home-away pair.")

    output = pd.DataFrame({
        "game_id": games["GAME_ID"],
        "date": pd.to_datetime(games["GAME_DATE_home"]),
        "home_team": games["TEAM_ABBREVIATION_home"],
        "away_team": games["TEAM_ABBREVIATION_away"],
        "home_pts": games["PTS_home"],
        "away_pts": games["PTS_away"],
    })
    return output.sort_values(["date", "game_id"]).reset_index(drop=True)


def history_path(season: str) -> Path:
    return HISTORY_DIR / f"nba_{season.replace('-', '_')}.csv"


def fetch_history(seasons=None, force=False, pause=2.0):
    """Download completed seasons into data/, skipping any already cached.

    Returns {season: "cached" | "downloaded" | "failed: <reason>"}. One failed season
    never stops the others, and existing cache files are never overwritten on failure.
    """
    HISTORY_DIR.mkdir(exist_ok=True)
    status = {}
    for season in seasons or HISTORY_SEASONS:
        path = history_path(season)
        if path.exists() and not force:
            status[season] = "cached"
            continue
        try:
            games = to_one_row_per_game(fetch_season(season))
            tmp = path.with_suffix(".tmp")
            games.to_csv(tmp, index=False)
            tmp.replace(path)
            status[season] = "downloaded"
        except Exception as exc:  # timeout, throttling, bad response...
            status[season] = f"failed: {type(exc).__name__}"
        time.sleep(pause)  # be polite to NBA.com
    return status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download NBA results.")
    parser.add_argument("--history", action="store_true",
                        help="download past seasons into data/ (skips cached ones)")
    parser.add_argument("--force", action="store_true",
                        help="with --history, re-download seasons already cached")
    args = parser.parse_args()

    if args.history:
        for season, result in fetch_history(force=args.force).items():
            print(f"{season}: {result}")
    else:
        season = CURRENT_SEASON
        raw = fetch_season(season)
        games = to_one_row_per_game(raw)

        filename = f"nba_{season.replace('-', '_')}.csv"
        games.to_csv(filename, index=False)

        print(f"Saved {len(games):,} games to {filename}")
        print(games.head().to_string(index=False))
        print("Ties:", (games["home_pts"] == games["away_pts"]).sum())
        print(f"Home win rate: {(games['home_pts'] > games['away_pts']).mean():.1%}")
