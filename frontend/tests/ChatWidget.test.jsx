
// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import ChatWidget from '../src/ChatWidget.jsx'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('ChatWidget de Fornaviva', () => {
  it('permite abrir y cerrar el asistente', () => {
    Element.prototype.scrollIntoView = vi.fn()

    render(<ChatWidget apiBase="http://localhost:8000" />)

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Abrir asistente de Fornaviva',
      }),
    )

    expect(
      screen.getByRole('dialog', {
        name: 'Asistente de Fornaviva',
      }),
    ).toBeTruthy()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Cerrar chat',
      }),
    )

    expect(
      screen.queryByRole('dialog', {
        name: 'Asistente de Fornaviva',
      }),
    ).toBeNull()
  })


  it('envía un mensaje a FastAPI y muestra la respuesta', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        respuesta: 'Tenemos pizza Margherita.',
        estado_reserva: null,
      }),
    })

    vi.stubGlobal('fetch', fetchMock)
    Element.prototype.scrollIntoView = vi.fn()

    render(<ChatWidget apiBase="http://localhost:8000" />)

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Abrir asistente de Fornaviva',
      }),
    )

    fireEvent.change(
      screen.getByRole('textbox', {
        name: 'Escribe tu pregunta',
      }),
      {
        target: { value: '¿Qué pizzas tenéis?' },
      },
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Enviar mensaje',
      }),
    )

    expect(
      await screen.findByText('Tenemos pizza Margherita.'),
    ).toBeTruthy()

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/chat',
      expect.objectContaining({
        method: 'POST',
      }),
    )

    const request = JSON.parse(fetchMock.mock.calls[0][1].body)

    expect(request.mensaje).toBe('¿Qué pizzas tenéis?')
  })

  it('muestra un error cuando FastAPI no responde', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('Network error')),
    )

    Element.prototype.scrollIntoView = vi.fn()

    render(<ChatWidget apiBase="http://localhost:8000" />)

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Abrir asistente de Fornaviva',
      }),
    )

    fireEvent.change(
      screen.getByRole('textbox', {
        name: 'Escribe tu pregunta',
      }),
      {
        target: { value: 'Hola' },
      },
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Enviar mensaje',
      }),
    )

    expect(
      await screen.findByRole('alert'),
    ).toHaveProperty(
      'textContent',
      expect.stringContaining('No se ha podido conectar'),
    )
  })


  it('reinicia la conversación al pulsar Nueva conversación', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          respuesta: '¡Tenemos muchas pizzas!',
          estado_reserva: null,
        }),
      }),
    )

    Element.prototype.scrollIntoView = vi.fn()

    render(<ChatWidget apiBase="http://localhost:8000" />)

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Abrir asistente de Fornaviva',
      }),
    )

    fireEvent.change(
      screen.getByRole('textbox', {
        name: 'Escribe tu pregunta',
      }),
      {
        target: { value: '¿Qué pizzas tenéis?' },
      },
    )

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Enviar mensaje',
      }),
    )

    expect(
      await screen.findByText('¡Tenemos muchas pizzas!'),
    ).toBeTruthy()

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Nueva conversación',
      }),
    )

    expect(
      screen.queryByText('¡Tenemos muchas pizzas!'),
    ).toBeNull()

    expect(
      screen.queryByText('¿Qué pizzas tenéis?'),
    ).toBeNull()

    expect(
      screen.getByText(/Soy el asistente de Fornaviva/),
    ).toBeTruthy()
  })


})

 it('muestra el horno solo durante la espera prolongada', () => {
   Element.prototype.scrollIntoView = vi.fn()
   const { rerender } = render(<ChatWidget apiBase="http://localhost:8000" availability="loading" />)
   fireEvent.click(screen.getByRole('button', {name:'Abrir asistente de Fornaviva'}))
   expect(screen.queryByText('¡Estamos calentando el horno!')).toBeNull()
   rerender(<ChatWidget apiBase="http://localhost:8000" availability="loading" delayed />)
   expect(screen.getByText('¡Estamos calentando el horno!')).toBeTruthy()
   expect(screen.getByRole('button', {name:'Enviar mensaje'}).disabled).toBe(true)
   fireEvent.click(screen.getByRole('button', {name:'Pausar curiosidades'}))
   expect(screen.getByRole('button', {name:'Reanudar curiosidades'})).toBeTruthy()
   rerender(<ChatWidget apiBase="http://localhost:8000" availability="ready" />)
   expect(screen.queryByText('¡Estamos calentando el horno!')).toBeNull()
 })
