import { useState } from 'react'
import { request, useApi } from '../api'
import { Problem, Skeleton } from '../components/bits'

export default function DataUpdates({ reloadMeta }) {
  const { data, error, retry } = useApi('/api/data')
  const [busy, setBusy] = useState(false)
  const [messages, setMessages] = useState([])
  const [failure, setFailure] = useState(null)

  const refresh = async () => {
    setBusy(true); setFailure(null)
    try {
      setMessages((await request('/api/refresh', { method: 'POST' })).messages)
      retry(); reloadMeta()
    } catch (e) { setFailure(e.message) } finally { setBusy(false) }
  }
  return (
    <>
      <header className="page-head"><h1>Data &amp; updates</h1></header>
      {error ? <Problem error={error} retry={retry} what="data status" /> : !data ? <Skeleton rows={1} height={90} /> : (
        <>
          <p className="lede">Results through <b>{data.through}</b> · {data.historyFiles} past season file(s) cached.</p>
          {data.scheduleStale && data.scheduleFetched && <p className="callout">The NBA schedule request failed, so this is the last saved copy ({data.scheduleError}).</p>}
          {data.scheduleStale && !data.scheduleFetched && <p className="callout">No schedule available ({data.scheduleError}). You can still simulate a matchup.</p>}
        </>
      )}
      {messages.map((m, i) => <p key={i} className={m.kind === 'success' ? 'callout good' : 'callout'} role="status">{m.text}</p>)}
      {failure && <p className="callout" role="alert">Refresh failed: {failure}.</p>}
      <button className="btn primary" onClick={refresh} disabled={busy}>{busy ? 'Contacting NBA.com…' : 'Refresh data'}</button>
    </>
  )
}
