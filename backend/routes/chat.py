"""
chat.py — Endpoint POST /api/chat de Fornaviva.

Esquema de petición:
    { "mensaje": str, "historial": [...], "estado_reserva": dict | null }

Esquema de respuesta:
    { "respuesta": str, "estado_reserva": dict | null }

El backend no confía en el estado recibido del cliente: lo sanitiza antes
de usarlo (ver reservas._sanitizar_estado).
Cuando el LLM no está configurado, responde con las funciones estructuradas.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Any, Literal

from chatbot.intenciones import detectar_intencion
from chatbot.respuestas import (
    responder_menu,
    responder_horarios,
    responder_alergenos,
    responder_faq,
    responder_desconocido,
)
from chatbot.reservas import gestionar_reserva, _sanitizar_estado
from chatbot.llm_client import completar, construir_contexto, INICIAR_RESERVA

router = APIRouter()

_AVISO_MODO_LIMITADO = (
    "⚠️ [Modo limitado — el asistente de IA no está disponible ahora mismo. "
    "Estoy respondiendo con información estructurada.]\n\n"
)


class MensajeHistorial(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rol: Literal["user", "assistant"]
    contenido: str = Field(min_length=1, max_length=2000)


class MensajeEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mensaje: str = Field(min_length=1, max_length=2000)
    historial: list[MensajeHistorial] = Field(default_factory=list, max_length=40)
    estado_reserva: dict[str, Any] | None = Field(default=None, max_length=16)

    @field_validator("mensaje")
    @classmethod
    def mensaje_no_vacio(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El mensaje no puede estar vacío.")
        return v

    @field_validator("historial")
    @classmethod
    def limitar_historial(cls, v):
        if sum(len(m.contenido) for m in v) > 20000:
            raise ValueError("El historial supera 20000 caracteres.")
        return v

    @field_validator("estado_reserva")
    @classmethod
    def limitar_estado(cls, v):
        if v is not None:
            for clave, valor in v.items():
                if len(clave) > 64 or type(valor) not in (str, int, bool, type(None)):
                    raise ValueError("Estado de reserva no válido.")
                if isinstance(valor, str) and len(valor) > 100:
                    raise ValueError("Un campo de reserva supera 100 caracteres.")
                if type(valor) is int and not -1000000 <= valor <= 1000000:
                    raise ValueError("Número fuera de los límites del estado.")
        return v


class RespuestaSalida(BaseModel):
    respuesta: str
    estado_reserva: dict[str, Any] | None = None


@router.post("/chat", response_model=RespuestaSalida)
async def chat(entrada: MensajeEntrada) -> RespuestaSalida:
    texto = entrada.mensaje
    estado_raw = entrada.estado_reserva

    # ---------------------------------------------------------------
    # ¿Hay una reserva activa? El estado llega del frontend (no fiable)
    # → _sanitizar_estado lo valida; si devuelve None el estado era inválido
    # ---------------------------------------------------------------
    estado_sanitizado = _sanitizar_estado(estado_raw)

    if (
        estado_raw is not None
        and estado_raw.get("activa") is not False
        and estado_sanitizado is None
    ):
        respuesta, nuevo_estado = gestionar_reserva(texto, estado_raw)
        return RespuestaSalida(
            respuesta=respuesta, estado_reserva=_serializar_estado(nuevo_estado)
        )

    reserva_activa = (
        estado_sanitizado is not None
        and estado_sanitizado.get("activa", False) is True
    )

    if reserva_activa:
        respuesta, nuevo_estado = gestionar_reserva(texto, estado_sanitizado)
        return RespuestaSalida(
            respuesta=respuesta,
            estado_reserva=_serializar_estado(nuevo_estado),
        )

    # ---------------------------------------------------------------
    # Sin reserva activa → intentar LLM primero, fallback a estructurado
    # ---------------------------------------------------------------
    intencion = detectar_intencion(texto)

    # Si la intención es reserva, el LLM nunca la gestiona directamente
    if intencion == "reserva":
        respuesta, nuevo_estado = gestionar_reserva(texto, None)
        return RespuestaSalida(
            respuesta=respuesta,
            estado_reserva=_serializar_estado(nuevo_estado),
        )

    # Para el resto de intenciones, intentar LLM
    historial_reciente = [
    {"rol": m.rol, "contenido": m.contenido}
    for m in entrada.historial[-6:]
    ]

    historial_reciente.append({
        "rol": "user",
        "contenido": texto
    })

    llm_respuesta = await completar(
        historial_reciente,
        construir_contexto()
    )

    # Límite interno de peticiones
    if llm_respuesta == "__FORNAVIVA_LIMITE__":
        return RespuestaSalida(
            respuesta=(
                "⏳ Has enviado varios mensajes seguidos. "
                "Espera aproximadamente un minuto para continuar "
                "conversando con nuestro asistente."
            ),
            estado_reserva=None,
        )

    # Gemini solicita iniciar una reserva
    if llm_respuesta == INICIAR_RESERVA:
        respuesta, nuevo_estado = gestionar_reserva(texto, None)
        return RespuestaSalida(
            respuesta=respuesta, estado_reserva=_serializar_estado(nuevo_estado)
        )
    if isinstance(llm_respuesta, str) and llm_respuesta.strip():
        return RespuestaSalida(respuesta=llm_respuesta, estado_reserva=None)

    # Modo fallback estructurado
    prefijo = _AVISO_MODO_LIMITADO

    if intencion == "menu":
        respuesta = prefijo + responder_menu()
    elif intencion == "horarios":
        respuesta = prefijo + responder_horarios()
    elif intencion == "alergenos":
        respuesta = prefijo + responder_alergenos(texto)
    elif intencion == "faq":
        respuesta = prefijo + responder_faq(texto)
    else:
        respuesta = prefijo + responder_desconocido()

    return RespuestaSalida(respuesta=respuesta, estado_reserva=None)


def _serializar_estado(estado: dict | None) -> dict | None:
    """Convierte objetos date a str para que sean serializables por JSON."""
    if estado is None:
        return None
    resultado = dict(estado)
    if "fecha" in resultado and hasattr(resultado["fecha"], "strftime"):
        resultado["fecha"] = resultado["fecha"].strftime("%d/%m/%Y")
    return resultado
