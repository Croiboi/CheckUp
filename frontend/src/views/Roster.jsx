import { navigate } from '../router'
import { useApi } from '../api'
import { useApp } from '../context'
import TeamPicker from '../components/TeamPicker'
import { Logo, Problem, Skeleton } from '../components/bits'
import { PlayerCard, RosterProblems, TeamStats } from './shared'

export default function Roster({ abbr }) {
  const { teams, meta } = useApp()
  const team = teams.find((t) => t.abbr === abbr)
  const { data, error, retry } = useApi(`/api/team/${abbr}/roster`)
  return (
    <>
      <header className="page-head">
        <div className="aside-team"><Logo abbr={abbr} size={64} /><h1>{team.name}</h1></div>
        <div className="head-tools"><TeamPicker label="Find a team" value={abbr} onSelect={(a) => navigate(`/teams/${a}`)} /></div>
      </header>
      <p className="small">{meta.season} regular season · Results through {meta.resultsThrough}</p>
      <TeamStats abbr={abbr} />
      <h2 className="section-title">Roster</h2>
      <p className="small">Regular-season averages per game with this team. GP is games played.</p>
      {error ? <Problem error={error} retry={retry} what="the roster" /> : !data ? <Skeleton rows={3} height={150} /> : (
        <>
          <RosterProblems data={data} />
          <div className="roster-grid" style={{ '--accent': team.color }}>{data.players.map((p) => <PlayerCard key={p.id} p={p} />)}</div>
        </>
      )}
    </>
  )
}
