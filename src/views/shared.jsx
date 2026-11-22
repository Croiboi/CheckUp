import { Link } from '../router'
import { useApp } from '../context'
import { useApi } from '../api'
import { Headshot, Logo, OddsBar, Problem, Skeleton, pct } from '../components/bits'

// ---------------------------------------------------------------- matchup
export function useMatchup(a, b, game, venue) {
  const { form } = useApp()
  const q = new URLSearchParams({ a, b, form: form ? 1 : 0 })
  if (game) q.set('game', game)
  if (venue) q.set('venue', venue)
  return useApi(`/api/matchup?${q}`)
}

export function MatchupBody({ data }) {
  const { a, b } = data
  const label = `${a.name} ${pct(a.pct)}, ${b.name} ${pct(b.pct)}`
  const side = (s) => (
    <div className="side" style={{ '--c': s.color }}>
      <div className="side-name"><Logo abbr={s.abbr} size={44} /><span>{s.name}</span></div>
      <div className="side-pct">{pct(s.pct)}</div>
      <span className={`tag ${s.tag === 'Home' ? 'home' : ''}`}>{s.tag}</span>
      <p className="meta">Elo {s.rating.toFixed(0)} · Last 5 avg margin {s.form >= 0 ? '+' : ''}{s.form.toFixed(1)}</p>
    </div>
  )
  return (
    <div className="matchup">
      <div className="sides">{side(a)}<span className="vs" aria-hidden="true">vs</span>{side(b)}</div>
      <OddsBar aPct={a.pct} bPct={b.pct} aColor={a.color} bColor={b.color} label={label} />
      <div className="matchup-links">
        <Link to={`/teams/${a.abbr}`} className="btn">{a.name} roster</Link>
        <Link to={`/teams/${b.abbr}`} className="btn">{b.name} roster</Link>
      </div>
      {data.formOn && (
        <p className="note">Recent form moves <b>{a.name}</b> by <b>{data.formShift >= 0 ? '+' : ''}{data.formShift.toFixed(1)}</b> points versus Elo plus home court.</p>
      )}
      <details>
        <summary>Breakdown: Elo, home court, recent form</summary>
        <div className="scroll-x">
          <table className="t">
            <thead><tr><th>Step</th><th className="n">{a.name}</th><th className="n">{b.name}</th></tr></thead>
            <tbody>
              <tr><td>Elo rating</td><td className="n">{a.rating.toFixed(0)}</td><td className="n">{b.rating.toFixed(0)}</td></tr>
              {data.steps.map((s) => (
                <tr key={s.label} className={s.applied ? '' : 'off'}>
                  <td>{s.label}</td>
                  <td className="n">{pct(s.a)}{s.delta != null && <small>{s.delta >= 0 ? '+' : ''}{s.delta.toFixed(1)} pts</small>}</td>
                  <td className="n">{pct(s.b)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!data.formOn && <p className="small">Recent form is off, so it is greyed out and not included in the win probabilities above.</p>}
        <p className="small">Recent form uses raw point margins. A team that built its streak against weak opponents can look hotter than it is, so treat that step as a nudge, not a verdict.</p>
      </details>
      <Watch data={data} />
    </div>
  )
}

function Watch({ data }) {
  const { a, b, watch } = data
  if (watch.error) {
    return <section className="watch"><h3>Players to watch</h3><p className="small">Player stats are temporarily unavailable. Refresh data to try again.</p></section>
  }
  const card = (team, p) => (
    <div className="watch-card">
      {p?.playerId ? <Headshot id={p.playerId} name={p.name} /> : <Logo abbr={team.abbr} size={48} />}
      <div>
        <small>{team.name}</small>
        {p ? (<>
          <b>{p.name}</b>
          <span>{p.points.toFixed(1)} PTS · {p.rebounds.toFixed(1)} REB · {p.assists.toFixed(1)} AST</span>
          <small>{p.games === p.window ? `Team’s last ${p.games} games` : `${p.games} of the team’s last ${p.window} games with complete stats`}</small>
        </>) : <span>Complete player stats unavailable.</span>}
      </div>
    </div>
  )
  return (
    <section className="watch">
      <h3>Players to watch</h3>
      <p className="small">Leading scorer per team game, including games the player missed.</p>
      <div className="watch-grid">{card(a, watch.a)}{card(b, watch.b)}</div>
    </section>
  )
}

// -------------------------------------------------------------- team stats
export function TeamStats({ abbr }) {
  const { data, error, retry } = useApi(`/api/team/${abbr}/profile`)
  if (error) return <Problem error={error} retry={retry} what="team stats" />
  if (!data) return <Skeleton rows={2} height={110} />
  const s = data.stats
  if (!s) return <p className="small">No completed regular-season games are available for this team.</p>
  const items = [
    ['Wins–losses', s.record], ['Win percentage', `${(s.win_pct * 100).toFixed(1)}%`],
    ['Current streak', s.streak], [`Last ${s.recent_count} games`, s.recent_record],
    ['Points per game', s.points_for.toFixed(1)], ['Opponent points', s.points_against.toFixed(1)],
  ]
  return (
    <>
      <dl className="stats">{items.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
      <details>
        <summary>Recent results</summary>
        <div className="scroll-x">
          <table className="t">
            <thead><tr><th>Date</th><th>Opponent</th><th>Venue</th><th>Result</th><th className="n">Score</th></tr></thead>
            <tbody>{s.results.map((g) => (
              <tr key={g.date + g.opponent}><td className="nw">{g.date}</td><td>{g.opponentName}</td><td>{g.venue}</td>
                <td><b className={g.result === 'W' ? 'win' : 'loss'}>{g.result}</b></td><td className="n nw">{g.scored}–{g.allowed}</td></tr>
            ))}</tbody>
          </table>
        </div>
      </details>
    </>
  )
}

// ----------------------------------------------------------------- players
export function PlayerCard({ p }) {
  const m = p.stats
  return (
    <article className="player">
      <div className="player-top">
        <Headshot id={p.id} name={p.name} />
        <div><span className="meta">#{p.jersey} · {p.position}</span><strong>{p.name}</strong></div>
      </div>
      {m ? (
        <dl className="player-stats">
          {[['PTS', m.PTS], ['REB', m.REB], ['AST', m.AST], ['MIN', m.MIN]].map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v.toFixed(1)}</dd></div>)}
          <div><dt>GP</dt><dd>{m.GP.toFixed(0)}</dd></div>
        </dl>
      ) : <p className="player-none">No season stats with this team</p>}
    </article>
  )
}

export function RosterProblems({ data }) {
  if (data.rosterUnavailable) return <p className="callout">NBA Stats couldn’t load this roster. Try again later.</p>
  if (data.noRoster) return <p className="small">NBA Stats has no roster available for this team.</p>
  if (data.averagesUnavailable) return <p className="callout">Player averages are temporarily unavailable.</p>
  return null
}
