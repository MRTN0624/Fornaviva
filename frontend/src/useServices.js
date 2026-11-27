import { useEffect, useReducer } from 'react'
import { initialState, serviceReducer, CHAT_DISPLAY_DELAY_MS, CONNECTION_TIMEOUT_MS } from './serviceState'

function useRequest(apiBase, path, status, dispatch, success, failure, parse) {
  useEffect(() => {
    if (status !== 'loading') return
    const controller = new AbortController()
    let active = true
    const timeout = setTimeout(() => { if (active) dispatch({ type: failure }); controller.abort() }, CONNECTION_TIMEOUT_MS)
    async function load() {
      try {
        const response = await fetch(`${apiBase}${path}`, { signal: controller.signal })
        if (!response.ok) throw new Error('HTTP error')
        const data = parse(await response.json())
        if (active && !controller.signal.aborted) dispatch({ type: success, dishes: data })
      } catch {
        if (active && !controller.signal.aborted) dispatch({ type: failure })
      } finally { clearTimeout(timeout) }
    }
    load()
    return () => { active = false; clearTimeout(timeout); controller.abort() }
  }, [apiBase, path, status, dispatch, success, failure, parse])
}
function parseMenu(data) {
  const groups = Array.isArray(data) ? data : data?.carta ?? data?.menu?.carta
  if (!Array.isArray(groups)) throw new Error('Carta inválida')
  return groups.filter(g => g && typeof g.categoria === 'string' && Array.isArray(g.platos)).map(g => ({ ...g, platos: g.platos.filter(d => d && typeof d.nombre === 'string' && typeof d.precio === 'number' && Number.isFinite(d.precio)) }))
}
// La raíz existente verifica que FastAPI responde, no la disponibilidad de Gemini.
function parseBackend(data) {
  if (data?.proyecto !== 'Fornaviva') throw new Error('Backend inválido')
  return null
}
export default function useServices(apiBase) {
  const [state, dispatch] = useReducer(serviceReducer, initialState)
  useRequest(apiBase, '/api/menu', state.menu, dispatch, 'MENU_READY', 'MENU_ERROR', parseMenu)
  useRequest(apiBase, '/', state.chat, dispatch, 'CHAT_READY', 'CHAT_ERROR', parseBackend)
  useEffect(() => {
    if (state.chat !== 'loading') return
    const timer = setTimeout(() => dispatch({ type: 'DELAY' }), CHAT_DISPLAY_DELAY_MS)
    return () => clearTimeout(timer)
  }, [state.chat])
  return [state, dispatch]
}
