"""CheckUp: a dark, desktop-style NBA matchup dashboard. Run: streamlit run app.py"""

from datetime import datetime, timedelta, timezone

import streamlit as st

import data_service
import elo
import player_watch
import team_profile
import ui
from teams import NAME_TO_ABBR, TEAMS

NOW = datetime.now(timezone.utc)

CSV_PATH = elo.DEFAULT_CSV
NAMES = sorted(NAME_TO_ABBR)

st.set_page_config(page_title="CheckUp · NBA Matchup Desk", page_icon=ui.page_icon(), layout="wide",
                   initial_sidebar_state="collapsed")


def html(markup):
    st.markdown(markup, unsafe_allow_html=True)


def fingerprint():
    files = elo.history_files() + ([CSV_PATH] if CSV_PATH.exists() else [])
    return tuple((str(p), p.stat().st_mtime) for p in files)


@st.cache_data(show_spinner="Evaluating the model on past seasons…")
def build_report(data_key):
    games = elo.load_history(CSV_PATH)
    return elo.select_model(games)


@st.cache_data(ttl=1800, show_spinner="Loading NBA schedule…")
def cached_schedule():
    return data_service.load_schedule()


@st.cache_data(ttl=900, show_spinner="Loading recent NBA player stats…")
def cached_player_leaders(csv_version):
    try:
        games = elo.load_games(CSV_PATH)
        recent = player_watch.recent_team_games(games)
        start = min(game["date"] for team_games in recent.values() for game in team_games)
        logs = player_watch.fetch_logs(data_service.SEASON, start, games[-1]["date"])
        return player_watch.find_leaders(recent, logs), None
    except Exception as exc:
        return {}, type(exc).__name__


@st.cache_data(ttl=900, show_spinner="Loading team roster…")
def cached_team_roster(team, season):
    try:
        return team_profile.fetch_roster(team, season), False
    except Exception:
        return [], True


@st.cache_data(ttl=900, show_spinner="Loading player averages…")
def cached_player_averages(team, season):
    try:
        return team_profile.fetch_player_averages(team, season), False
    except Exception:
        return {}, True


PAGES = ("Home", "Matchups", "Team Profiles", "Model Performance", "Data & Updates")
TEAM_ROUTE_KEYS = ("schedule_team", "team_a", "team_b", "profile_team")


def sync_route():
    """Restore the view when the URL changes, including browser history events."""
    query = st.query_params.to_dict()
    route = tuple(sorted(query.items()))
    if st.session_state.get("active_route") == route:
        return
    st.session_state.active_route = route
    page = query.get("page")
    st.session_state.page = page if page in PAGES else "Home"
    for key in TEAM_ROUTE_KEYS:
        if query.get(key) in TEAMS:
            st.session_state[key] = TEAMS[query[key]][0]
        else:
            st.session_state.pop(key, None)
    st.session_state.compare_first = query.get("compare") == "1"
    st.session_state.selected_matchup = query.get("game")


def write_route():
    state = st.session_state
    query = {"page": state.page}
    for key in TEAM_ROUTE_KEYS:
        if state.get(key) in NAME_TO_ABBR:
            query[key] = NAME_TO_ABBR[state[key]]
    if state.get("compare_first"):
        query["compare"] = "1"
    if state.get("selected_matchup"):
        query["game"] = state.selected_matchup
    st.query_params.from_dict(query)
    state.active_route = tuple(sorted(query.items()))


def navigate(**destination):
    state = st.session_state
    if any(state.get(key) != value for key, value in destination.items()):
        state.update(destination)
        write_route()


def team_profile_button(team, key):
    st.button(
        TEAMS[team][0], key=key, help="View team stats and roster",
        on_click=navigate,
        kwargs={"page": "Team Profiles", "profile_team": TEAMS[team][0]},
    )


def swap_teams():
    st.session_state.team_a, st.session_state.team_b = (
        st.session_state.team_b, st.session_state.team_a)
    write_route()


def open_team_schedule():
    team = st.session_state.home_team_picker
    if team:
        navigate(page="Matchups", schedule_team=team, compare_first=False)
        st.session_state.home_team_picker = None


def open_scheduled_matchup(game):
    navigate(
        page="Matchups", team_a=TEAMS[game["away"]][0], team_b=TEAMS[game["home"]][0],
        compare_first=True, selected_matchup=game["game_id"],
    )


def game_day(game):
    return datetime.fromisoformat(game["tipoff_utc"]).astimezone(data_service.EASTERN).date()


def selected_game(team_a, team_b):
    selected_id = st.session_state.get("selected_matchup")
    if selected_id:
        for game in data_service.upcoming_games(schedule.games, team_a, NOW, days=None):
            if game["game_id"] == selected_id and team_b in (game["home"], game["away"]):
                return game
    return data_service.next_game(schedule.games, team_a, team_b, NOW)


def team_prediction(team, home, away, neutral, use_form):
    result = elo.predict_matchup(ratings, form, home, away, neutral, use_form, settings)
    return result, result["home_prob"] if team == home else result["away_prob"]


def render_matchup(abbr_a, abbr_b, home, away, neutral, use_form, *, context):
    name_a, name_b = TEAMS[abbr_a][0], TEAMS[abbr_b][0]
    result, p_a = team_prediction(abbr_a, home, away, neutral, use_form)
    pct_a, pct_b = ui.split_percentages(p_a)

    def side(abbr, name, pct, color):
        tag = "NEUTRAL" if neutral else ("HOME" if abbr == home else "AWAY")
        return {"abbr": abbr, "name": name, "pct": pct, "color": color, "tag": tag,
                "rating": ratings.get(abbr, elo.START_RATING),
                "form": elo.recent_form(form, abbr)}

    color_a, color_b = ui.distinct_colors(TEAMS[abbr_a][1], TEAMS[abbr_b][1])
    html(ui.hero_html(side(abbr_a, name_a, pct_a, color_a),
                      side(abbr_b, name_b, pct_b, color_b)))

    team_a_link, team_b_link = st.columns(2)
    with team_a_link:
        team_profile_button(abbr_a, f"profile_{context}_a")
    with team_b_link:
        team_profile_button(abbr_b, f"profile_{context}_b")

    if use_form:
        shift = (result["p_with_form"] - result["p_with_home"]) * 100
        shift = shift if abbr_a == home else -shift
        html(f'<p class="note dash">Recent form moves <b>{name_a}</b> by <b>{shift:+.1f}</b> '
             "points versus Elo plus home court.</p>")

    with st.expander("Breakdown: Elo, home court, recent form"):
        def for_a(p_home_side):
            return p_home_side if abbr_a == home else 1 - p_home_side
        home_label = ("Neutral court: no home bonus" if neutral
                      else f"+ Home court (+{result['home_bonus']} Elo to {TEAMS[home][0]})")
        html(ui.breakdown_html(
            name_a, name_b,
            ratings.get(abbr_a, elo.START_RATING), ratings.get(abbr_b, elo.START_RATING),
            [("Elo ratings only", for_a(result["p_elo"]), True),
             (home_label, for_a(result["p_with_home"]), True),
             (f"+ Recent form (weight {settings['form_weight']:g})",
              for_a(result["p_with_form"]), use_form)],
            use_form))
    html(ui.players_to_watch_html([
        (abbr_a, name_a, player_leaders.get(abbr_a)),
        (abbr_b, name_b, player_leaders.get(abbr_b)),
    ], stats_error))

    return p_a


def render_team_overview(team, through, *, compact=False):
    name = TEAMS[team][0]
    html(f'<div class="team-heading dash">{ui.logo_html(team)}'
         f'<div role="heading" aria-level="2"><strong>{name}</strong></div></div>')
    st.caption(f"{data_service.SEASON} regular season · Results through {through}")
    stats = team_profile.season_stats(elo.load_games(CSV_PATH), team) if CSV_PATH.is_file() else None
    if stats:
        if compact:
            record, percentage = st.columns(2)
            streak, recent = st.columns(2)
        else:
            record, percentage, streak, recent = st.columns(4)
        record.metric("Wins–losses", stats["record"])
        percentage.metric("Win percentage", f"{stats['win_pct']:.1%}")
        streak.metric("Current streak", stats["streak"])
        recent.metric(f"Last {stats['recent_count']} games", stats["recent_record"])
        scored, allowed = st.columns(2)
        scored.metric("Points per game", f"{stats['points_for']:.1f}")
        allowed.metric("Opponent points per game", f"{stats['points_against']:.1f}")

        with st.expander("Recent results"):
            st.table([
                {"Date": game["date"], "Opponent": TEAMS.get(game["opponent"], (game["opponent"],))[0],
                 "Venue": game["venue"], "Result": game["result"],
                 "Score": f"{game['scored']}–{game['allowed']}"}
                for game in stats["results"]
            ])
    else:
        st.info("No completed regular-season games are available for this team.")

    st.subheader("Top scorers" if compact else "Roster", anchor=False)
    roster, unavailable = cached_team_roster(team, data_service.SEASON)
    if roster:
        averages, averages_unavailable = cached_player_averages(team, data_service.SEASON)
        st.caption("Ranked by season points per game with this team." if compact
                   else "Regular-season averages per game with this team. GP is games played.")
        if averages_unavailable:
            st.warning("Player averages are temporarily unavailable.")
        elif compact and not any(player["PLAYER_ID"] in averages for player in roster):
            st.info("No scoring averages are available for the current roster yet.")
        html(ui.roster_cards_html(
            roster, averages, TEAMS[team][1], averages_unavailable, limit=3 if compact else None,
        ))
    elif unavailable:
        st.warning("NBA Stats couldn’t load this roster. Try again later.")
    else:
        st.info("NBA Stats has no roster available for this team.")

    if compact:
        st.button(
            "View full roster →", key="view_full_roster",
            on_click=navigate,
            kwargs={"page": "Team Profiles", "profile_team": name},
        )


# ---------------------------------------------------------------- load data
try:
    report = build_report(fingerprint())
except (ValueError, OSError) as exc:
    st.error(f"Not enough results to build the model ({exc}). "
             "Run `python fetch_data.py` first.")
    st.stop()
schedule = cached_schedule()
settings, ratings, form = report["selected"], report["ratings"], report["form"]

sync_route()
st.session_state.setdefault("team_a", "New York Knicks")
st.session_state.setdefault("team_b", "Boston Celtics")
st.session_state.setdefault("use_form", False)
st.session_state.setdefault("schedule_team", "New York Knicks")
if st.session_state.team_a == st.session_state.team_b:
    st.session_state.team_b = next(n for n in NAMES if n != st.session_state.team_a)

color_a, color_b = ui.distinct_colors(TEAMS[NAME_TO_ABBR[st.session_state.team_a]][1],
                                      TEAMS[NAME_TO_ABBR[st.session_state.team_b]][1])
html(f"<style>{ui.CSS}{ui.brand_icon_css()}{ui.wallpaper_css(color_a, color_b)}</style>")

# ----------------------------------------------------------------- top bar
through = datetime.strptime(report["latest_date"], "%Y-%m-%d").strftime("%b %d, %Y")
if schedule.fetched_at:
    sched_label = f"Schedule · {data_service.format_updated(schedule.fetched_at)}"
    sched_state = "stale" if schedule.stale else "ok"
else:
    sched_label, sched_state = "Schedule unavailable", "none"

for widget_key in ("team_a", "team_b", "schedule_team", "use_form", "profile_team"):
    if widget_key in st.session_state:
        # Keep the selection when its widget is on a different page.
        st.session_state[widget_key] = st.session_state[widget_key]

page = st.session_state.page
with st.container(key="tipoff_header"):
    brand, status, menu = st.columns([2, 7, 1], vertical_alignment="center")
    brand.button(
        "CheckUp", key="check_up_home", help="Go to Home",
        on_click=navigate, kwargs={"page": "Home"},
    )
    with status:
        html(ui.top_bar_html(through, sched_label, sched_state))
    with menu:
        with st.popover("☰ Menu"):
            for destination in PAGES:
                st.button(
                    destination,
                    key=f"go_{destination}",
                    disabled=destination == page,
                    on_click=navigate,
                    kwargs={"page": destination},
                )

if page == "Home":
    html(ui.home_hero_html())
    with st.container(key="home_actions"):
        browse, performance = st.columns(2)
        browse.button("Explore matchups →", type="primary", key="home_matchups",
                      on_click=navigate,
                      kwargs={"page": "Matchups", "compare_first": False})
        performance.button("View model performance", key="home_performance",
                           on_click=navigate,
                           kwargs={"page": "Model Performance"})

    with st.container(key="home_team_search"):
        st.selectbox(
            "Find your team", NAMES, index=None, placeholder="Search team name or abbreviation",
            format_func=lambda name: f"{name} · {NAME_TO_ABBR[name]}",
            key="home_team_picker", on_change=open_team_schedule,
        )

    upcoming = [
        game for game in data_service.upcoming_games(schedule.games, now=NOW, days=None)
        if game["home"] in TEAMS and game["away"] in TEAMS
    ]
    if upcoming:
        slate_day = game_day(upcoming[0])
        slate = [game for game in upcoming if game_day(game) == slate_day]
        today = NOW.astimezone(data_service.EASTERN).date()
        title = "Today’s Games" if slate_day == today else "Next Game Day"
        html(ui.home_slate_heading_html(title, slate_day.strftime("%a, %b %d"), len(slate)))

        scored = []
        for game in slate:
            home, away, neutral = data_service.resolve_home_away(game, game["home"], game["away"])
            _, probability = team_prediction(home, home, away, neutral, st.session_state.use_form)
            home_pct, away_pct = ui.split_percentages(probability)
            scored.append((game, probability, (away, TEAMS[away][0], away_pct),
                           (home, TEAMS[home][0], home_pct), neutral))
        featured = min(scored, key=lambda item: abs(item[1] - 0.5))
        game, _, away_card, home_card, neutral = featured
        day, time = data_service.format_tipoff(game)
        html(ui.home_game_html("Featured Matchup", day, time, away_card, home_card, neutral))
        st.button("View matchup →", key="featured_matchup",
                  on_click=open_scheduled_matchup, args=(game,))

        remaining = [item for item in scored if item is not featured]
        for start in range(0, len(remaining), 3):
            columns = st.columns(3)
            for column, (game, _, away_card, home_card, neutral) in zip(
                columns, remaining[start:start + 3]
            ):
                with column:
                    _, time = data_service.format_tipoff(game)
                    html(ui.home_slate_card_html(time, away_card, home_card, neutral))
                    st.button(
                        "View matchup", key=f"slate_{game['game_id']}",
                        on_click=open_scheduled_matchup, args=(game,),
                    )
    else:
        html(ui.home_game_empty_html(
            "No upcoming games are listed."
            if schedule.games else "Schedule data is unavailable."
        ))


elif page == "Matchups":
    with st.container(key="win_matchup"):
        html(ui.window_title("Matchup"))
        use_form = st.toggle(
            "Include last-5 form", key="use_form",
            help="Applies to schedule projections and matchup details.")
        player_leaders, stats_error = (
            cached_player_leaders(CSV_PATH.stat().st_mtime_ns)
            if CSV_PATH.exists() else ({}, None)
        )
        if st.session_state.get("compare_first", False):
            compare_tab, schedule_tab = st.tabs(["Compare Teams", "Team Schedule"])
        else:
            schedule_tab, compare_tab = st.tabs(["Team Schedule", "Compare Teams"])

        with schedule_tab:
            team_name = st.selectbox(
                "Find a team", NAMES,
                format_func=lambda name: f"{name} · {NAME_TO_ABBR[name]}",
                key="schedule_team", on_change=write_route,
            )
            team = NAME_TO_ABBR[team_name]
            predictions, overview = st.columns([1.65, 1], gap="large")
            with predictions:
                st.caption(f"Next {data_service.SCHEDULE_WINDOW_DAYS} days · "
                           f"Based on current ratings through {through} · All times Eastern")
                upcoming = data_service.upcoming_games(schedule.games, team, NOW)
                if not upcoming:
                    st.info("No scheduled games in the next 14 days."
                            if schedule.games else "The NBA schedule is unavailable right now.")

                for scheduled in upcoming:
                    home, away, neutral = data_service.resolve_home_away(scheduled, team, team)
                    opponent = away if team == home else home
                    if opponent not in TEAMS:
                        continue
                    venue = "Neutral" if neutral else "Home" if team == home else "Away"
                    day, time = data_service.format_tipoff(scheduled)
                    _, probability = team_prediction(team, home, away, neutral, use_form)
                    displayed, _ = ui.split_percentages(probability)
                    html(ui.schedule_row_html(team, opponent, TEAMS[opponent][0],
                                              venue, f"{day} · {time}", displayed / 100))
                    with st.expander(f"Game details · {team} vs {opponent} · {day}"):
                        render_matchup(
                            team, opponent, home, away, neutral, use_form, context=scheduled["game_id"]
                        )
            with overview:
                with st.container(key="schedule_team_overview"):
                    render_team_overview(team, through, compact=True)

        with compare_tab:
            col1, col2 = st.columns(2)
            name_a = col1.selectbox(
                "Team 1", [n for n in NAMES if n != st.session_state.team_b],
                format_func=lambda name: f"{name} · {NAME_TO_ABBR[name]}", key="team_a", on_change=write_route)
            b_options = [n for n in NAMES if n != name_a]
            if st.session_state.team_b not in b_options:
                st.session_state.team_b = b_options[0]
            name_b = col2.selectbox(
                "Team 2", b_options,
                format_func=lambda name: f"{name} · {NAME_TO_ABBR[name]}", key="team_b", on_change=write_route)
            abbr_a, abbr_b = NAME_TO_ABBR[name_a], NAME_TO_ABBR[name_b]

            st.button("⇄ Swap teams", on_click=swap_teams)

            game = selected_game(abbr_a, abbr_b)
            venue = "a_home"
            if game:
                date_str, time_str = data_service.format_tipoff(game)
                html(ui.schedule_strip_html(
                    {"date": date_str, "time": time_str,
                     "home_name": "Neutral court" if game.get("neutral") else TEAMS[game["home"]][0]}))
                if datetime.fromisoformat(game["tipoff_utc"]) > NOW + timedelta(
                    days=data_service.SCHEDULE_WINDOW_DAYS
                ):
                    st.caption(f"Early projection · Based on current ratings through {through}.")
            else:
                reason = ("No upcoming game between these teams on the schedule."
                          if schedule.games else "The NBA schedule is unavailable right now.")
                html(ui.schedule_strip_html(reason=reason))
                choices = {f"{name_a} at home": "a_home", f"{name_b} at home": "b_home",
                           "Neutral court": "neutral"}
                venue = choices[st.radio("Venue", list(choices), horizontal=True,
                                         label_visibility="collapsed")]
            home, away, neutral = data_service.resolve_home_away(game, abbr_a, abbr_b, venue)

            p_a = render_matchup(abbr_a, abbr_b, home, away, neutral, use_form, context="compare")
            st.session_state.comparison_venue = venue

elif page == "Team Profiles":
    with st.container(key="win_matchup"):
        html(ui.window_title("Team Profiles"))
        st.session_state.setdefault("profile_team", st.session_state.schedule_team)
        name = st.selectbox(
            "Find a team", NAMES,
            format_func=lambda name: f"{name} · {NAME_TO_ABBR[name]}",
            key="profile_team", on_change=write_route,
        )
        team = NAME_TO_ABBR[name]
        render_team_overview(team, through)

elif page == "Model Performance":
    with st.container(key="win_perf"):
        html(ui.window_title("Model Performance",
                             f"{report['game_count']:,} games · {len(report['seasons'])} season(s)"))
        html(ui.performance_html(report))
        with st.expander("How the settings were chosen"):
            html(ui.search_html(report))
        with st.expander("Compare with an outside estimate"):
            name_a = st.session_state.team_a
            abbr_a, abbr_b = NAME_TO_ABBR[name_a], NAME_TO_ABBR[st.session_state.team_b]
            game = selected_game(abbr_a, abbr_b)
            home, away, neutral = data_service.resolve_home_away(
                game, abbr_a, abbr_b, st.session_state.get("comparison_venue", "a_home"))
            _, p_a = team_prediction(
                abbr_a, home, away, neutral, st.session_state.get("use_form", False))
            st.caption(f"{name_a} vs {TEAMS[abbr_b][0]} · "
                       + ("Neutral court" if neutral else f"Home: {TEAMS[home][0]}"))
            outside = st.number_input(f"Outside win probability for {name_a} (%)",
                                      min_value=1.0, max_value=99.0, value=None, step=0.5,
                                      placeholder="e.g. 59")
            if outside is not None:
                html(ui.outside_html(name_a, p_a, outside / 100))

else:
    with st.container(key="win_data"):
        html(ui.window_title("Data & Updates"))
        html(f'<p class="small dash">Results through <b>{through}</b> · '
             f'{len(elo.history_files())} past season file(s) cached.</p>')
        if schedule.stale and schedule.fetched_at:
            st.warning("The NBA schedule request failed, so this is the last saved copy "
                       f"({schedule.error}).")
        elif schedule.stale:
            st.warning(f"No schedule available ({schedule.error}). You can still simulate a matchup.")

        for kind, text in st.session_state.pop("refresh_msgs", []):
            getattr(st, kind)(text)

        if st.button("Refresh data"):
            msgs = []
            with st.spinner("Contacting NBA.com…"):
                try:
                    n = data_service.refresh_results(CSV_PATH)
                    msgs.append(("success", f"Current-season results updated ({n:,} games)."))
                except Exception as exc:
                    msgs.append(("warning", f"Couldn't update current-season results "
                                            f"({type(exc).__name__}); using the last saved CSV."))
                try:
                    status = data_service.refresh_history()
                    got = [s for s, r in status.items() if r == "downloaded"]
                    bad = [s for s, r in status.items() if r.startswith("failed")]
                    if got:
                        msgs.append(("success", "Downloaded past seasons: " + ", ".join(got)))
                    if bad:
                        msgs.append(("warning", "Couldn't download: " + ", ".join(bad)
                                     + ". Cached seasons are still in use."))
                except Exception as exc:
                    msgs.append(("warning", f"Past-season download skipped ({type(exc).__name__})."))
            st.cache_data.clear()
            st.session_state["refresh_msgs"] = msgs
            st.rerun()
