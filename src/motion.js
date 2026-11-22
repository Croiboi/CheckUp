// All motion lives here so the reduced-motion rule is applied in one place.
import { useLayoutEffect, useSyncExternalStore } from 'react'
import { gsap } from 'gsap'
import Lenis from 'lenis'
import 'lenis/dist/lenis.css'

const QUERY = '(prefers-reduced-motion: reduce)'
export const useReducedMotion = () =>
  useSyncExternalStore(
    (cb) => { const m = matchMedia(QUERY); m.addEventListener('change', cb); return () => m.removeEventListener('change', cb) },
    () => matchMedia(QUERY).matches,
    () => false,
  )

// Homepage entrance: headline, copy and controls rise in; text only. Odds are never animated.
export function useEntrance(ref, selector, deps = []) {
  const reduced = useReducedMotion()
  useLayoutEffect(() => {
    const root = ref.current
    if (reduced || !root) return
    const ctx = gsap.context(() => {
      const items = root.querySelectorAll(selector)
      if (items.length) gsap.from(items, { y: 22, opacity: 0, duration: 0.6, stagger: 0.08, ease: 'power3.out', clearProps: 'transform,opacity' })
    }, root)
    return () => ctx.revert()
  }, [reduced, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps
}

// Staggered reveal as cards scroll into view. Cards start at 55% opacity, never invisible,
// so the odds are legible from the first frame.
export function useScrollReveal(ref, selector, deps = []) {
  const reduced = useReducedMotion()
  useLayoutEffect(() => {
    const root = ref.current
    if (reduced || !root || !('IntersectionObserver' in window)) return
    const els = [...root.querySelectorAll(selector)]
    if (!els.length) return
    gsap.set(els, { opacity: 0.55, y: 18 })
    let queue = [], timer
    const show = (targets) => gsap.to(targets, { opacity: 1, y: 0, duration: 0.55, stagger: 0.07, ease: 'power2.out', clearProps: 'opacity,transform' })
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { queue.push(e.target); io.unobserve(e.target) } })
      clearTimeout(timer)
      timer = setTimeout(() => { show(queue); queue = [] }, 30)
    }, { threshold: 0.12 })
    els.forEach((el) => io.observe(el))
    const safety = setTimeout(() => show(els), 3000) // never leave a card dimmed
    return () => {
      io.disconnect(); clearTimeout(timer); clearTimeout(safety)
      gsap.killTweensOf(els); gsap.set(els, { clearProps: 'opacity,transform' })
    }
  }, [reduced, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps
}

// Smooth scrolling for the homepage only. Mounted by the Home view and destroyed when you leave it,
// so dashboard pages keep native scrolling. Lenis doesn't touch the keyboard; anchors are handled by `anchors`.
export function useSmoothScroll() {
  const reduced = useReducedMotion()
  useLayoutEffect(() => {
    if (reduced) return
    const lenis = new Lenis({ lerp: 0.1, anchors: true })
    let raf
    const tick = (time) => { lenis.raf(time); raf = requestAnimationFrame(tick) }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); lenis.destroy() }
  }, [reduced])
}
