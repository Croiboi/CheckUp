import { useRef } from 'react'
import { Link, navigate } from '../router'
import { useApi } from '../api'
import { useApp } from '../context'
import { useEntrance, useScrollReveal, useSmoothScroll } from '../motion'
import Squares from '../components/Squares'
import SpotlightCard from '../components/SpotlightCard'
import TeamPicker from '../components/TeamPicker'
import { Logo, OddsBar, Problem, Skeleton, pct } from '../components/bits'

const matchupLink = (g) => `/compare?a=${g.away.abbr}&b=${g.home.abbr}&game=${g.id}`

function Featured({ game }) {
  const team = (t, venue) => (
    <div className={`f-team ${t.pct >= 50 ? 'fav' : ''}`}>
      <Logo abbr={t.abbr} size={56} />
      <div><small>{game.neutral ? 'Neutral court' : venue}</small><strong>{t.name}</strong></div>
      <span className="odds">{pct(t.pct)}</span>
    </div>
  )
  return (
    <SpotlightCard className="featured featured-in">
      <header>
        <h2>Featured matchup</h2>
        <span>{game.tipoff.day} · {game.tipoff.time}</span>
      </header>
      {team(game.away, 'Away')}
      {team(game.home, 'Home')}
      <OddsBar aPct={game.away.pct} bPct={game.home.pct}
        label={`${game.away.name} ${pct(game.away.pct)}, ${game.home.name} ${pct(game.home.pct)}`} />
      <footer>
        <p>Closest call on the slate. Model-estimated win probabilities.</p>
        <Link to={matchupLink(game)} className="btn ghost">View matchup</Link>
      </footer>
    </SpotlightCard>
  )
}

function SlateCard({ game }) {
  const row = (t) => (
    <div className={`s-team ${t.pct >= 50 ? 'fav' : ''}`}>
      <Logo abbr={t.abbr} size={36} /><span>{t.name}</span><b>{pct(t.pct)}</b>
    </div>
  )
  return (
    <Link to={matchupLink(game)} className="slate-card" aria-label={`View matchup: ${game.away.name} at ${game.home.name}`}>
      <span className="s-time">{game.tipoff.time}{game.neutral ? ' · Neutral court' : ''}</span>
      {row(game.away)}{row(game.home)}
      <span className="s-go">View matchup</span>
    </Link>
  )
}

export default function Home() {
  const { form } = useApp()
  const { data, error, retry } = useApi(`/api/slate?form=${form ? 1 : 0}`)
  const hero = useRef(null)
  const grid = useRef(null)
  useSmoothScroll()
  useEntrance(hero, '.hero-in')
  const featured = data?.games?.find((g) => g.id === data.featuredId)
  const rest = data?.games?.filter((g) => g.id !== data.featuredId) ?? []
  useEntrance(hero, '.featured-in', [!!featured])
  useScrollReveal(grid, '.slate-card', [rest.length])

  return (
    <>
      <section className="hero" ref={hero}>
        <Squares />
        <div className="hero-grid">
          <div className="hero-copy">
            <h1 className="hero-in">Before the ball<br />goes up.</h1>
            <p className="lede hero-in">See who’s favored in the next NBA matchup and explore two weeks of win probabilities for any team.</p>
            <div className="hero-in hero-find">
              <TeamPicker label="Find your team" value={null} onSelect={(abbr) => navigate(`/matchups/${abbr}`)} />
            </div>
            <div className="hero-actions hero-in">
              <Link to="/matchups/NYK" className="btn primary">Explore matchups</Link>
              <Link to="/performance" className="btn">View model performance</Link>
              <a href="#slate" className="jump">Jump to the slate</a>
            </div>
          </div>
          {error ? <Problem error={error} retry={retry} what="the featured matchup" />
            : !data ? <Skeleton rows={1} height={380} />
            : featured ? <Featured game={featured} />
            : <div className="featured empty"><h2>Next matchup</h2><p>{data.reason}</p></div>}
        </div>
      </section>

      <section id="slate" className="slate">
        {data?.games?.length > 0 && (
          <header className="slate-head">
            <h2>{data.title}</h2>
            <span>{data.date} · {data.games.length} {data.games.length === 1 ? 'game' : 'games'} · Eastern time</span>
          </header>
        )}
        {!data && !error && <Skeleton rows={3} height={150} />}
        <div className="slate-grid" ref={grid}>{rest.map((g) => <SlateCard key={g.id} game={g} />)}</div>
      </section>
    </>
  )
}
