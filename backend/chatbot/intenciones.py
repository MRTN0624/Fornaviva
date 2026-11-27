"""
intenciones.py — Detección de intención del usuario (Fornaviva).
Funciona por coincidencia de palabras clave. El LLM (Fase 3) enriquecerá
este mecanismo pero este módulo se mantiene como fallback.
"""

import re
import unicodedata

PALABRAS_CLAVE = {
    "menu": [
        "carta", "menu", "plato", "platos", "comer", "comida",
        "precio", "precios", "costar", "cuesta", "entrante", "antipasti",
        "pizza", "pizzas", "postre", "dolci", "bebida", "bevande",
        "que teneis", "que hay", "que ofreceis", "que sirveis",
    ],
    "horarios": [
        "horario", "horarios", "abre", "abrir", "cierra", "cerrar",
        "cuando", "hora", "horas", "turno", "mediodia", "noche",
        "disponible", "disponibilidad", "abierto", "cerrado",
    ],
    "alergenos": [
        "alergeno", "alergenos", "alergia", "alergico", "intolerancia",
        "vegetariano", "vegetarianos", "vegetariana", "vegetarianas",
        "vegano", "vegana", "celiaco", "celiaca", "alergica", "alergias",
        "sin gluten", "gluten", "lactosa", "leche", "huevo",
        "frutos secos", "pescado", "marisco",
    ],
    "reserva": [
        "reserva", "reservar", "mesa", "book", "booking",
        "quiero una mesa", "necesito mesa", "apartar", "guardar sitio",
    ],
    "faq": [
        "donde", "ubicacion", "direccion", "como llegar",
        "mascota", "mascotas", "ninos", "infantil",
        "grupo", "grupos", "cancelar", "cancelacion", "politica",
        "telefono", "contacto", "email", "correo",
    ],
}


def _quitar_tildes(texto: str) -> str:
    """Elimina diacríticos para comparaciones insensibles a tildes."""
    normalizado = unicodedata.normalize("NFD", texto)
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


def detectar_intencion(texto: str) -> str:
    """
    Devuelve la intención detectada en el mensaje del usuario.

    Valores posibles: "menu", "horarios", "alergenos", "reserva", "faq", "desconocido"
    """
    texto_limpio = _quitar_tildes(texto.lower())
    for intencion in ("reserva", "alergenos", "horarios", "menu", "faq"):
        for palabra in PALABRAS_CLAVE[intencion]:
            if re.search(r"\b" + re.escape(palabra) + r"\b", texto_limpio):
                return intencion
    return "desconocido"
