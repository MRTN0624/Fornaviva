"""
respuestas.py — Generación de respuestas estructuradas para Fornaviva.

Cada función carga datos desde backend/data/ y devuelve texto en Markdown.
Ninguna función inventa información alimentaria: usa null cuando los datos
no están confirmados y añade el aviso de que son datos orientativos.
"""

import json
import os
import unicodedata

# Ruta a backend/data/ relativa a este archivo (backend/chatbot/)
RUTA_DATOS = os.path.join(os.path.dirname(__file__), "..", "data")


def cargar_json(nombre_archivo: str):
    """Carga un JSON de data/. Devuelve None si no existe o tiene error."""
    ruta = os.path.join(RUTA_DATOS, nombre_archivo)
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _quitar_tildes(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# AVISO GLOBAL — se añade al final de cualquier respuesta sobre alérgenos
# ---------------------------------------------------------------------------
_AVISO_ALERGENOS = (
    "\n\n⚠️ _Esta información es orientativa. "
    "Los datos no garantizan ausencia de contaminación cruzada. "
    "Ante cualquier alergia o intolerancia, consulta siempre con el personal._"
)


def responder_menu() -> str:
    datos = cargar_json("menu.json")
    if datos is None:
        return "Lo siento, no puedo mostrar la carta en este momento."

    lineas = ["🍕 **Carta de Fornaviva**\n"]
    for categoria in datos["carta"]:
        lineas.append(f"### {categoria['categoria']}")
        for plato in categoria["platos"]:
            lineas.append(f"**{plato['nombre']}** — {plato['precio']:.2f} €")
            lineas.append(f"  _{plato['descripcion']}_")
            lineas.append("")
    return "\n".join(lineas)


def responder_horarios() -> str:
    datos = cargar_json("horarios.json")
    if datos is None:
        return "Lo siento, no puedo consultar los horarios en este momento."

    lineas = [f"🕐 **Horarios de {datos['nombre_restaurante']}**\n"]
    lineas.append(f"_{datos['nota_general']}_\n")

    for dia_info in datos["horarios"]:
        dia = dia_info["dia"]
        if not dia_info["abierto"]:
            motivo = dia_info.get("motivo", "Cerrado")
            lineas.append(f"**{dia}:** Cerrado ({motivo})")
        else:
            turnos = []
            med = dia_info.get("turno_mediodia")
            noch = dia_info.get("turno_noche")
            if med:
                turnos.append(f"mediodía {med['apertura']}–{med['cierre']}")
            if noch:
                cierre_label = noch["cierre"]
                if noch.get("dia_siguiente"):
                    cierre_label += " (madrugada)"
                turnos.append(f"noche {noch['apertura']}–{cierre_label}")
            lineas.append(f"**{dia}:** {' | '.join(turnos)}")

    return "\n".join(lineas)


def responder_alergenos(texto: str) -> str:
    datos = cargar_json("alergenos.json")
    if datos is None:
        return "Lo siento, no puedo consultar los alérgenos en este momento."

    texto_limpio = _quitar_tildes(texto.lower())

    # Buscar si el usuario menciona un plato concreto por nombre
    plato_encontrado = None
    for plato in datos["platos"]:
        nombre_limpio = _quitar_tildes(plato["nombre"].lower())
        palabras = nombre_limpio.split()
        if any(p in texto_limpio for p in palabras if len(p) > 3):
            plato_encontrado = plato
            break

    if plato_encontrado:
        lineas = [f"🔍 **Alérgenos: {plato_encontrado['nombre']}**\n"]

        # Estado vegetariano: puede ser True, False o None
        veg = plato_encontrado.get("vegetariano")
        if veg is True:
            lineas.append("✅ Este plato es **apto para vegetarianos** (según los ingredientes declarados).")
        elif veg is False:
            lineas.append("🥩 Este plato **contiene carne, pescado u otro ingrediente animal**.")
        else:
            lineas.append(
                "❓ **Estado vegetariano no confirmado.** "
                "Este plato puede contener ingredientes de origen animal no verificados. "
                "Consulta con el personal."
            )

        # Alérgenos: puede ser una lista, una lista vacía o None
        alergenos = plato_encontrado.get("alergenos")
        if alergenos is None:
            lineas.append(
                "\n⚠️ **Alérgenos: información no disponible.** "
                "Los ingredientes de este plato varían. Consulta con el personal antes de pedir."
            )
        elif alergenos:
            lineas.append(f"\n**Alérgenos declarados:** {', '.join(alergenos)}")
        else:
            lineas.append("\n**Alérgenos:** Sin alérgenos de declaración obligatoria según los datos disponibles.")

        nota = plato_encontrado.get("nota")
        if nota:
            lineas.append(f"\n📝 _{nota}_")

        return "\n".join(lineas) + _AVISO_ALERGENOS

    # Sin plato concreto → mostrar platos con vegetariano confirmado True
    lineas = ["🥗 **Platos aptos para vegetarianos (confirmados)**\n"]
    lineas.append(f"_{datos['nota']}_\n")

    vegetarianos = [p for p in datos["platos"] if p.get("vegetariano") is True]
    no_confirmados = [p for p in datos["platos"] if p.get("vegetariano") is None]

    if vegetarianos:
        for plato in vegetarianos:
            alerg = plato.get("alergenos")
            alerg_txt = ", ".join(alerg) if alerg else "ninguno declarado"
            lineas.append(f"• **{plato['nombre']}** — Alérgenos: {alerg_txt}")
    else:
        lineas.append("No hay platos vegetarianos confirmados en este momento.")

    if no_confirmados:
        lineas.append("\n**Condición vegetariana no confirmada en:**")
        for plato in no_confirmados:
            lineas.append(f"  • {plato['nombre']} (consultar con el personal)")

    lineas.append(
        "\n_Para consultar los alérgenos de un plato concreto, escríbeme su nombre._"
    )
    return "\n".join(lineas) + _AVISO_ALERGENOS


def responder_faq(texto: str) -> str:
    datos = cargar_json("faqs.json")
    if datos is None:
        return "Lo siento, no puedo acceder a las preguntas frecuentes en este momento."

    texto_limpio = _quitar_tildes(texto.lower())
    palabras_usuario = set(texto_limpio.split())

    mejor_puntuacion = 0
    mejor_respuesta = None

    for entrada in datos["preguntas_frecuentes"]:
        pregunta_limpia = _quitar_tildes(entrada["pregunta"].lower())
        palabras_pregunta = set(pregunta_limpia.split())
        coincidencias = sum(
            1 for p in palabras_usuario
            if len(p) > 3 and p in palabras_pregunta
        )
        if coincidencias > mejor_puntuacion:
            mejor_puntuacion = coincidencias
            mejor_respuesta = entrada["respuesta"]

    if mejor_respuesta and mejor_puntuacion > 0:
        return f"💬 {mejor_respuesta}"

    lineas = ["❓ **Preguntas frecuentes**\n"]
    lineas.append("Estas son las preguntas más habituales:\n")
    for i, entrada in enumerate(datos["preguntas_frecuentes"], start=1):
        lineas.append(f"**{i}.** {entrada['pregunta']}")
    lineas.append("\n_Escríbeme sobre cualquiera de estos temas y te respondo._")
    return "\n".join(lineas)


def responder_desconocido() -> str:
    return (
        "🤔 No he entendido bien tu pregunta. Puedo ayudarte con:\n\n"
        "• 🍕 **Carta y precios** — escríbeme \"carta\" o \"pizzas\"\n"
        "• 🕐 **Horarios** — escríbeme \"horario\" o \"cuándo abrís\"\n"
        "• 🥗 **Alérgenos** — escríbeme \"alérgenos\" o el nombre de un plato\n"
        "• 📅 **Reservas** — escríbeme \"reserva\" o \"mesa\"\n"
        "• ❓ **Preguntas frecuentes** — escríbeme \"dónde estáis\" o \"contacto\"\n\n"
        "_¿En qué puedo ayudarte?_"
    )
