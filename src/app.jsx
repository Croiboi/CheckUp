import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useScrollRestore } from './router'
import { request } from './api'
import { AppContext } from './context'
import Home from './views/Home'
import TeamSchedule from './views/TeamSchedule'
import Compare from './views/Compare'
import Roster from './views/Roster'
import Performance from './views/Performance'
import DataUpdates from './views/DataUpdates'

export { useApp } from './context'

const DEFAULT_TEAM = 'NYK'

function parseRoute(loc, abbrs) {
  const [path, search = ''] = loc.split('?')
  const q = new URLSearchParams(search)
  const seg = path.split('/').filter(Boolean)
  const team = (s) => (s || DEFAULT_TEAM).toUpperCase()
  if (!seg.length) return { name: 'home' }
  if (seg[0] === 'matchups') return abbrs.has(team(seg[1])) ? { name: 'team', abbr: team(seg[1]) } : { name: 'missing' }
  if (seg[0] === 'teams') return abbrs.has(team(seg[1])) ? { name: 'roster', abbr: team(seg[1]) } : { name: 'missing' }
  if (seg[0] === 'compare') {
    const a = (q.get('a') || 'NYK').toUpperCase(), b = (q.get('b') || 'BOS').toUpperCase()
    if (!abbrs.has(a) || !abbrs.has(b)) return { name: 'missing' }
    return { name: 'compare', a, b: a === b ? [...abbrs].find((x) => x !== a) : b, game: q.get('game'), venue: q.get('venue') }
  }
  if (seg[0] === 'performance') return { name: 'performance' }
  if (seg[0] === 'data') return { name: 'data' }
  return { name: 'missing' }
}

const TITLES = { home: 'Home', team: 'Matchups', compare: 'Compare teams', roster: 'Team profiles', performance: 'Model performance', data: 'Data & updates', missing: 'Page not found' }

function Menu({ lastTeam, current }) {
  const [open, setOpen] = useState(false)
  const root = useRef(null), button = useRef(null)
  const items = [
    ['Home', '/', 'home'], ['Matchups', `/matchups/${lastTeam}`, 'matchups'], ['Team Profiles', `/teams/${lastTeam}`, 'roster'],
    ['Model Performance', '/performance', 'performance'], ['Data & Updates', '/data', 'data'],
  ]
  useEffect(() => {
    if (!open) return
    const outside = (e) => { if (!root.current?.contains(e.target)) setOpen(false) }
    const key = (e) => { if (e.key === 'Escape') { setOpen(false); button.current?.focus() } }
    document.addEventListener('pointerdown', outside); document.addEventListener('keydown', key)
    root.current.querySelector('a')?.focus()
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('keydown', key) }
  }, [open])
  return (
    <div className="menu" ref={root}>
      <button ref={button} className="btn menu-btn" aria-expanded={open} aria-controls="site-menu" onClick={() => setOpen(!open)}>
        <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 6h14M3 10h14M3 14h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
        Menu
      </button>
      {open && (
        <nav id="site-menu" aria-label="Main">
          <ul>{items.map(([label, to, key]) => (
            <li key={key}><Link to={to} aria-current={current === key ? 'page' : undefined} onClick={() => setOpen(false)}>{label}</Link></li>
          ))}</ul>
        </nav>
      )}
    </div>
  )
}

export default function App() {
  const loc = useLocation()
  const [meta, setMeta] = useState(null)
  const [metaError, setMetaError] = useState(null)
  const [form, setFormState] = useState(() => sessionStorage.getItem('checkup:form') === '1')
  const [lastTeam, setLastTeam] = useState(DEFAULT_TEAM)

  const loadMeta = useCallback(() => request('/api/meta').then((m) => { setMeta(m); setMetaError(null) }).catch((e) => setMetaError(e.message)), [])
  useEffect(() => { loadMeta() }, [loadMeta])
  const setForm = useCallback((v) => { setFormState(v); sessionStorage.setItem('checkup:form', v ? '1' : '0') }, [])

  const abbrs = useMemo(() => new Set(meta?.teams.map((t) => t.abbr) ?? []), [meta])
  const route = meta ? parseRoute(loc, abbrs) : { name: 'loading' }
  useScrollRestore(loc.split('?')[0])
  useEffect(() => { if (route.abbr) setLastTeam(route.abbr) }, [route.abbr])
  useEffect(() => { document.title = `${TITLES[route.name] ?? 'CheckUp'} · CheckUp` }, [route.name])

  const ctx = useMemo(() => meta && ({ meta, teams: meta.teams, form, setForm }), [meta, form, setForm])
  const menuKey = { home: 'home', team: 'matchups', compare: 'matchups', roster: 'roster', performance: 'performance', data: 'data' }[route.name]

  let view = null
  if (ctx) {
    switch (route.name) {
      case 'home': view = <Home />; break
      case 'team': view = <TeamSchedule abbr={route.abbr} />; break
      case 'compare': view = <Compare {...route} lastTeam={lastTeam} />; break
      case 'roster': view = <Roster abbr={route.abbr} />; break
      case 'performance': view = <Performance />; break
      case 'data': view = <DataUpdates reloadMeta={loadMeta} />; break
      default: view = <div className="problem"><b>That page doesn’t exist.</b><p>Check the address, or head back to the homepage.</p><Link to="/" className="btn primary">Go to Home</Link></div>
    }
  }

  return (
    <AppContext.Provider value={ctx}>
      <a className="skip" href="#main">Skip to content</a>
      <header className="site-head">
        <Link to="/" className="brand" aria-label="CheckUp, go to Home"><img src="/checkup-wordmark.png" alt="CheckUp" width="540" height="160" /></Link>
        {meta && (
          <div className="status" aria-label="Data status">
            <span className="pill">Results through {meta.resultsThrough}</span>
            <span className={`pill ${meta.schedule.state}`}><i />{meta.schedule.label}</span>
          </div>
        )}
        <Menu lastTeam={lastTeam} current={menuKey} />
      </header>
      <main id="main" className={`page page-${route.name}`} tabIndex={-1}>
        {metaError && (
          <div className="problem" role="alert"><b>Can’t reach the CheckUp API.</b>
            <p>{metaError}. Start it with <code>python api.py</code> in the project folder, then reload.</p>
            <button className="btn primary" onClick={loadMeta}>Try again</button></div>
        )}
        {!meta && !metaError && <p className="small" role="status">Loading CheckUp…</p>}
        {view}
      </main>
    </AppContext.Provider>
  )
}
