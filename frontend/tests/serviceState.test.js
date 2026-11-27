import { describe, it, expect } from 'vitest'
import { initialState, serviceReducer as reduce } from '../src/serviceState.js'
import menu from '../../backend/data/menu.json'
const step = (s, type, extra = {}) => reduce(s, { type, ...extra })
describe('Disponibilidad independiente', () => {
  it('la copia local coincide con el backend', () => expect(initialState.dishes).toEqual(menu.carta))
  it('conserva la carta ante errores', () => expect(step(initialState, 'MENU_ERROR').dishes).toEqual(menu.carta))
  it('actualiza la carta cuando responde la API', () => expect(step(initialState, 'MENU_READY', { dishes: [] }).dishes).toEqual([]))
  it('activa la espera temática solo mientras conecta el chat', () => {
    expect(step(initialState, 'DELAY').chatDelayed).toBe(true)
    expect(step(step(initialState, 'CHAT_READY'), 'DELAY').chatDelayed).toBe(false)
  })
  it('retira la espera cuando responde o falla el chat', () => {
    const delayed = step(initialState, 'DELAY')
    expect(step(delayed, 'CHAT_READY').chatDelayed).toBe(false)
    expect(step(delayed, 'CHAT_ERROR').chatDelayed).toBe(false)
  })
  it('reintenta servicios por separado', () => {
    const failed = step(step(initialState, 'CHAT_ERROR'), 'MENU_ERROR')
    expect(step(failed, 'RETRY_MENU')).toMatchObject({menu:'loading',chat:'error'})
    expect(step(failed, 'RETRY_CHAT')).toMatchObject({menu:'error',chat:'loading',chatDelayed:false})
  })
})
