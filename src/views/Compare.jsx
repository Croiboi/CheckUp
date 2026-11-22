import { navigate } from '../router'
import { useApp } from '../context'
import TeamPicker from '../components/TeamPicker'
import { FormToggle, Problem, Skeleton } from '../components/bits'
import { MatchupBody, useMatchup } from './shared'
import { MatchupsHeader } from './TeamSchedule'

export default function Compare({ a, b, game, venue, lastTeam }) {
  const { teams } = useApp()
  const nameOf = (abbr) => teams.find((t) => t.abbr === abbr).name
  const { data, error, retry } = useMatchup(a, b, game, venue)
  const go = (next) => {
    const q = new URLSearchParams({ a, b, ...next })
    if (next.a || next.b) q.delete('game')
    if (next.a || next.b || next.swap) q.delete('venue')
    navigate(`/compare?${q}`)
  }
  const swap = () => navigate(`/compare?${new URLSearchParams({ a: b, b: a, ...(game ? { game } : {}) })}`)
  const venues = [['a_home', `${nameOf(a)} at home`], ['b_home', `${nameOf(b)} at home`], ['neutral', 'Neutral court']]

  return (
    <>
      <MatchupsHeader title="Compare teams" abbr={lastTeam} mode="compare">
        <div className="head-tools"><FormToggle /></div>
      </MatchupsHeader>
      <div className="compare-pickers">
        <TeamPicker label="Team 1" value={a} exclude={b} onSelect={(abbr) => go({ a: abbr })} />
        <button className="btn swap" onClick={swap} aria-label="Swap teams">⇄ Swap teams</button>
        <TeamPicker label="Team 2" value={b} exclude={a} onSelect={(abbr) => go({ b: abbr })} />
      </div>
      {error ? <Problem error={error} retry={retry} what="this matchup" /> : !data ? <Skeleton rows={1} height={320} /> : (
        <>
          {data.game ? (
            <div className="strip">
              <span className="badge ok">Next scheduled game</span>
              <span className="chip"><b>{data.game.day}</b></span>
              <span className="chip">Tipoff <b>{data.game.time}</b></span>
              <span className="chip">Home: <b>{data.game.homeName}</b></span>
              {data.game.early && <span className="chip muted">Early projection · Based on current ratings</span>}
            </div>
          ) : (
            <div className="strip">
              <span className="badge hypo">Hypothetical matchup</span>
              <span className="chip muted">{data.reason} Choose a venue to simulate one.</span>
              <div className="venues" role="radiogroup" aria-label="Venue">
                {venues.map(([v, label]) => (
                  <button key={v} role="radio" aria-checked={data.venue === v} className="seg"
                    onClick={() => go({ venue: v })}>{label}</button>
                ))}
              </div>
            </div>
          )}
          <MatchupBody data={data} />
        </>
      )}
    </>
  )
}
