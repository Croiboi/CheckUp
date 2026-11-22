import { useState } from 'react'
import { useApi } from '../api'
import { useApp } from '../context'
import { Problem, Skeleton } from '../components/bits'
import { request } from '../api'

const VERDICT = { 'clearly better': 'clearly better', 'clearly worse': 'clearly worse', 'no clear difference': 'no clear difference' }

function Bars({ title, rows, chosen, fmt }) {
  const values = rows.map((r) => r.value)
  const lo = Math.min(...values), span = Math.max(...values) - lo || 1
  return (
    <>
      <h4>{title}</h4>
      {rows.map((r) => (
        <div key={r.key} className={`mini ${String(r.key) === String(chosen) ? 'sel' : ''}`}>
          <span>{fmt(r.key)}</span>
          <span className="track"><span style={{ width: `${25 + 75 * (1 - (r.value - lo) / span)}%` }} /></span>
          <span>{r.value.toFixed(4)}</span>
        </div>
      ))}
    </>
  )
}

function Outside() {
  const { teams, form } = useApp()
  const [a, setA] = useState('NYK'), [b, setB] = useState('BOS'), [outside, setOutside] = useState('')
  const [model, setModel] = useState(null)
  const load = async (x, y) => {
    if (x === y) return setModel(null)
    try { setModel(await request(`/api/matchup?a=${x}&b=${y}&form=${form ? 1 : 0}`)) } catch { setModel(null) }
  }
  const p = model ? model.a.pct / 100 : null
  const q = Number(outside) / 100
  const valid = p != null && q > 0.005 && q < 0.995
  const row = (label, m, o) => <tr><td>{label}</td><td className="n">{m.toFixed(3)}</td><td className="n">{o.toFixed(3)}</td></tr>
  return (
    <>
      <div className="outside">
        {[['Team 1', a, (v) => { setA(v); load(v, b) }], ['Team 2', b, (v) => { setB(v); load(a, v) }]].map(([label, val, set]) => (
          <label key={label}>{label}
            <select value={val} onChange={(e) => set(e.target.value)}>
              {teams.map((t) => <option key={t.abbr} value={t.abbr}>{t.name}</option>)}
            </select>
          </label>
        ))}
        <label>Outside win probability for Team 1 (%)
          <input type="number" min="1" max="99" step="0.5" placeholder="e.g. 59" value={outside}
            onFocus={() => model || load(a, b)} onChange={(e) => { setOutside(e.target.value); if (!model) load(a, b) }} />
        </label>
      </div>
      {valid && (
        <>
          <div className="scroll-x"><table className="t"><thead><tr><th>If this happens</th><th className="n">Model</th><th className="n">Outside</th></tr></thead>
            <tbody>{row(`${model.a.name} win`, (1 - p) ** 2, (1 - q) ** 2)}{row(`${model.a.name} lose`, p ** 2, q ** 2)}</tbody></table></div>
          <p className="small">Model is <b>{((p - q) * 100 >= 0 ? '+' : '') + ((p - q) * 100).toFixed(1)} pts</b> from the outside estimate (lower squared miss is better). One game cannot show which is better calibrated. Outside numbers may reflect injuries and betting-market information this model does not use. Compare Brier scores over many games, as the table above does, and don’t tune settings to match one estimate.</p>
        </>
      )}
    </>
  )
}

export default function Performance() {
  const { data, error, retry } = useApi('/api/performance')
  if (error) return <><h1>Model performance</h1><Problem error={error} retry={retry} what="model performance" /></>
  if (!data) return <><h1>Model performance</h1><Skeleton rows={3} height={140} /></>
  const s = data.selected, sp = data.splits
  const span = data.seasons.length ? `${data.seasons[0]}–${data.seasons.at(-1) + 1}` : ''
  return (
    <>
      <header className="page-head"><div><h1>Model performance</h1>
        <p className="lede">{data.gameCount.toLocaleString()} games · {data.seasons.length} season(s)</p></div></header>
      <div className="chips">
        <span className="chip">Home bonus <b>+{s.home_bonus} Elo</b>{data.bonusAtEdge && <small> (top of range tried)</small>}</span>
        <span className="chip">Carryover <b>{s.carryover.toFixed(2)}</b></span>
        <span className="chip">Form weight <b>{s.form_weight}</b></span>
      </div>
      {data.warning && <p className="callout">{data.warning}</p>}
      <div className="scroll-x">
        <table className="t">
          <thead><tr><th>Model</th><th className="n">Brier</th><th className="n">Test games</th><th className="n">Change vs Elo</th></tr></thead>
          <tbody>
            {data.models.map((m) => (
              <tr key={m.key} className={m.best ? 'best' : ''}>
                <td>{m.label}</td><td className="n">{m.brier.toFixed(4)}</td><td className="n">{m.games.toLocaleString()}</td>
                <td className="n">{m.key === 'elo' ? <small>baseline</small> : m.diff_se == null ? '—'
                  : <>{(m.diff_vs_elo >= 0 ? '+' : '') + m.diff_vs_elo.toFixed(4)}<small>± {m.diff_se.toFixed(4)} · {VERDICT[m.verdict]}</small></>}</td>
              </tr>
            ))}
            <tr className="off"><td>Coin flip (always 50%)</td><td className="n">{data.coinFlip.toFixed(4)}</td><td className="n">—</td><td /></tr>
          </tbody>
        </table>
      </div>
      <p className="small"><b>Brier score</b> is the average squared miss between the predicted win probability and what happened (1 for a win, 0 for a loss). 0 is perfect, always saying 50% scores 0.25, and lower is better. Test games are newer than everything used to choose settings.</p>
      <div className="scroll-x">
        <table className="t">
          <thead><tr><th>Period · {span}</th><th className="n">Games</th><th className="n">Dates</th></tr></thead>
          <tbody>{[['Warm-up (build ratings)', 'warmup'], ['Validation (choose settings)', 'validation'], ['Test (report results)', 'test']].map(([name, k]) => (
            <tr key={k}><td>{name}</td><td className="n">{sp[k].games.toLocaleString()}</td><td className="n nw">{sp[k].start} → {sp[k].end}</td></tr>
          ))}</tbody>
        </table>
      </div>
      <details>
        <summary>How the settings were chosen</summary>
        <p className="small">Validation Brier for each candidate (longer bar = better). Each bonus shows its best carryover, and each carryover its best bonus. The test period was not used here.</p>
        <Bars title="Home bonus (Elo points)" rows={data.search.bonus} chosen={s.home_bonus} fmt={(k) => k} />
        <Bars title="Carryover into a new season" rows={data.search.carryover} chosen={s.carryover} fmt={(k) => Number(k).toFixed(2)} />
        <Bars title="Recent-form weight" rows={data.search.formWeight} chosen={s.form_weight} fmt={(k) => k} />
        <p className="small">With no form adjustment the validation score is {data.search.noForm.toFixed(4)}.</p>
      </details>
      <details><summary>Compare with an outside estimate</summary><Outside /></details>
    </>
  )
}
