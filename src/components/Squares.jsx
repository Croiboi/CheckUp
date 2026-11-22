// Adapted from React Bits "Squares" (https://github.com/DavidHDev/react-bits): a canvas grid that drifts
// diagonally and lights the square under the pointer. Restyled to CheckUp's ice-blue hairlines, with the
// drift switched off under prefers-reduced-motion. Check React Bits' license terms before commercial use.
import { useEffect, useRef } from 'react'
import { useReducedMotion } from '../motion'

export default function Squares({ size = 56, speed = 0.25, line = 'rgba(158,216,255,.10)', hover = 'rgba(158,216,255,.10)' }) {
  const canvas = useRef(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    const el = canvas.current
    const ctx = el.getContext('2d')
    let offset = 0, raf, hovered = null, w = 0, h = 0

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      w = el.offsetWidth; h = el.offsetHeight
      el.width = w * dpr; el.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      draw()
    }
    function draw() {
      ctx.clearRect(0, 0, w, h)
      const shift = offset % size
      ctx.lineWidth = 1
      for (let x = -size + shift; x < w + size; x += size) {
        for (let y = -size + shift; y < h + size; y += size) {
          if (hovered && Math.floor((hovered.x - shift + size) / size) === Math.floor((x + size) / size)
            && Math.floor((hovered.y - shift + size) / size) === Math.floor((y + size) / size)) {
            ctx.fillStyle = hover; ctx.fillRect(x, y, size, size)
          }
          ctx.strokeStyle = line; ctx.strokeRect(x + 0.5, y + 0.5, size, size)
        }
      }
    }
    const tick = () => { offset += speed; draw(); raf = requestAnimationFrame(tick) }
    const move = (e) => { const r = el.getBoundingClientRect(); hovered = { x: e.clientX - r.left, y: e.clientY - r.top }; if (reduced) draw() }
    const leave = () => { hovered = null; if (reduced) draw() }

    const ro = new ResizeObserver(resize)
    ro.observe(el)
    resize()
    if (!reduced) raf = requestAnimationFrame(tick)
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerleave', leave)
    return () => { cancelAnimationFrame(raf); ro.disconnect(); window.removeEventListener('pointermove', move); window.removeEventListener('pointerleave', leave) }
  }, [size, speed, line, hover, reduced])

  return <canvas ref={canvas} className="squares" aria-hidden="true" />
}
