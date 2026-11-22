// Adapted from React Bits "Spotlight Card" (https://github.com/DavidHDev/react-bits): a soft highlight that
// follows the pointer across the card. With reduced motion the highlight stays fixed in the top corner.
import { useRef } from 'react'
import { useReducedMotion } from '../motion'

export default function SpotlightCard({ children, className = '', ...rest }) {
  const ref = useRef(null)
  const reduced = useReducedMotion()
  const move = (e) => {
    const r = ref.current.getBoundingClientRect()
    ref.current.style.setProperty('--sx', `${e.clientX - r.left}px`)
    ref.current.style.setProperty('--sy', `${e.clientY - r.top}px`)
  }
  return (
    <div ref={ref} className={`spotlight ${className}`} onPointerMove={reduced ? undefined : move} {...rest}>
      {children}
    </div>
  )
}
