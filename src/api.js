import { useEffect, useState } from 'react'

export async function request(path, options) {
  const response = await fetch(path, options)
  if (!response.ok) {
    let message = response.statusText
    try { message = (await response.json()).error || message } catch { /* not JSON */ }
    throw new Error(message)
  }
  return response.json()
}

// Returns data only for the path that was asked for, so a slow response can't show the wrong team.
export function useApi(path) {
  const [state, setState] = useState({ path: null })
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!path) return
    const controller = new AbortController()
    request(path, { signal: controller.signal })
      .then((data) => setState({ path, data }))
      .catch((error) => { if (error.name !== 'AbortError') setState({ path, error: error.message }) })
    return () => controller.abort()
  }, [path, attempt])
  const ready = state.path === path
  return {
    data: ready ? state.data ?? null : null,
    error: ready ? state.error ?? null : null,
    loading: !ready,
    retry: () => setAttempt((n) => n + 1),
  }
}
