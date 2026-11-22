import { useState } from 'react'
import { Link } from '../router'
import { useApp } from '../context'

export const Logo = ({ abbr, size = 40 }) => (
  <img className="logo" src={`/api/logos/${abbr}.svg`} alt="" width={size} height={size} loading="lazy" />
)

export const pct = (n) => `${n.toFixed(1)}%`

// Two-segment probability bar; widths are the displayed percentages, which always total 100.
export function OddsBar({ aPct, bPct, aColor = '#9ED8FF', bColor = '#3D5677', label }) {
  return (
    <div className="bar" role="img" aria-label={label}>
      <span style={{ width: `${aPct}%`, background: aColor }} />
      <span style={{ width: `${bPct}%`, background: bColor }} />
    </div>
  )
}

export function FormToggle() {
  const { form, setForm } = useApp()
  return (
    <button type="button" role="switch" aria-checked={form} className="switch" onClick={() => setForm(!form)}>
      <span className="track"><i /></span>
      <span>Include last-5 form</span>
    </button>
  )
}

export function Skeleton({ rows = 3, height = 96 }) {
  return <div className="skeleton" aria-hidden="true">{Array.from({ length: rows }, (_, i) => <i key={i} style={{ height }} />)}</div>
}

export function Problem({ error, retry, what }) {
  return (
    <div className="problem" role="alert">
      <b>Couldn’t load {what}.</b>
      <p>{error}. Check that the Python API is running (<code>python api.py</code>), then try again.</p>
      {retry && <button className="btn" onClick={retry}>Try again</button>}
    </div>
  )
}

export function Headshot({ id, name, className = '' }) {
  const [failed, setFailed] = useState(false)
  const initials = name.split(' ').map((p) => p[0]).slice(0, 2).join('')
  return failed
    ? <span className={`headshot fallback ${className}`} aria-hidden="true">{initials}</span>
    : <img className={`headshot ${className}`} alt="" loading="lazy" onError={() => setFailed(true)}
        src={`https://cdn.nba.com/headshots/nba/latest/1040x760/${id}.png`} />
}

export function Tabs({ items }) {
  return (
    <nav className="tabs" aria-label="Matchup views">
      {items.map((t) => <Link key={t.to} to={t.to} aria-current={t.current ? 'page' : undefined}>{t.label}</Link>)}
    </nav>
  )
}
