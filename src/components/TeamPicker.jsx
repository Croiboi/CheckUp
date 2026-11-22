import { useEffect, useId, useMemo, useState } from 'react'
import { useApp } from '../context'
import { Logo } from './bits'

// Accessible combobox: type to filter by name or abbreviation, arrow keys + Enter to choose, Esc to close.
export default function TeamPicker({ label, value, onSelect, exclude, placeholder = 'Search team name or abbreviation' }) {
  const { teams } = useApp()
  const id = useId()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const selected = teams.find((t) => t.abbr === value)

  const options = useMemo(() => {
    const q = query.trim().toLowerCase()
    return teams.filter((t) => t.abbr !== exclude && (!q || t.name.toLowerCase().includes(q) || t.abbr.toLowerCase().startsWith(q)))
  }, [teams, query, exclude])

  useEffect(() => { setActive(0) }, [query])
  useEffect(() => {
    if (open) document.getElementById(`${id}-${active}`)?.scrollIntoView({ block: 'nearest' })
  }, [active, open, id])

  const choose = (team) => { setOpen(false); setQuery(''); onSelect(team.abbr) }
  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive((i) => Math.min(i + 1, options.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter' && open && options[active]) { e.preventDefault(); choose(options[active]) }
    else if (e.key === 'Escape') { setOpen(false); setQuery('') }
  }

  return (
    <div className="picker">
      <label htmlFor={id}>{label}</label>
      <div className="picker-field">
        {selected && !open && <Logo abbr={selected.abbr} size={28} />}
        <input
          id={id} role="combobox" aria-expanded={open} aria-controls={`${id}-list`} aria-autocomplete="list"
          aria-activedescendant={open && options[active] ? `${id}-${active}` : undefined}
          autoComplete="off" spellCheck="false" placeholder={placeholder}
          className={selected && !open ? 'has-logo' : ''}
          value={open ? query : selected ? selected.name : ''}
          onFocus={(e) => { setOpen(true); setQuery(''); e.target.select?.() }}
          onBlur={() => { setOpen(false); setQuery('') }}
          onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
          onKeyDown={onKeyDown}
        />
      </div>
      {open && (
        <ul id={`${id}-list`} role="listbox" aria-label={label} data-lenis-prevent onPointerDown={(e) => e.preventDefault()}>
          {options.length === 0 && <li className="picker-empty">No team matches “{query}”. Try a city or abbreviation.</li>}
          {options.map((team, i) => (
            <li key={team.abbr} id={`${id}-${i}`} role="option" aria-selected={team.abbr === value}
              className={i === active ? 'on' : ''} onPointerEnter={() => setActive(i)} onClick={() => choose(team)}>
              <Logo abbr={team.abbr} size={28} /><span>{team.name}</span><b>{team.abbr}</b>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
