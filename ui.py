"""Presentation helpers for the dashboard: CSS and HTML strings (no Streamlit imports).

Keeping these as plain functions makes them testable. HTML is returned without blank
lines or indentation because Streamlit's markdown renderer would otherwise treat it
as a code block.
"""

import base64
import re
from functools import lru_cache
from pathlib import Path
from html import escape as esc

import elo

NEUTRAL_ACCENT = "#9CB1D0"
BRAND_WORDMARK = Path(__file__).with_name("checkup-wordmark.png")


def page_icon():
    return str(BRAND_WORDMARK) if BRAND_WORDMARK.is_file() else None


@lru_cache(maxsize=1)
def brand_icon_css():
    if not BRAND_WORDMARK.is_file():
        return ""
    data = base64.b64encode(BRAND_WORDMARK.read_bytes()).decode("ascii")
    return f"""
        .st-key-check_up_home button [data-testid="stMarkdownContainer"] {{
          position:absolute;clip-path:inset(50%);width:1px;height:1px;overflow:hidden;
        }}
        .st-key-check_up_home button::after {{
          content:"";display:block;flex:none;width:clamp(8rem,15vw,13rem);
          height:clamp(2.5rem,5.2vw,4.5rem);
          background:url("data:image/png;base64,{data}") left center/contain no-repeat;
        }}
    """


CSS = """
html, body, [data-testid="stAppViewContainer"]{color:#ECF5FF}
.stApp label, .stApp p, .stApp button, .stApp li, .dash{
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Inter","Segoe UI",system-ui,sans-serif}
header[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"],[data-testid="stDecoration"],footer{display:none !important}
[data-testid="stMainBlockContainer"],.block-container{max-width:1540px;padding:clamp(1rem,3.2vw,3rem) clamp(1rem,4vw,4rem) 5rem}

/* ---- menu bar ---- */
.menubar{display:flex;align-items:center;justify-content:space-between;gap:.6rem;flex-wrap:wrap;
  min-height:34px;padding:.3rem .9rem;margin:0 0 .9rem;border-radius:12px;
  background:rgba(13,20,39,.72);border:1px solid rgba(255,255,255,.08);
  backdrop-filter:blur(18px) saturate(150%);-webkit-backdrop-filter:blur(18px) saturate(150%);
  font-size:.82rem;color:#D2E3FA}
.menubar b{color:#fff;font-weight:700;letter-spacing:.01em}
.mb-left,.mb-right{display:flex;align-items:center;gap:.55rem;flex-wrap:wrap}
.mb-dim{color:#A3B8D4}
.pill{display:inline-flex;align-items:center;gap:.35rem;padding:.12rem .6rem;border-radius:999px;
  background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.08);font-size:.76rem;color:#D2E3FA}
.pill i{width:.45rem;height:.45rem;border-radius:50%;background:#5fd38d;display:inline-block}
.pill.warn i{background:#f5c451}.pill.bad i{background:#ef6f6c}

/* ---- windows (containers keyed in app.py) ---- */
.st-key-win_matchup,.st-key-win_perf,.st-key-win_data{
  background:rgba(17,27,48,.72);border:1px solid rgba(255,255,255,.09);border-radius:18px;
  padding:0 1.1rem 1.1rem;box-shadow:0 24px 60px rgba(0,0,0,.35),inset 0 1px 0 rgba(255,255,255,.04);
  backdrop-filter:blur(22px) saturate(150%);-webkit-backdrop-filter:blur(22px) saturate(150%)}
.wtitle{display:flex;align-items:center;gap:.7rem;margin:0 -1.1rem .9rem;padding:.6rem 1rem;
  border-bottom:1px solid rgba(255,255,255,.07)}
.dots{display:inline-flex;gap:.35rem}
.dots i{width:.7rem;height:.7rem;border-radius:50%;background:rgba(255,255,255,.16);display:block}
.dots i:nth-child(1){background:#ef6f6c}.dots i:nth-child(2){background:#f5c451}
.dots i:nth-child(3){background:#5fd38d}
.wt{font-weight:650;font-size:.9rem;color:#fff}.ws{font-size:.78rem;color:#A3B8D4}

/* ---- widgets ---- */
[data-baseweb="select"] > div{background:rgba(255,255,255,.055) !important;
  border:1px solid rgba(255,255,255,.12) !important;border-radius:12px !important;min-height:46px}
.stApp [data-testid="stWidgetLabel"] p{font-size:.78rem;letter-spacing:.06em;text-transform:uppercase;
  color:#A3B8D4}
.stButton > button{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.14);
  border-radius:10px;color:#ECF5FF;padding:.3rem .9rem}
.stButton > button:hover{border-color:#9ED8FF;color:#fff}
[data-testid="stExpander"]{border:1px solid rgba(255,255,255,.08);border-radius:12px;
  background:rgba(255,255,255,.03)}
[data-testid="stExpander"] details{border:none}

/* ---- schedule strip ---- */
.strip{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin:.3rem 0 .2rem}
.badge{display:inline-block;padding:.22rem .75rem;border-radius:999px;font-size:.7rem;
  font-weight:700;letter-spacing:.09em;text-transform:uppercase}
.badge.sched{background:rgba(95,211,141,.14);color:#6fe0a0;border:1px solid rgba(95,211,141,.3)}
.badge.hypo{background:rgba(245,196,81,.13);color:#f5c451;border:1px solid rgba(245,196,81,.3)}
.chip{padding:.2rem .65rem;border-radius:10px;background:rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.08);font-size:.86rem;color:#DEECFF}
.chip b{color:#fff}.chip.muted{color:#ABC0DC}

/* ---- hero ---- */
.hero{position:relative;display:grid;grid-template-columns:1fr 1fr;gap:.8rem;margin:1rem 0 .9rem}
.card{position:relative;overflow:hidden;min-width:0;padding:1rem 1.05rem 1rem;border-radius:16px;
  background:linear-gradient(160deg,color-mix(in srgb,var(--c) 22%,rgba(17,27,48,.85)),rgba(17,27,48,.82) 70%);
  border:1px solid color-mix(in srgb,var(--c) 38%,rgba(255,255,255,.08))}
.card::before{content:"";position:absolute;inset:0 0 auto 0;height:4px;background:var(--c)}
.card .wm{position:absolute;right:.7rem;top:.4rem;font-size:3.4rem;font-weight:800;opacity:.07;
  letter-spacing:-.03em;pointer-events:none}
.card .name{font-size:1rem;font-weight:600;color:#ECF5FF;min-height:2.5em;line-height:1.25;padding-right:2rem}
.card .pct{font-size:clamp(2.5rem,8vw,4.2rem);font-weight:800;line-height:1.05;color:var(--c);
  letter-spacing:-.03em;margin:.2rem 0 .1rem}
.card .tag{display:inline-block;font-size:.68rem;font-weight:800;letter-spacing:.1em;border-radius:6px;
  padding:.08rem .5rem;background:rgba(255,255,255,.16);color:#fff}
.card .tag.home{background:var(--c);color:#0b1013}
.card .meta{margin-top:.6rem;font-size:.8rem;color:#A9BED9}
.vs{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);z-index:2;width:2.3rem;height:2.3rem;
  border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.72rem;
  font-weight:800;letter-spacing:.06em;color:#D2E3FA;background:rgba(8,13,27,.92);
  border:1px solid rgba(255,255,255,.18)}
.bar{display:flex;height:2.3rem;border-radius:999px;overflow:hidden;background:rgba(255,255,255,.08);
  box-shadow:inset 0 1px 3px rgba(0,0,0,.4)}
.bar .seg{display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.88rem;
  color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.65);white-space:nowrap;overflow:hidden;
  transition:width .4s ease}
.note{color:#A9BED9;font-size:.85rem;margin:.7rem 0 .4rem}
.note b{color:#fff}

/* ---- tables ---- */
table.t{width:100%;border-collapse:collapse;font-size:.86rem}
table.t th{text-align:left;font-weight:600;color:#A3B8D4;font-size:.72rem;letter-spacing:.06em;
  text-transform:uppercase;padding:.35rem .4rem;border-bottom:1px solid rgba(255,255,255,.08)}
table.t td{padding:.5rem .4rem;border-bottom:1px solid rgba(255,255,255,.05);color:#DEECFF;
  vertical-align:top}
table.t td.n,table.t th.n{text-align:right;font-variant-numeric:tabular-nums}
table.t td.nw{white-space:nowrap}
table.t tr.best td{color:#fff;font-weight:650}
table.t tr.off td{color:#849AB8}
table.t .sub{display:block;font-size:.74rem;color:#A3B8D4;font-weight:400}
.verdict{font-size:.74rem;color:#A3B8D4;margin-left:.3rem}
.settings{display:flex;flex-wrap:wrap;gap:.4rem;margin:.2rem 0 .8rem}
.small{font-size:.8rem;color:#A9BED9;line-height:1.5;margin:.5rem 0}
.small b{color:#ECF5FF}
.callout{margin:.6rem 0;padding:.55rem .75rem;border-radius:12px;font-size:.82rem;line-height:1.45;
  background:rgba(245,196,81,.1);border:1px solid rgba(245,196,81,.25);color:#f1dfa5}
.mini{display:grid;grid-template-columns:3.2rem 1fr 3.6rem;gap:.4rem;align-items:center;
  font-size:.78rem;color:#D2E3FA;margin:.18rem 0;font-variant-numeric:tabular-nums}
.mini .track{height:.5rem;border-radius:99px;background:rgba(255,255,255,.07);overflow:hidden}
.mini .fill{height:100%;background:rgba(255,255,255,.28)}
.mini.sel .fill{background:#9ED8FF}.mini.sel{color:#fff;font-weight:650}
.mini-h{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:#A3B8D4;margin:.8rem 0 .3rem}

@media (max-width:640px){
  .st-key-win_matchup,.st-key-win_perf,.st-key-win_data{padding:0 .8rem .9rem;border-radius:16px}
  .wtitle{margin:0 -.8rem .8rem}
  .hero{gap:.55rem}.card{padding:.75rem .75rem .8rem}.card .name{font-size:.86rem}
  .card .wm{font-size:2.6rem}.vs{width:1.9rem;height:1.9rem;font-size:.62rem}
  .menubar{font-size:.76rem}
}
"""


def compact(html):
    """Collapse whitespace between tags and drop blank lines."""
    return re.sub(r">\s+<", "><", html).strip()


def wallpaper_css(color_a, color_b):
    """Soft glows behind the windows in the two selected teams' colors."""
    return (".stApp{background:"
            f"radial-gradient(900px 520px at 12% -5%,{color_a}10,transparent 62%),"
            f"radial-gradient(900px 520px at 88% 0%,{color_b}10,transparent 62%),"
            "radial-gradient(ellipse at 62% 0%,#25487944,transparent 58%),"
            "linear-gradient(165deg,#080D1B,#0D172C 55%,#090F20) fixed !important}")


def distinct_colors(c1, c2):
    """Return both colors, swapping the second for grey if they are too similar."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return (c1, c2) if sum(abs(x - y) for x, y in zip(a, b)) > 120 else (c1, NEUTRAL_ACCENT)


def split_percentages(p_a):
    """Round Team A to 0.1% and give Team B the remainder, so the pair is exactly 100."""
    pct_a = round(p_a * 100, 1)
    return pct_a, round(100 - pct_a, 1)


# --------------------------------------------------------------------- shell
def top_bar_html(results_through, schedule_label, schedule_state):
    state = {"ok": "", "stale": " warn", "none": " bad"}.get(schedule_state, "")
    return compact(f"""
    <div class="menubar dash"><div class="mb-right"><span class="pill">Results through {esc(results_through)}</span>
    <span class="pill{state}"><i></i>{esc(schedule_label)}</span></div></div>""")


def window_title(title, subtitle=""):
    sub = f'<span class="ws">{esc(subtitle)}</span>' if subtitle else ""
    return compact(f'<div class="wtitle dash"><span class="dots"><i></i><i></i><i></i></span>'
                   f'<span class="wt">{esc(title)}</span>{sub}</div>')


# ------------------------------------------------------------------ matchup
def schedule_strip_html(game_info=None, reason=""):
    """game_info = dict(date, time, home_name) for a scheduled game, else hypothetical."""
    if game_info:
        return compact(f"""<div class="strip dash"><span class="badge sched">Next scheduled game</span>
        <span class="chip"><b>{esc(game_info['date'])}</b></span>
        <span class="chip">Tipoff <b>{esc(game_info['time'])}</b></span>
        <span class="chip">Home: <b>{esc(game_info['home_name'])}</b></span></div>""")
    return compact(f"""<div class="strip dash"><span class="badge hypo">Hypothetical matchup</span>
    <span class="chip muted">{esc(reason)} Choose a venue to simulate one.</span></div>""")


@lru_cache(maxsize=32)
def logo_html(abbr):
    path = Path(__file__).with_name("logos") / f"{abbr}.svg"
    if not re.fullmatch(r"[A-Z]{3}", abbr) or not path.is_file():
        return f'<span class="logo-fallback" aria-hidden="true">{esc(abbr)}</span>'
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<img class="team-logo" src="data:image/svg+xml;base64,{encoded}" alt="">'


def home_hero_html():
    return compact("""
        <section class="tipoff-hero dash">
            <div class="hero-copy">
                <div class="hero-title" role="heading" aria-level="1">Before the ball<br><span>goes up.</span></div>
                <p>See who’s favored in the next NBA matchup and explore
                two weeks of win probabilities for any team.</p>
            </div>
            <div class="court-visual" aria-hidden="true">
                <div class="court-sheet">
                    <i class="court-midline"></i><i class="court-circle"></i>
                    <i class="court-key court-key-left"></i><i class="court-key court-key-right"></i>
                </div>
            </div>
        </section>
    """)


def home_game_html(label, day, time, away, home, neutral):
    def team_card(team, venue):
        abbr, name, pct = team
        return compact(f"""
            <div class="featured-team">
                {logo_html(abbr)}
                <div><span class="featured-venue">{esc(venue)}</span>
                    <strong>{esc(name)}</strong></div>
                <span class="featured-odds">{pct:.1f}%</span>
            </div>
        """)

    venue = "Neutral court" if neutral else None
    return compact(f"""
        <section class="featured-game dash">
            <header><h2>{esc(label)}</h2><span>{esc(day)} · {esc(time)}</span></header>
            <div class="featured-pair">
                {team_card(away, venue or "Away")}{team_card(home, venue or "Home")}
            </div>
            <div class="featured-bar" style="--away:{away[2]:.1f}%;"
                 role="img" aria-label="{esc(away[1])} {away[2]:.1f}%, {esc(home[1])} {home[2]:.1f}%"></div>
            <p>Model-estimated win probabilities</p>
        </section>
    """)


def home_slate_heading_html(title, date, count):
    games = "game" if count == 1 else "games"
    return compact(f"""
        <div class="home-slate-heading dash">
            <div role="heading" aria-level="2">{esc(title)}</div>
            <span>{esc(date)} · {count} {games} · Eastern time</span>
        </div>
    """)


def home_slate_card_html(time, away, home, neutral):
    def side(team):
        abbr, name, pct = team
        return (f'<div class="slate-team">{logo_html(abbr)}'
                f'<span>{esc(name)}</span><strong>{pct:.1f}%</strong></div>')

    venue = " · Neutral court" if neutral else ""
    return compact(f"""
        <div class="slate-card dash">
            <div class="slate-time">{esc(time)}{venue}</div>
            {side(away)}{side(home)}
        </div>
    """)


def home_game_empty_html(message):
    return compact(f'<section class="featured-game dash"><h2>Next matchup</h2>'
                   f'<p>{esc(message)}</p></section>')


def schedule_row_html(team, opponent, opponent_name, venue, tipoff, probability):
    return compact(f"""
        <div class="schedule-row dash">
            <div class="schedule-logos">{logo_html(team)}{logo_html(opponent)}</div>
            <div><b>{esc(opponent_name)}</b>
                <div class="small">{esc(venue)} · {esc(tipoff)}</div></div>
            <strong class="schedule-prob">{probability:.1%}</strong>
        </div>
    """)


def hero_html(side_a, side_b):
    """side = dict(name, abbr, color, pct, tag, rating, form). Percentages sum to 100."""
    def card(s):
        tag_class = " home" if s["tag"] == "HOME" else ""
        return (f'<div class="card" style="--c:{s["color"]}"><span class="wm">{esc(s["abbr"])}</span>'
                f'<div class="name team-heading">{logo_html(s["abbr"])}{esc(s["name"])}</div><div class="pct">{s["pct"]:.1f}%</div>'
                f'<span class="tag{tag_class}">{esc(s["tag"])}</span>'
                f'<div class="meta">Elo {s["rating"]:.0f} · Last 5 avg margin {s["form"]:+.1f}</div></div>')

    label = f'{side_a["name"]} {side_a["pct"]:.1f}%, {side_b["name"]} {side_b["pct"]:.1f}%'
    def seg(side):
        text = f'{side["pct"]:.1f}%' if side["pct"] >= 14 else ""   # too narrow to fit a label
        return (f'<div class="seg" style="width:{side["pct"]}%;background:{side["color"]}">'
                f'{text}</div>')

    bar = f'<div class="bar" role="img" aria-label="{esc(label)}">{seg(side_a)}{seg(side_b)}</div>'
    return compact(f'<div class="hero dash">{card(side_a)}{card(side_b)}<div class="vs">VS</div></div>'
                   f'<div class="dash">{bar}</div>')


def roster_cards_html(roster, averages, accent, averages_unavailable=False, *, limit=None):
    """Render the current roster with team-specific NBA season averages."""
    def scoring(player):
        return averages.get(player["PLAYER_ID"], {}).get("PTS", -1)

    ranked = sorted(roster, key=lambda row: (-scoring(row), row["Player"]))
    if limit is not None:
        ranked = [player for player in ranked if player["PLAYER_ID"] in averages][:limit]

    cards = []
    for player in ranked:
        player_id = int(player["PLAYER_ID"])
        name = esc(player["Player"])
        jersey = esc(str(player["Jersey"]))
        position = esc(player["Position"])
        stats = averages.get(player_id)
        if stats:
            metrics = "".join(
                f'<div><dt>{label}</dt><dd>{stats[field]:{fmt}}</dd></div>'
                for label, field, fmt in (
                    ("PTS", "PTS", ".1f"), ("REB", "REB", ".1f"), ("AST", "AST", ".1f"),
                    ("MIN", "MIN", ".1f"), ("GP", "GP", ".0f"),
                )
            )
            stat_html = f'<dl class="roster-metrics">{metrics}</dl>'
        else:
            message = ("Season stats unavailable" if averages_unavailable
                       else "No season stats with this team")
            stat_html = f'<div class="roster-empty">{message}</div>'
        photo = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"
        cards.append(compact(f"""
            <article class="roster-card">
              <div class="roster-player">
                <img src="{photo}" alt="" loading="lazy" width="120" height="88">
                <div><span class="roster-meta">#{jersey} · {position}</span>
                  <strong>{name}</strong></div>
              </div>
              {stat_html}
            </article>
        """))
    return f'<div class="roster-grid dash" style="--team-accent:{esc(accent)}">{"".join(cards)}</div>'


def players_to_watch_html(teams, error=None):
    if error:
        return compact("""
            <section class="watch-section dash"><h3>Players to Watch</h3>
            <p>Player stats are temporarily unavailable. Refresh data to try again.</p></section>
        """)

    cards = []
    for abbr, team, player in teams:
        photo = logo_html(abbr)
        if player:
            name = esc(player["name"])
            if player.get("player_id") is not None:
                photo_url = (
                    "https://cdn.nba.com/headshots/nba/latest/1040x760/"
                    f"{int(player['player_id'])}.png"
                )
                photo = f'<img class="watch-photo" src="{photo_url}" alt="" loading="lazy">' 
            stats = " · ".join(
                f'{player[key]:.1f} {label}'
                for key, label in (("points", "PTS"), ("rebounds", "REB"), ("assists", "AST"))
            )
            games = player["games"]
            window = player.get("window", games)
            coverage = (f"Team’s last {games} games" if games == window
                        else f"{games} of the team’s last {window} games with complete stats")
            detail = f'<b>{name}</b><span>{stats}</span><small>{coverage}</small>'
        else:
            detail = "<span>Complete player stats unavailable.</span>"
        cards.append(
            f'<div class="watch-card">{photo}<div><small>{esc(team)}</small>{detail}</div></div>'
        )
    return compact(f"""
        <section class="watch-section dash"><h3>Players to Watch</h3>
        <p>Leading scorer · Per team game, including games the player missed</p>
        <div class="watch-grid">{''.join(cards)}</div></section>
    """)


def breakdown_html(name_a, name_b, rating_a, rating_b, steps, form_on):
    """steps = [(label, p_a_after_step, applied?)]: probabilities for Team A."""
    rows, previous = [], None
    for label, p_a, applied in steps:
        change = "" if previous is None else f' <span class="sub">{(p_a - previous) * 100:+.1f} pts</span>'
        cls = "" if applied else ' class="off"'
        pa, pb = split_percentages(p_a)
        rows.append(f"<tr{cls}><td>{esc(label)}</td><td class='n'>{pa:.1f}%{change}</td>"
                    f"<td class='n'>{pb:.1f}%</td></tr>")
        if applied:
            previous = p_a
    off = "" if form_on else ('<p class="small">Recent form is off, so it is shown greyed out and '
                              "not included in the win probabilities above.</p>")
    return compact(f"""<div class="dash"><table class="t"><thead><tr><th>Step</th>
    <th class="n">{esc(name_a)}</th><th class="n">{esc(name_b)}</th></tr></thead><tbody>
    <tr><td>Elo rating</td><td class="n">{rating_a:.0f}</td><td class="n">{rating_b:.0f}</td></tr>
    {''.join(rows)}</tbody></table>{off}
    <p class="small">Recent form uses raw point margins. A team that built its streak against weak
    opponents can look hotter than it is, so treat that step as a nudge, not a verdict.</p></div>""")


# -------------------------------------------------------------- performance
def _verdict(diff, se):
    if se is None:
        return "too few games"
    if diff + 2 * se < 0:
        return "clearly better"
    if diff - 2 * se > 0:
        return "clearly worse"
    return "no clear difference"


def performance_html(report):
    best = min(m["brier"] for m in report["models"])
    rows = []
    for m in report["models"]:
        if m["key"] == "elo":
            versus = '<span class="verdict">baseline</span>'
        else:
            versus = (f'{m["diff_vs_elo"]:+.4f}'
                      f'<span class="sub">± {m["diff_se"]:.4f} · {_verdict(m["diff_vs_elo"], m["diff_se"])}</span>'
                      if m["diff_se"] is not None else "—")
        cls = ' class="best"' if m["brier"] == best else ""
        rows.append(f'<tr{cls}><td>{esc(m["label"])}</td><td class="n">{m["brier"]:.4f}</td>'
                    f'<td class="n">{m["games"]:,}</td><td class="n">{versus}</td></tr>')
    rows.append(f'<tr class="off"><td>Coin flip (always 50%)</td><td class="n">{report["coin_flip"]:.4f}</td>'
                f'<td class="n">—</td><td class="n"></td></tr>')

    sel = report["selected"]
    edge = (' <span class="verdict">(top of range tried)</span>'
            if sel["home_bonus"] == max(elo.BONUS_GRID) else "")
    chips = (f'<span class="chip">Home bonus <b>+{sel["home_bonus"]} Elo</b>{edge}</span>'
             f'<span class="chip">Carryover <b>{sel["carryover"]:.2f}</b></span>'
             f'<span class="chip">Form weight <b>{sel["form_weight"]:g}</b></span>')

    sp = report["splits"]
    seasons = report["seasons"]
    span = f"{seasons[0]}–{seasons[-1] + 1}" if seasons else ""
    split_rows = "".join(
        f'<tr><td>{name}</td><td class="n">{sp[key]["games"]:,}</td>'
        f'<td class="n nw">{esc(str(sp[key]["start"]))} → {esc(str(sp[key]["end"]))}</td></tr>'
        for name, key in (("Warm-up (build ratings)", "warmup"),
                          ("Validation (choose settings)", "validation"),
                          ("Test (report results)", "test")))

    warn = ""
    if len(seasons) < 2:
        warn = ('<div class="callout">Only the current season is loaded, so the validation period is '
                'tiny and the chosen settings are noisy. Run <b>python fetch_data.py --history</b> '
                'to add past seasons.</div>')
    elif sp["test"]["games"] < 500:
        warn = '<div class="callout">The test period is small, so differences may be noise.</div>'

    return compact(f"""<div class="dash"><div class="settings">{chips}</div>{warn}
    <table class="t"><thead><tr><th>Model</th><th class="n">Brier</th><th class="n">Test games</th>
    <th class="n">Change vs Elo</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <p class="small"><b>Brier score</b> is the average squared miss between the predicted win
    probability and what happened (1 for a win, 0 for a loss). 0 is perfect, always saying 50% scores
    0.25, and lower is better. Test games are newer than everything used to choose settings.</p>
    <table class="t"><thead><tr><th>Period · {esc(span)}</th><th class="n">Games</th><th class="n">Dates</th>
    </tr></thead><tbody>{split_rows}</tbody></table></div>""")


def search_html(report):
    s, sel = report["search"], report["selected"]

    def block(title, values, chosen, fmt):
        lo, hi = min(values.values()), max(values.values())
        span = (hi - lo) or 1
        rows = "".join(
            f'<div class="mini{" sel" if k == chosen else ""}"><span>{fmt(k)}</span>'
            f'<span class="track"><span class="fill" style="width:{25 + 75 * (1 - (v - lo) / span):.0f}%">'
            f'</span></span><span>{v:.4f}</span></div>' for k, v in values.items())
        return f'<div class="mini-h">{esc(title)}</div>{rows}'

    return compact(f"""<div class="dash">
    <p class="small">Validation Brier for each candidate (longer bar = better). Each bonus shows its
    best carryover, and each carryover its best bonus. The test period was not used here.</p>
    {block("Home bonus (Elo points)", s["bonus"], sel["home_bonus"], lambda k: f"{k}")}
    {block("Carryover into a new season", s["carryover"], sel["carryover"], lambda k: f"{k:.2f}")}
    {block("Recent-form weight", s["form_weight"], sel["form_weight"], lambda k: f"{k:g}")}
    <p class="small">With no form adjustment the validation score is {s["no_form"]:.4f}.</p></div>""")


def outside_comparison(name_a, p_model, p_outside):
    """Brier contribution of one game for the model vs an outside estimate (Team A's win prob)."""
    win = ((1 - p_model) ** 2, (1 - p_outside) ** 2)
    lose = (p_model ** 2, p_outside ** 2)
    return {"gap_pts": (p_model - p_outside) * 100, "win": win, "lose": lose}


def outside_html(name_a, p_model, p_outside):
    c = outside_comparison(name_a, p_model, p_outside)
    return compact(f"""<div class="dash"><table class="t"><thead><tr><th>If this happens</th>
    <th class="n">Model</th><th class="n">Outside</th></tr></thead><tbody>
    <tr><td>{esc(name_a)} win</td><td class="n">{c['win'][0]:.3f}</td><td class="n">{c['win'][1]:.3f}</td></tr>
    <tr><td>{esc(name_a)} lose</td><td class="n">{c['lose'][0]:.3f}</td><td class="n">{c['lose'][1]:.3f}</td></tr>
    </tbody></table><p class="small">Model is <b>{c['gap_pts']:+.1f} pts</b> from the outside estimate
    (lower squared miss is better). One game cannot show which is better calibrated. Outside numbers may also
    reflect injuries and betting-market information that this model does not use. Compare Brier scores over
    many games, as the table above does, and don't tune settings to match one estimate.</p></div>""")

CSS += """
.dash .team-logo,.dash .logo-fallback{width:42px;height:42px;object-fit:contain;flex:none}
.dash .logo-fallback{display:inline-grid;place-items:center;background:#ffffff12;border-radius:8px;font-size:.75rem}
.dash .team-heading,.dash .schedule-logos{display:flex;align-items:center;gap:.5rem}
.schedule-row.dash{display:grid;grid-template-columns:auto minmax(0,1fr) auto;
  align-items:center;gap:.85rem;padding:.6rem .8rem;border-radius:12px;
  background:#ffffff05;border:1px solid #ffffff12}
.dash .schedule-prob{font-size:1.2rem;font-variant-numeric:tabular-nums}
@media(max-width:480px){.dash .team-logo,.dash .logo-fallback{width:28px;height:28px}
.schedule-row.dash{gap:.45rem;padding:.5rem}.dash .schedule-logos{gap:.2rem}}
"""

CSS += """
.st-key-tipoff_header [data-testid="stHorizontalBlock"]{flex-wrap:nowrap;align-items:center}
.st-key-tipoff_header [data-testid="stColumn"]:last-child{flex:0 0 auto;min-width:0;width:auto}
.st-key-tipoff_header .menubar{margin:0}
.st-key-tipoff_header [data-testid="stPopover"]{display:flex;justify-content:flex-end}
.tipoff-hero.dash{
  padding:clamp(2.8rem,8vw,7rem) 0 1rem;max-width:920px;
}
.tipoff-hero .hero-title{
  margin:0;padding:0;color:#F0F7FF;font-weight:720;letter-spacing:-.075em;
  font-size:clamp(3rem,8vw,7.5rem);line-height:.92;
}
.tipoff-hero p{
  color:#ABC2E0;font-size:clamp(1rem,2vw,1.3rem);max-width:32rem;margin:1.5rem 0 0;
}
.st-key-home_actions{max-width:470px;margin-bottom:clamp(1.6rem,4vw,3.2rem)}
.featured-game.dash{
  border:1px solid #9ED8FF29;border-radius:22px;padding:clamp(1rem,3vw,2rem);
  background:radial-gradient(ellipse at 75% 0%,#2B548E3D,transparent 74%),#111B30;
  box-shadow:0 20px 70px #0004;
}
.featured-game header{display:flex;justify-content:space-between;gap:.5rem;flex-wrap:wrap;align-items:center}
.featured-game h2{font-size:1.1rem;padding:0;margin:0}
.featured-game header span,.featured-game p,.featured-venue{color:#ABC2E0;font-size:.85rem}
.featured-game p{margin:.85rem 0 0}
.featured-pair{display:grid;grid-template-columns:1fr 1fr;gap:.7rem;margin-top:1rem}
.featured-team{
  display:grid;grid-template-columns:auto 1fr auto;gap:.7rem;align-items:center;
  background:#ffffff06;border:1px solid #ffffff12;border-radius:14px;padding:.9rem;
}
.featured-team strong,.featured-venue{display:block}
.featured-odds{color:#E7F5FF;font-size:clamp(1.25rem,3vw,2.25rem);font-variant-numeric:tabular-nums}
@media(max-width:620px){
  .st-key-tipoff_header .mb-right{display:none}
  .featured-pair{grid-template-columns:1fr}
  .featured-team{padding:.65rem}
}
"""

CSS += """
.st-key-win_matchup{padding:0 clamp(1rem,3vw,2.4rem) 2.4rem}
.st-key-win_matchup .wtitle{padding-block:1.1rem}
.st-key-win_matchup [data-testid="stTabContent"]{padding-top:1.25rem}
.st-key-win_matchup [data-testid="stExpander"]{margin-bottom:1.1rem}
.schedule-row.dash{min-height:94px;gap:1.15rem;padding:1rem clamp(.85rem,2.3vw,1.75rem)}
.schedule-row.dash .team-logo{width:50px;height:50px}
.schedule-row.dash .schedule-prob{font-size:clamp(1.25rem,2.4vw,1.85rem)}
.tipoff-hero.dash{
  position:relative;isolation:isolate;max-width:none;overflow:hidden;
  min-height:clamp(275px,29vw,365px);display:flex;align-items:center;
  border:1px solid #9ED8FF29;border-radius:28px;margin-top:clamp(1.4rem,3vw,3rem);
  padding:clamp(1.7rem,4vw,3.6rem);
  background:radial-gradient(ellipse at 87% 52%,#355E9B54,transparent 59%),#0D162B;
}
.hero-copy{position:relative;z-index:1}
.tipoff-hero .hero-title{font-size:clamp(3.2rem,6.6vw,6.3rem);line-height:.91}
.tipoff-hero .hero-title span{color:#9ED8FF}
.court-visual{
  position:absolute;inset:0 0 0 32%;display:grid;place-items:center;pointer-events:none;
  perspective:850px;opacity:.82;mask-image:linear-gradient(90deg,transparent,#000 48%);
}
.court-sheet{
  position:relative;width:92%;max-width:840px;aspect-ratio:1.88;
  border:2px solid #9ED8FFAB;border-radius:14px;transform:rotateX(35deg) rotateZ(-22deg);
  background:repeating-linear-gradient(90deg,#A8DDFF16 0 1px,transparent 1px 30px),#162C4CAA;
  box-shadow:0 0 45px #7FC3FF3A,inset 0 0 45px #7FC3FF26;
}
.court-sheet i{position:absolute;display:block;border:2px solid #9ED8FF90}
.court-midline{top:0;bottom:0;left:50%;border-width:0 0 0 2px!important}
.court-circle{width:22%;aspect-ratio:1;left:50%;top:50%;transform:translate(-50%,-50%);border-radius:50%}
.court-key{width:20%;height:35%;top:32.5%}
.court-key-left{left:0;border-radius:0 60% 60% 0}
.court-key-right{right:0;border-radius:60% 0 0 60%}
.st-key-home_actions{margin-top:1.1rem;margin-bottom:clamp(2.2rem,5vw,4.5rem)}
.featured-game.dash{padding:clamp(1.25rem,4vw,3rem)}
.featured-pair{gap:1rem;margin-top:1.4rem}
.featured-team{min-height:106px;padding:clamp(.8rem,2.4vw,1.75rem)}
.featured-bar{
  height:9px;border-radius:999px;margin-top:1.25rem;
  background:linear-gradient(90deg,#9ED8FF 0 var(--away),#3D5677 var(--away) 100%);
}
@media(max-width:620px){
  .tipoff-hero.dash{min-height:305px;align-items:flex-start;padding-top:2.4rem}
  .court-visual{inset:36% -18% -4% 12%;mask-image:linear-gradient(180deg,transparent,#000)}
  .schedule-row.dash{min-height:76px;gap:.55rem;padding:.65rem}
  .schedule-row.dash .team-logo{width:29px;height:29px}
}
"""

CSS += """
.watch-section.dash{margin-top:1rem}
.watch-section h3{font-size:1.12rem;margin:0;padding:0}
.watch-section p,.watch-card small{color:#ABC2E0;font-size:.85rem}
.watch-section p{margin:.4rem 0 .8rem}
.watch-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.7rem}
.watch-card{padding:.9rem;border:1px solid #ffffff16;border-radius:12px;
  display:flex;gap:.7rem;align-items:center;background:#ffffff06}
.watch-card .watch-photo{width:66px;height:49px;object-fit:contain;flex:none}
.watch-card div>*{display:block}
.watch-card b{font-size:1.05rem}
.watch-card span{font-variant-numeric:tabular-nums}
@media(max-width:620px){.watch-grid{grid-template-columns:1fr}}
"""

CSS += """
.st-key-home_actions .stButton > button[kind="primary"]{
  background:#D63828;border-color:#D63828;color:#fff;
  font-weight:700;box-shadow:0 4px 18px #D6382838;
}
.st-key-home_actions .stButton > button[kind="primary"]:hover{
  background:#BF3023;border-color:#BF3023;color:#fff;
}
.st-key-home_actions .stButton > button[kind="primary"]:focus-visible{
  outline:2px solid #9ED8FF;outline-offset:3px;
}
"""

CSS += """
.st-key-tipoff_header .menubar{justify-content:flex-end;background:transparent;border:0;padding:0}
.st-key-check_up_home .stButton>button{
  padding:0;color:#ECF5FF;
  font-size:clamp(1.65rem,3.5vw,3rem);font-weight:820;letter-spacing:-.06em;white-space:nowrap;
  display:flex;align-items:center;gap:.35rem;line-height:1;
}
.st-key-check_up_home .stButton>button p{font-size:inherit;font-weight:inherit}
.st-key-check_up_home button,
.st-key-check_up_home button:is(:hover,:active,:focus,:focus-visible){
  background:transparent!important;border:0!important;
  outline:0!important;box-shadow:none!important;
}
.st-key-check_up_home button:hover{opacity:.86}
.st-key-check_up_home button:focus-visible{
  filter:drop-shadow(0 0 4px #9ED8FF) drop-shadow(0 0 2px #9ED8FF);
}
.st-key-tipoff_header [data-testid="stColumn"]:first-child{flex:0 0 auto;min-width:0;width:auto}
@media(max-width:620px){
  .st-key-tipoff_header [data-testid="stColumn"]:nth-child(2){display:none}
  .st-key-tipoff_header [data-testid="stHorizontalBlock"]{justify-content:space-between}
}
"""

CSS += """
.st-key-home_actions{margin-bottom:clamp(1rem,3vw,2rem)}
.home-slate-heading.dash{display:flex;justify-content:space-between;align-items:baseline;
  flex-wrap:wrap;gap:.4rem;margin-top:.75rem}
.home-slate-heading [role="heading"]{font-size:clamp(1.35rem,3vw,2rem);font-weight:730}
.home-slate-heading span,.slate-time{color:#ABC2E0;font-size:.85rem}
.slate-card.dash{padding:1rem;border-radius:14px;background:#111B30;
  border:1px solid #9ED8FF29}
.slate-team{display:grid;grid-template-columns:auto minmax(0,1fr) auto;
  align-items:center;gap:.6rem;margin-top:.55rem}
.slate-team strong{color:#9ED8FF;font-variant-numeric:tabular-nums}
.slate-team .team-logo,.slate-team .logo-fallback{width:32px;height:32px}
.st-key-home_team_search{margin-top:1.4rem;max-width:560px}
"""

CSS += """
.roster-grid.dash{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,275px),1fr));gap:1rem}
.roster-card{border:1px solid #9ED8FF26;border-top:2px solid var(--team-accent);
  border-radius:15px;background:#101b31;overflow:hidden}
.roster-player{display:flex;align-items:center;gap:.8rem;padding:.8rem .9rem 0;
  background:linear-gradient(130deg,color-mix(in srgb,var(--team-accent) 17%,transparent),transparent 72%);
  min-height:100px}
.roster-player img{width:clamp(70px,8vw,106px);height:auto;aspect-ratio:120/88;object-fit:contain;flex:none}
.roster-player strong{display:block;color:#ECF5FF;font-size:1.1rem;line-height:1.2}
.roster-meta,.roster-metrics dt,.roster-empty{color:#ABC2E0;font-size:.76rem}
.roster-metrics{display:grid;grid-template-columns:repeat(5,1fr);gap:.3rem;margin:0;
  padding:.85rem;text-align:center;border-top:1px solid #9ED8FF1c}
.roster-metrics dd{margin:.22rem 0 0;color:#ECF5FF;font-weight:700;font-variant-numeric:tabular-nums}
.roster-empty{padding:1rem;border-top:1px solid #9ED8FF1c}
"""

CSS += """
.stButton > button,.stApp [data-testid="stPopoverButton"]{
  min-height:3.1rem;padding:.62rem 1.15rem;font-size:1.04rem;
}
.stButton > button p,.stApp [data-testid="stPopoverButton"] p{font-size:inherit}
.st-key-check_up_home .stButton>button{padding:0;min-height:0;font-size:clamp(1.65rem,3.5vw,3rem)}
[data-baseweb="select"] > div{min-height:54px}
[data-testid="stExpander"] summary{min-height:3rem;align-items:center}
.st-key-home_team_search{max-width:640px;margin:1.4rem 0 1.7rem}
.st-key-schedule_team_overview{padding:1rem;background:#0D172C;border:1px solid #9ED8FF25;
  border-radius:16px}
.st-key-schedule_team_overview .roster-grid{grid-template-columns:minmax(0,1fr)}
"""
