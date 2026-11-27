import { useEffect, useState } from 'react'
import facts from './data/curiosidades.json'
export default function OvenWait() {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * facts.length))
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (paused) return
    const timer = setInterval(() => setIndex(i => (i + 1) % facts.length), 8000)
    return () => clearInterval(timer)
  }, [paused])
  const fact = facts[index]
  return <div className="fv-oven-wait">
    <svg viewBox="0 0 160 95" width="120" aria-hidden="true" focusable="false">
      <rect x="5" y="5" width="150" height="85" rx="10" fill="#a43e29" />
      <path d="M29 90V52a51 40 0 0 1 102 0v38Z" fill="#38271f" stroke="#d9ad85" strokeWidth="5" />
      <path className="fv-oven-flame" d="M58 76Q40 57 62 40Q60 59 72 55Q65 36 82 22Q77 45 93 55Q106 47 103 39Q123 64 101 76Z" fill="#ffad48" />
      <ellipse cx="80" cy="82" rx="36" ry="6" fill="#e9bb72" />
    </svg>
    <p role="status"><strong>¡Estamos calentando el horno!</strong><br />El asistente se está preparando.</p>
    <div className="fv-oven-fact"><strong>¿Sabías que…?</strong><p>{fact.texto}</p><a href={fact.url} target="_blank" rel="noopener noreferrer">Fuente: {fact.fuente}</a><button type="button" onClick={() => setPaused(p => !p)}>{paused ? 'Reanudar curiosidades' : 'Pausar curiosidades'}</button></div>
  </div>
}
