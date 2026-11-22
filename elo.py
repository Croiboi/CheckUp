"""NBA Elo with a home-court bonus, season carryover and optional last-five form.

Settings (home bonus, between-season carryover, form weight) are chosen by a
chronological backtest:

    older games  -> warm-up: build ratings only, nothing is scored
    middle games -> validation: score every candidate setting, pick the best
    newest games -> test: report results for the chosen settings

Every prediction is made before that game's result touches the ratings, and the
test period never influences which settings are chosen.
"""

import argparse
import csv
from collections import defaultdict, deque
from math import sqrt
from pathlib import Path
from statistics import mean, stdev

START_RATING = 1500
K = 20
DEFAULT_CSV = Path(__file__).with_name("nba_2026_27.csv")
HISTORY_DIR = Path(__file__).with_name("data")

# Fallback settings (used before a backtest has run, and by old callers).
DEFAULT_SETTINGS = {"home_bonus": 30, "carryover": 1.0, "form_weight": 2.0}

BONUS_GRID = (0, 10, 20, 30, 40, 50, 60)
# Fraction of last season's distance from 1500 kept at the start of a new season
# (1.0 = keep everything, 0.5 = move halfway back to 1500).
CARRYOVER_GRID = (1.0, 0.9, 0.75, 0.6, 0.5)
# Elo points added per point of difference in last-five average margin.
FORM_WEIGHT_GRID = (0.5, 1, 2, 3, 4, 6, 8)
WARMUP_FRACTION = 0.40
VALIDATION_FRACTION = 0.30      # the remaining 30% is the test period


# --------------------------------------------------------------------- basics
def win_probability(rating_gap):
    return 1 / (1 + 10 ** (-rating_gap / 400))


def season_of(date):
    """Season label from an ISO date: Oct 2026 - Sep 2027 -> 2026."""
    year, month = int(date[:4]), int(date[5:7])
    return year if month >= 10 else year - 1


def load_games(path):
    """Read one results CSV, oldest first."""
    with Path(path).open(newline="", encoding="utf-8-sig") as file:
        return sorted(csv.DictReader(file), key=lambda g: (g["date"], g["game_id"]))


def history_files(history_dir=HISTORY_DIR):
    return sorted(Path(history_dir).glob("nba_*.csv")) if Path(history_dir).exists() else []


def load_history(current_csv=DEFAULT_CSV, history_dir=HISTORY_DIR):
    """Cached past seasons plus the current-season CSV, de-duplicated, oldest first."""
    paths = history_files(history_dir)
    if Path(current_csv).exists():
        paths.append(Path(current_csv))
    by_id = {}
    for path in paths:
        for game in load_games(path):
            by_id[game["game_id"]] = game
    return sorted(by_id.values(), key=lambda g: (g["date"], g["game_id"]))


def recent_form(form, team):
    """Average point margin over the team's last five games (0 if none)."""
    margins = form.get(team)
    return mean(margins) if margins else 0


def brier(predictions, outcomes):
    """Mean squared gap between predicted probability and the 0/1 result."""
    return mean((p - y) ** 2 for p, y in zip(predictions, outcomes))


# ----------------------------------------------------------- one chronological pass
def simulate(games, home_bonus=0, carryover=1.0, k=K):
    """Walk through games in date order.

    For each game this records what was known BEFORE tipoff (rating gap including
    the home bonus, and the difference in last-five average margin) and only then
    uses the result to update ratings. At the first game of a new season every
    rating moves back toward 1500 by (1 - carryover) and last-five histories reset.
    """
    ratings = defaultdict(lambda: START_RATING)
    margins = defaultdict(lambda: deque(maxlen=5))
    gaps, form_diffs, outcomes = [], [], []
    season = None

    for game in games:
        this_season = season_of(game["date"])
        if season is not None and this_season != season:
            for team in list(ratings):
                ratings[team] = START_RATING + carryover * (ratings[team] - START_RATING)
            margins.clear()
        season = this_season

        home, away = game["home_team"], game["away_team"]
        gap = ratings[home] - ratings[away] + home_bonus
        form_diff = recent_form(margins, home) - recent_form(margins, away)

        margin = int(game["home_pts"]) - int(game["away_pts"])
        home_won = int(margin > 0)
        gaps.append(gap)
        form_diffs.append(form_diff)
        outcomes.append(home_won)

        change = k * (home_won - win_probability(gap))   # update AFTER predicting
        ratings[home] += change
        ratings[away] -= change
        margins[home].append(margin)
        margins[away].append(-margin)

    return {"gaps": gaps, "form_diffs": form_diffs, "outcomes": outcomes,
            "ratings": ratings, "form": margins}


def split_indices(n):
    """(validation_start, test_start). Everything before validation_start is warm-up."""
    return int(n * WARMUP_FRACTION), int(n * (WARMUP_FRACTION + VALIDATION_FRACTION))


def _predictions(run, lo, hi, form_weight=0.0):
    return [win_probability(run["gaps"][i] + form_weight * run["form_diffs"][i])
            for i in range(lo, hi)]


def _paired_difference(model_preds, base_preds, outcomes):
    """Mean(model error - baseline error) and its standard error. Negative = better."""
    diffs = [(p - y) ** 2 - (q - y) ** 2 for p, q, y in zip(model_preds, base_preds, outcomes)]
    se = stdev(diffs) / sqrt(len(diffs)) if len(diffs) > 1 else None
    return mean(diffs), se


def _span(games, lo, hi):
    return {"games": hi - lo,
            "start": games[lo]["date"] if hi > lo else None,
            "end": games[hi - 1]["date"] if hi > lo else None}


# ---------------------------------------------------------------- model selection
def select_model(games):
    """Choose settings on the validation period; report on the untouched test period."""
    n = len(games)
    if n < 20:
        raise ValueError("Need at least 20 completed games to evaluate the model.")
    val_lo, test_lo = split_indices(n)
    runs = {}
    for carry in CARRYOVER_GRID:
        for bonus in BONUS_GRID:
            runs[(bonus, carry)] = simulate(games, bonus, carry)
    outcomes = runs[(0, 1.0)]["outcomes"]
    val_y, test_y = outcomes[val_lo:test_lo], outcomes[test_lo:]

    def val_score(key, form_weight=0.0):
        return brier(_predictions(runs[key], val_lo, test_lo, form_weight), val_y)

    # Each model is tuned on validation data only, so the comparison is fair.
    plain_carry = min(CARRYOVER_GRID, key=lambda c: val_score((0, c)))
    home_bonus, carryover = min(runs, key=lambda key: val_score(key))
    home_run = runs[(home_bonus, carryover)]
    form_weight = min(FORM_WEIGHT_GRID, key=lambda w: val_score((home_bonus, carryover), w))

    plain_run = runs[(0, plain_carry)]
    specs = [
        ("elo", "Plain Elo", plain_run, 0.0,
         {"home_bonus": 0, "carryover": plain_carry, "form_weight": 0.0}),
        ("home", "Elo + home court", home_run, 0.0,
         {"home_bonus": home_bonus, "carryover": carryover, "form_weight": 0.0}),
        ("form", "Elo + home court + last 5", home_run, form_weight,
         {"home_bonus": home_bonus, "carryover": carryover, "form_weight": form_weight}),
    ]
    base_preds = _predictions(plain_run, test_lo, n)
    models = []
    for key, label, run, weight, settings in specs:
        preds = _predictions(run, test_lo, n, weight)
        diff, se = _paired_difference(preds, base_preds, test_y)
        models.append({"key": key, "label": label, "settings": settings,
                       "brier": brier(preds, test_y), "games": len(test_y),
                       "diff_vs_elo": diff, "diff_se": se})

    selected = {"home_bonus": home_bonus, "carryover": carryover, "form_weight": form_weight}
    final = simulate(games, home_bonus, carryover)       # state used for live predictions

    return {
        "selected": selected,
        "models": models,
        "coin_flip": 0.25,
        "splits": {"warmup": _span(games, 0, val_lo),
                   "validation": _span(games, val_lo, test_lo),
                   "test": _span(games, test_lo, n)},
        "search": {
            "bonus": {b: min(val_score((b, c)) for c in CARRYOVER_GRID) for b in BONUS_GRID},
            "carryover": {c: min(val_score((b, c)) for b in BONUS_GRID) for c in CARRYOVER_GRID},
            "form_weight": {w: val_score((home_bonus, carryover), w) for w in FORM_WEIGHT_GRID},
            "no_form": val_score((home_bonus, carryover)),
        },
        "ratings": dict(final["ratings"]),
        "form": {t: list(m) for t, m in final["form"].items()},
        "latest_date": games[-1]["date"],
        "game_count": n,
        "seasons": sorted({season_of(g["date"]) for g in games}),
    }


# ------------------------------------------------------------------- predictions
def fit_current_state(games, settings=None):
    """Ratings and last-five margins after every completed game."""
    settings = settings or DEFAULT_SETTINGS
    run = simulate(games, settings["home_bonus"], settings["carryover"])
    return run["ratings"], run["form"]


def predict_matchup(ratings, form, home, away, neutral=False, use_form=False, settings=None):
    """Single source of truth for a prediction (used by the CLI and the dashboard).

    Also returns the pieces of the calculation so the dashboard can explain it.
    """
    settings = settings or DEFAULT_SETTINGS
    rating_gap = ratings.get(home, START_RATING) - ratings.get(away, START_RATING)
    bonus = 0 if neutral else settings["home_bonus"]
    form_adjustment = settings["form_weight"] * (
        recent_form(form, home) - recent_form(form, away))
    applied_form = form_adjustment if use_form else 0.0

    p_elo = win_probability(rating_gap)
    p_home = win_probability(rating_gap + bonus)
    p_final = win_probability(rating_gap + bonus + applied_form)
    return {
        "home_prob": p_final,
        "away_prob": 1 - p_final,
        "elo_gap": rating_gap + bonus,          # kept for older callers
        "rating_gap": rating_gap,
        "home_bonus": bonus,
        "form_adjustment": applied_form,
        "form_adjustment_if_on": form_adjustment,
        "p_elo": p_elo,                          # ratings only, neutral court
        "p_with_home": p_home,                   # + home court
        "p_with_form": win_probability(rating_gap + bonus + form_adjustment),
    }


# -------------------------------------------------------------------------- CLI
def format_report(report):
    lines = []
    for name in ("warmup", "validation", "test"):
        s = report["splits"][name]
        lines.append(f"  {name:<10} {s['games']:>5,} games  {s['start']} to {s['end']}")
    sel = report["selected"]
    out = ["Chronological split (oldest to newest)"] + lines
    out += [f"\nChosen on validation: home bonus {sel['home_bonus']} Elo, "
            f"carryover {sel['carryover']:.2f}, form weight {sel['form_weight']}",
            "\nTest-period Brier score (lower is better; 0.25 = coin flip)"]
    for m in report["models"]:
        se = f" (vs Elo {m['diff_vs_elo']:+.4f} +/- {m['diff_se']:.4f})" \
            if m["key"] != "elo" and m["diff_se"] is not None else ""
        out.append(f"  {m['label']:<28} {m['brier']:.4f}  n={m['games']:,}{se}")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("home", nargs="?", default="NYK", type=str.upper)
    parser.add_argument("away", nargs="?", default="BOS", type=str.upper)
    parser.add_argument("--neutral", action="store_true")
    parser.add_argument("--csv", type=Path, default=None,
                        help="use only this results CSV instead of cached history + current season")
    args = parser.parse_args()

    try:
        games = load_games(args.csv) if args.csv else load_history()
    except FileNotFoundError:
        parser.error(f"CSV not found: {args.csv}. Run fetch_data.py first.")
    if len(games) < 20:
        parser.error("Not enough completed games. Run fetch_data.py first.")
    if not args.csv and not history_files():
        print("Note: no cached past seasons found. Run `python fetch_data.py --history` "
              "for a stronger model.\n")

    report = select_model(games)
    print(format_report(report))

    ratings, form, settings = report["ratings"], report["form"], report["selected"]
    home, away = args.home, args.away
    if home == away or home not in ratings or away not in ratings:
        parser.error(f"Choose two different teams from: {', '.join(sorted(ratings))}")

    venue = f"{away} vs {home} (neutral)" if args.neutral else f"{away} at {home}"
    print(f"\n{venue} | Ratings through {report['latest_date']}")
    for label, use_form in (("Elo + home court", False), ("Elo + home court + last 5", True)):
        r = predict_matchup(ratings, form, home, away, args.neutral, use_form, settings)
        print(f"  {label}: {home} {r['home_prob']:.1%}, {away} {r['away_prob']:.1%}")


if __name__ == "__main__":
    main()
