import { useRef, useState } from 'react'
import { Link, navigate } from '../router'
import { useApi } from '../api'
import { useApp } from '../context'
import { useEntrance } from '../motion'
import TeamPicker from '../components/TeamPicker'
import { FormToggle, Logo, Problem, Skeleton, Tabs, pct } from '../components/bits'
import { Headshot } from '../components/bits'
import { MatchupBody, RosterProblems, TeamStats, useMatchup } from './shared'

export function MatchupsHeader({ title, children, abbr, mode }) {
  return (
    <header className="page-head">
      <div>
        <h1>{title}</h1>
        <Tabs items={[
          { to: `/matchups/${abbr}`, label: 'Team schedule', current: mode === 'team' },
          { to: '/compare', label: 'Compare teams', current: mode === 'compare' },
        ]} />
      </div>
      {children}
    </header>
  )
}

function GameRow({ team, game }) {
  const [open, setOpen] = useState(false)
  const opp = game.opponent
  const odds = game.pct
  return (
    <li className={`game ${open ? 'open' : ''}`}>
      <button className="game-main" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="game-logos"><Logo abbr={team} size={48} /><Logo abbr={opp.abbr} size={48} /></span>
        <span className="game-info">
          <b>{opp.name}</b>
          <small>{game.venue} · {game.tipoff.day} · {game.tipoff.time}</small>
        </span>
        <span className={`odds ${odds >= 50 ? 'fav' : ''}`}>{pct(odds)}</span>
        <span className="chev" aria-hidden="true" />
        <span className="game-bar" style={{ '--p': `${odds}%` }} />
      </button>
      {open && <Detail team={team} game={game} />}
    </li>
  )
}

function Detail({ team, game }) {
  const { data, error, retry } = useMatchup(team, game.opponent.abbr, game.id)
  return (
    <div className="game-detail">
      {error ? <Problem error={error} retry={retry} what="game details" />
        : !data ? <Skeleton rows={1} height={220} /> : <MatchupBody data={data} />}
    </div>
  )
}

function TopScorers({ abbr }) {
  const { data, error, retry } = useApi(`/api/team/${abbr}/roster`)
  return (
    <section className="aside-block">
      <h2>Top scorers</h2>
      <p className="small">Ranked by season points per game with this team.</p>
      {error ? <Problem error={error} retry={retry} what="scorers" />
        : !data ? <Skeleton rows={3} height={84} /> : (
          <>
            <RosterProblems data={data} />
            {!data.rosterUnavailable && data.players.length > 0 && data.topScorers.length === 0 && !data.averagesUnavailable &&
              <p className="small">No scoring averages are available for the current roster yet.</p>}
            <ol className="scorers">
              {data.topScorers.map((p, i) => (
                <li key={p.id}>
                  <span className="rank">{i + 1}</span>
                  <Headshot id={p.id} name={p.name} />
                  <div><b>{p.name}</b><small>#{p.jersey} · {p.position}</small></div>
                  <div className="ppg"><b>{p.stats.PTS.toFixed(1)}</b><small>PTS</small></div>
                </li>
              ))}
            </ol>
          </>
        )}
      <Link to={`/teams/${abbr}`} className="btn full">View full roster</Link>
    </section>
  )
}

export default function TeamSchedule({ abbr }) {
  const { form, meta, teams } = useApp()
  const team = teams.find((t) => t.abbr === abbr)
  const { data, error, retry } = useApi(`/api/team/${abbr}/schedule?form=${form ? 1 : 0}`)
  const head = useRef(null)
  useEntrance(head, '.rise', [abbr])

  return (
    <div ref={head}>
      <MatchupsHeader title={team.name} abbr={abbr} mode="team">
        <div className="head-tools">
          <TeamPicker label="Find a team" value={abbr} onSelect={(a) => navigate(`/matchups/${a}`)} />
          <FormToggle />
        </div>
      </MatchupsHeader>
      <div className="split">
        <section aria-labelledby="pred-title">
          <h2 id="pred-title" className="section-title">Next {meta.windowDays} days</h2>
          <p className="small">Based on current ratings through {data?.through ?? meta.resultsThrough} · All times Eastern</p>
          {error ? <Problem error={error} retry={retry} what="predictions" />
            : !data ? <Skeleton rows={4} height={104} />
            : data.games.length === 0 ? <p className="callout">{data.reason}</p>
            : <ul className="games">{data.games.map((g) => <GameRow key={g.id + form} team={abbr} game={g} />)}</ul>}
        </section>
        <aside className="aside" aria-label={`${team.name} stats`}>
          <section className="aside-block">
            <div className="aside-team"><Logo abbr={abbr} size={56} /><h2>{team.name}</h2></div>
            <p className="small">{meta.season} regular season · Results through {meta.resultsThrough}</p>
            <TeamStats abbr={abbr} />
          </section>
          <TopScorers abbr={abbr} />
        </aside>
      </div>
    </div>
  )
}
