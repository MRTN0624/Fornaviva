import menu from './data/menu.json'
export const CHAT_DISPLAY_DELAY_MS = 3000
export const CONNECTION_TIMEOUT_MS = 90000
export const initialState = { menu: 'loading', chat: 'loading', chatDelayed: false, dishes: menu.carta }
export function serviceReducer(state, event) {
  switch (event.type) {
    case 'MENU_READY': return { ...state, menu: 'ready', dishes: event.dishes }
    case 'MENU_ERROR': return { ...state, menu: 'error' }
    case 'CHAT_READY': return { ...state, chat: 'ready', chatDelayed: false }
    case 'CHAT_ERROR': return { ...state, chat: 'error', chatDelayed: false }
    case 'RETRY_MENU': return state.menu === 'error' ? { ...state, menu: 'loading' } : state
    case 'RETRY_CHAT': return state.chat === 'error' ? { ...state, chat: 'loading', chatDelayed: false } : state
    case 'DELAY': return state.chat === 'loading' ? { ...state, chatDelayed: true } : state
    default: return state
  }
}
