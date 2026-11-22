// Tiny History-API router. pushState gives Chrome's Back/Forward buttons real entries to move between.
import { useEffect, useSyncExternalStore } from 'react'

const subs = new Set()
const read = () => location.pathname + location.search
let current = read()
let key = history.state?.k ?? Date.now()
let pending // undefined = leave scroll alone, number = scroll there after the next render
const positions = new Map()

history.scrollRestoration = 'manual'
if (history.state?.k == null) history.replaceState({ k: key }, '')

const emit = () => { current = read(); subs.forEach((f) => f()) }
window.addEventListener('scroll', () => positions.set(key, window.scrollY), { passive: true })
window.addEventListener('popstate', (e) => {
  key = e.state?.k ?? key
  pending = location.hash ? undefined : positions.get(key) ?? 0
  emit()
})

export function navigate(to, { replace = false } = {}) {
  if (to === current) return
  if (replace) history.replaceState({ k: key }, '', to)
  else { key = Date.now() + Math.random(); history.pushState({ k: key }, '', to); pending = 0 }
  emit()
}

export const useLocation = () =>
  useSyncExternalStore((cb) => { subs.add(cb); return () => subs.delete(cb) }, () => current)

// Scroll to the top on a new page, or back to where you were on Back/Forward.
export function useScrollRestore(pathname) {
  useEffect(() => {
    if (pending === undefined) return
    const y = pending
    pending = undefined
    let raf, tries = 0
    const go = () => {
      window.scrollTo(0, y)
      if (y > 0 && Math.abs(window.scrollY - y) > 2 && tries++ < 40) raf = requestAnimationFrame(go)
    }
    go()
    return () => cancelAnimationFrame(raf)
  }, [pathname])
}

export function Link({ to, children, onClick, ...props }) {
  const handle = (e) => {
    onClick?.(e)
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    e.preventDefault()
    navigate(to)
  }
  return <a href={to} onClick={handle} {...props}>{children}</a>
}
