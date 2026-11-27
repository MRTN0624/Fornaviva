

// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  cleanup,
  fireEvent,
  render,
  screen,
} from '@testing-library/react'
import App from '../src/App.jsx'

const menu = [
  {
    categoria: 'Pizzas',
    platos: [
      {
        id: 1,
        nombre: 'Margherita',
        descripcion: 'Tomate, mozzarella y albahaca',
        precio: 11,
      },
    ],
  },
  {
    categoria: 'Antipasti',
    platos: [
      {
        id: 2,
        nombre: 'Bruschetta',
        descripcion: 'Pan tostado con tomate',
        precio: 6.5,
      },
    ],
  },
  {
    categoria: 'Bevande',
    platos: [
      {
        id: 3,
        nombre: 'Limonata',
        descripcion: 'Refresco de limón',
        precio: 3,
      },
    ],
  },
]

function mockMenuResponse(data = { carta: menu }) {
  const fetchMock = vi.fn().mockImplementation(async (url) => ({
    ok: true,
    json: async () => url.endsWith('/api/menu') ? data : { proyecto: 'Fornaviva' },
  }))

  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Carta de Fornaviva', () => {
  it('muestra la carta local sin esperar a la API', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<App />)
    expect(screen.getByText('Margherita')).toBeTruthy()
    expect(screen.getByText(/Mostrando la carta guardada/)).toBeTruthy()
  })

  it('carga las pizzas desde FastAPI', async () => {
    const fetchMock = mockMenuResponse()

    render(<App />)

    expect(await screen.findByText('Tomate, mozzarella y albahaca')).toBeTruthy()

    expect(screen.queryByText('Bruschetta')).toBeNull()

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/menu',
      expect.objectContaining({
        signal: expect.any(AbortSignal),
      }),
    )
  })

  it('permite filtrar la carta por categorías', async () => {
    mockMenuResponse()

    render(<App />)

    await screen.findByText('Tomate, mozzarella y albahaca')

    fireEvent.click(
      screen.getByRole('button', { name: 'Antipasti' }),
    )

    expect(screen.getByText('Bruschetta')).toBeTruthy()
    expect(screen.queryByText('Margherita')).toBeNull()

    fireEvent.click(
      screen.getByRole('button', { name: 'Todos' }),
    )

    expect(screen.getByText('Margherita')).toBeTruthy()
    expect(screen.getByText('Bruschetta')).toBeTruthy()
    expect(screen.getByText('Limonata')).toBeTruthy()
  })

  it('relaciona Bebidas con la categoría Bevande', async () => {
    mockMenuResponse()

    render(<App />)

    await screen.findByText('Tomate, mozzarella y albahaca')

    fireEvent.click(
      screen.getByRole('button', { name: 'Bebidas' }),
    )

    expect(screen.getByText('Limonata')).toBeTruthy()
    expect(screen.queryByText('Margherita')).toBeNull()
  })

  it('muestra un aviso si FastAPI no responde', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('Network error')),
    )

    render(<App />)

    expect(
      await screen.findByText(/No se ha podido actualizar la carta/),
    ).toBeTruthy()
  })

  it('rechaza una carta con formato incorrecto', async () => {
    mockMenuResponse({
      carta: 'formato incorrecto',
    })

    render(<App />)

    expect(
      await screen.findByText(/No se ha podido actualizar la carta/),
    ).toBeTruthy()
  })

  it('descarta los platos con datos inválidos', async () => {
    mockMenuResponse({
      carta: [
        {
          categoria: 'Pizzas',
          platos: [
            {
              nombre: 'Margherita',
              descripcion: 'Pizza clásica',
              precio: 11,
            },
            {
              nombre: 'Pizza inválida',
              descripcion: 'Precio incorrecto',
              precio: 'gratis',
            },
          ],
        },
      ],
    })

    render(<App />)

    expect(await screen.findByText('Pizza clásica')).toBeTruthy()
    expect(screen.queryByText('Pizza inválida')).toBeNull()
  })

  it('muestra un aviso cuando una categoría está vacía', async () => {
    mockMenuResponse()

    render(<App />)

    await screen.findByText('Tomate, mozzarella y albahaca')

    fireEvent.click(
      screen.getByRole('button', { name: 'Dolci' }),
    )

    expect(
      screen.getByText('No hay platos disponibles en esta categoría.'),
    ).toBeTruthy()
  })
})
