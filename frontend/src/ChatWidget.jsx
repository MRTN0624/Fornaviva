
import { useEffect, useRef, useState } from 'react'
import './ChatWidget.css'
import OvenWait from './OvenWait'

const INTRO = {
  role: 'assistant',
  text: '¡Ciao! Soy el asistente de Fornaviva. Pregúntame por nuestra carta, horarios, alérgenos o reservas simuladas.',
}

const MAX_MESSAGE = 2000
const REQUEST_TIMEOUT = 20000

export default function ChatWidget({ apiBase, availability = 'ready', delayed = false, onRetry }) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [reservation, setReservation] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const visibleMessages = availability === 'ready' ? [INTRO, ...messages] : messages

  const endRef = useRef(null)
  const inputRef = useRef(null)
  const controllerRef = useRef(null)
  const requestIdRef = useRef(0)
  const busyRef = useRef(false)

  useEffect(() => {
    if (open) {
      endRef.current?.scrollIntoView({
        behavior: 'auto',
        block: 'end',
      })

    }
  }, [messages, open, busy, availability])

  useEffect(() => {
    return () => {
      requestIdRef.current += 1
      controllerRef.current?.abort()
    }
  }, [])

  async function send(event) {
    event.preventDefault()

    const text = draft.trim()

    if (availability !== 'ready' || !text || busyRef.current || text.length > MAX_MESSAGE) {
      return
    }

    const history = messages
      .filter((message) => !message.error)
      .slice(-20)
      .map((message) => ({
        rol: message.role === 'user' ? 'user' : 'assistant',
        contenido: message.text.slice(0, MAX_MESSAGE),
      }))

    const requestId = ++requestIdRef.current
    const controller = new AbortController()

    controllerRef.current = controller
    busyRef.current = true

    setMessages((current) => [
      ...current,
      { role: 'user', text },
    ])
    setDraft('')
    setError('')
    setBusy(true)

    const timeout = setTimeout(() => {
      controller.abort()
    }, REQUEST_TIMEOUT)

    try {
      const response = await fetch(`${apiBase}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mensaje: text,
          historial: history,
          estado_reserva: reservation,
        }),
        signal: controller.signal,
      })

      if (requestId !== requestIdRef.current) {
        return
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      if (requestId !== requestIdRef.current) {
        return
      }

      if (
        !data ||
        typeof data !== 'object' ||
        typeof data.respuesta !== 'string'
      ) {
        throw new Error('Respuesta inválida del servidor')
      }

      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: data.respuesta,
        },
      ])

      setReservation(data.estado_reserva ?? null)
    } catch (err) {
      if (requestId !== requestIdRef.current) {
        return
      }

      if (err.name === 'AbortError') {
        setError(
          'El asistente ha tardado demasiado en responder. Inténtalo de nuevo.',
        )
      } else {
        setError(
          'No se ha podido conectar con el asistente. Comprueba que FastAPI esté funcionando e inténtalo de nuevo.',
        )
      }
    } finally {
      clearTimeout(timeout)

      if (requestId === requestIdRef.current) {
        controllerRef.current = null
        busyRef.current = false
        setBusy(false)
      }
    }
  }

  function reset() {
    requestIdRef.current += 1

    controllerRef.current?.abort()
    controllerRef.current = null
    busyRef.current = false

    setMessages([])
    setReservation(null)
    setDraft('')
    setError('')
    setBusy(false)
  }

  return (
    <div className="fv-chat-root">
      {open && (
        <section
          className="fv-chat-panel"
          role="dialog"
          aria-label="Asistente de Fornaviva"
        >
          <header className="fv-chat-header">
            <div>
              <span className="fv-chat-overline">
                FORNAVIVA · ASISTENTE
              </span>
              <strong>¿En qué te ayudamos?</strong>
            </div>

            <div className="fv-chat-header-actions">
              <button
                type="button"
                onClick={reset}
                title="Nueva conversación"
                aria-label="Nueva conversación"
              >
                ↺
              </button>

              <button
                type="button"
                onClick={() => setOpen(false)}
                title="Cerrar chat"
                aria-label="Cerrar chat"
              >
                ×
              </button>
            </div>
          </header>

          <div
            className="fv-chat-messages"
            role="log"
            aria-live="polite"
            aria-relevant="additions text"
          >
            {visibleMessages.map((message, index) => (
              <div
                key={index}
                className={`fv-chat-bubble ${
                  message.role === 'user'
                    ? 'fv-chat-user'
                    : 'fv-chat-assistant'
                }`}
              >
                {message.text
                  .replace(/\*\*/g, '')
                  .replace(/_/g, '')}
              </div>
            ))}

            {busy && (
              <div className="fv-chat-bubble fv-chat-assistant fv-chat-wait">
                Escribiendo…
              </div>
            )}

            {error && (
              <p className="fv-chat-error" role="alert">
                {error}
              </p>
            )}

            <div ref={endRef} />
          </div>

          {availability === 'loading' && delayed ? <OvenWait /> : availability !== 'ready' && <div className="fv-chat-disclaimer"><p role="status">{availability === 'loading' ? 'El chatbot se está despertando…' : 'No se ha podido conectar con el asistente.'}</p>{availability === 'error' && <button type="button" onClick={onRetry}>Reintentar conexión</button>}</div>}
          <form className="fv-chat-form" onSubmit={send}>
            <label
              htmlFor="fv-chat-input"
              className="fv-visually-hidden"
            >
              Escribe tu pregunta
            </label>

            <input
              ref={inputRef}
              id="fv-chat-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              maxLength={MAX_MESSAGE}
              placeholder={availability === 'loading' ? 'El chatbot se está despertando…' : availability === 'error' ? 'Asistente no disponible' : 'Escribe tu pregunta…'}
              disabled={busy || availability !== 'ready'}
            />

            <button
              type="submit"
              disabled={busy || availability !== 'ready' || !draft.trim()}
              aria-label="Enviar mensaje"
            >
              ↗
            </button>
          </form>

          <p className="fv-chat-disclaimer">
            Restaurante ficticio · Reservas simuladas · Confirma alérgenos con el personal
          </p>
        </section>
      )}

      <button
        className="fv-chat-launcher"
        type="button"
        aria-expanded={open}
        aria-label={
          open
            ? 'Cerrar asistente'
            : 'Abrir asistente de Fornaviva'
        }
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true">
          {open ? '×' : '✳'}
        </span>
        <span>
          {open ? 'Cerrar' : 'Pregúntanos'}
        </span>
      </button>
    </div>
  )
}
