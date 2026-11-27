import { useState } from 'react'
import useServices from './useServices'
import ChatWidget from './ChatWidget'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const filters = ['Todos', 'Pizzas', 'Antipasti', 'Dolci', 'Bebidas']

function App() {
  const [state, dispatch] = useServices(API_BASE)
  const menu = state.dishes
  const [category, setCategory] = useState('Pizzas')
  const [mobileOpen, setMobileOpen] = useState(false)
  const dishes = menu.flatMap((group) =>
    (group.platos || []).map((dish) => ({ ...dish, categoria: group.categoria }))
  )
  const visible = category === 'Todos' ? dishes : dishes.filter((dish) => dish.categoria === (category === 'Bebidas' ? 'Bevande' : category))
  const money = (price) => new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(price)

  return (
    <div className="site-shell">
      <header className="site-header">
        <a className="wordmark" href="#inicio" aria-label="Fornaviva, inicio">forna<span>viva</span><i>.</i></a>
        <button className="menu-toggle" type="button" aria-expanded={mobileOpen} aria-label="Abrir navegación" onClick={() => setMobileOpen(!mobileOpen)}>☰</button>
        <nav className={mobileOpen ? 'nav-links open' : 'nav-links'} aria-label="Navegación principal">
          <a href="#filosofia" onClick={() => setMobileOpen(false)}>Nuestra esencia</a>
          <a href="#carta" onClick={() => setMobileOpen(false)}>La carta</a>
          <a href="#visitanos" onClick={() => setMobileOpen(false)}>Visítanos</a>
        </nav>
        <a className="header-cta" href="#carta">Explorar carta <span aria-hidden="true">↗</span></a>
      </header>

      <main>
        <section className="hero" id="inicio">
          <div className="hero-copy">
            <p className="eyebrow"><span className="eyebrow-line" /> TRADICIÓN ITALIANA · ESPÍRITU ACTUAL</p>
            <h1>El fuego<br />tiene <em>alma.</em></h1>
            <p className="hero-lead">Ingredientes honestos. Masa con paciencia. Una forma diferente de vivir la pizza italiana.</p>
            <div className="hero-actions"><a className="button button-light" href="#carta">Descubre nuestra carta <span>↗</span></a><a className="text-link" href="#filosofia">Conoce Fornaviva <span>↓</span></a></div>
            <div className="hero-bottom"><span>HECHO CON CALMA. SERVIDO CON PASIÓN.</span><a href="#filosofia" className="scroll-link">
  DESCUBRE MÁS ↓
</a></div>
          </div>
          <div className="hero-visual" role="img" aria-label="Pizza artesanal recién horneada">
            <div className="pizza-art"><div className="pizza-inner"><span className="leaf leaf-one"/><span className="leaf leaf-two"/><span className="leaf leaf-three"/><span className="leaf leaf-four"/><span className="leaf leaf-five"/></div></div>
            <div className="hero-visual-label">UNA HISTORIA QUE EMPIEZA EN EL HORNO <span>✳</span></div>
          </div>
        </section>

        <section className="intro section-pad" id="filosofia"><div><p className="eyebrow dark">✳ &nbsp; NUESTRA FILOSOFÍA</p><h2>No es solo pizza.<br /><em>Es nuestra forma de ser.</em></h2></div><div className="intro-right"><p>Creemos en lo sencillo hecho extraordinariamente bien: una masa cuidada, ingredientes que hablan por sí solos y el placer de compartir la mesa.</p><a className="small-accent" href="#carta">
  FATTO CON AMORE <span>↗</span>
</a></div></section>

        <section className="menu-section section-pad" id="carta"><div className="section-heading"><div><p className="eyebrow dark">✳ &nbsp; EL SABOR DE FORNAVIVA</p><h2>La carta<span className="period">.</span></h2></div><p>Un recorrido por Italia, plato a plato.<br />Sin prisas, como debe ser.</p></div>
          {state.menu === 'error' && <div className="menu-notice"><p role="status">No se ha podido actualizar la carta. Mostramos la versión guardada.</p><button type="button" onClick={() => dispatch({ type: 'RETRY_MENU' })}>Reintentar actualización</button></div>}
          <div className="filters" role="group" aria-label="Filtrar carta">{filters.map((filter) => <button key={filter} type="button" className={category === filter ? 'filter active' : 'filter'} onClick={() => setCategory(filter)}>{filter}</button>)}</div>
          {visible.length === 0 ? <p className="menu-notice">No hay platos disponibles en esta categoría.</p> : <div className="dish-grid">{visible.map((dish, index) => <article className="dish" key={dish.id || `${dish.nombre}-${index}`}><div className="dish-number">{String(index + 1).padStart(2, '0')} <span>✳</span></div><div className="dish-content"><div className="dish-title-row"><h3>{dish.nombre}</h3><strong>{money(dish.precio)}</strong></div><p>{dish.descripcion}</p><span className="dish-category">{dish.categoria}</span></div></article>)}</div>}
          <p className="allergen-note">¿Tienes alguna alergia o intolerancia? Consulta con nuestro equipo antes de realizar tu pedido.</p>
        </section>

        <section className="closing" id="visitanos"><div className="closing-mark">✳</div><p className="eyebrow">NOS VEMOS EN LA MESA</p><h2>La buena vida<br />se <em>comparte.</em></h2><p>Una buena pizza siempre sabe mejor en compañía.</p><a href="#carta" className="button button-light">Volver a la carta <span>↑</span></a></section>
      </main>
      <ChatWidget apiBase={API_BASE} availability={state.chat} delayed={state.chatDelayed} onRetry={() => dispatch({ type: 'RETRY_CHAT' })} />
      <footer className="footer"><a className="wordmark" href="#inicio">forna<span>viva</span><i>.</i></a><span>COCINA ITALIANA · PASIÓN SIN PRISAS</span><span>© {new Date().getFullYear()} FORNAVIVA · RESTAURANTE FICTICIO · Desarrollado por <a href="https://github.com/MRTN0624" target="_blank" rel="noopener noreferrer">Martín</a></span></footer>
    </div>
  )
}
export default App