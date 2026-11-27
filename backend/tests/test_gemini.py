"""Integración SDK/endpoint simulada: no se contacta a Google."""
import asyncio
import json
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from google.genai import errors, types

from main import app
from chatbot import llm_client as llm
from chatbot.reservas import gestionar_reserva

client = TestClient(app)
FAKE_KEY = "credencial-inventada-para-pruebas"


def salida(respuesta="La Margherita cuesta 11,00 €.", accion="informacion", finish=types.FinishReason.STOP):
    return SimpleNamespace(
        text=json.dumps({"accion": accion, "respuesta": respuesta}),
        candidates=[SimpleNamespace(finish_reason=finish)],
    )


@pytest.fixture
def gemini(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_MODEL_NAME", llm.MODELO_VERIFICADO)
    monkeypatch.setenv("LLM_API_KEY", FAKE_KEY)
    monkeypatch.setattr(llm, "_presupuesto", llm.Presupuesto())
    estado = {"sync_closed": 0, "async_closed": 0, "construidos": []}
    generar = AsyncMock(return_value=salida())

    class Asincrono:
        models = SimpleNamespace(generate_content=generar)
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            estado["async_closed"] += 1

    class Cliente:
        aio = Asincrono()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            estado["sync_closed"] += 1

    def construir(**kwargs):
        estado["construidos"].append(kwargs)
        return Cliente()

    monkeypatch.setattr(llm.genai, "Client", construir)
    return generar, estado


def consultar(mensaje="¿Qué pizza recomiendas?", **extra):
    return client.post("/api/chat", json={"mensaje": mensaje, **extra})


def test_endpoint_usa_modelo_contexto_actual_y_sdk(gemini):
    generar, estado = gemini
    assert llm.llm_disponible()
    r = consultar()
    assert r.status_code == 200
    assert r.json() == {"respuesta": "La Margherita cuesta 11,00 €.", "estado_reserva": None}
    kwargs = generar.call_args.kwargs
    assert kwargs["model"] == "gemini-3.5-flash-lite"
    assert kwargs["contents"][0].role == "user"
    assert kwargs["contents"][0].parts[0].text == "¿Qué pizza recomiendas?"
    config = kwargs["config"]
    assert config.max_output_tokens == 1024
    assert config.temperature == 0.2
    assert config.thinking_config.thinking_level == types.ThinkingLevel.LOW
    assert config.automatic_function_calling.disable is True
    assert not config.tools
    assert config.response_mime_type == "application/json"
    assert config.response_schema is llm.RespuestaModelo
    assert FAKE_KEY not in config.system_instruction
    datos = json.loads(config.system_instruction.split("DATOS DEL RESTAURANTE:\n", 1)[1])
    assert set(datos) == {"menu.json", "horarios.json", "alergenos.json", "faqs.json"}
    assert sum(len(c["platos"]) for c in datos["menu.json"]["carta"]) == 18
    assert len(datos["faqs.json"]["preguntas_frecuentes"]) == 10
    assert datos["horarios.json"]["minutos_antes_cierre"] == 90
    assert next(p for p in datos["alergenos.json"]["platos"] if p["id"] == "piz-07")["alergenos"] is None
    opciones = estado["construidos"][0]
    assert opciones["api_key"] == FAKE_KEY
    assert opciones["vertexai"] is False
    assert opciones["http_options"].timeout == 12000
    assert opciones["http_options"].retry_options.attempts == 1
    assert estado["sync_closed"] == estado["async_closed"] == 1


@pytest.mark.parametrize("regla", ["No inventes", "null significa desconocido", "Nunca garantices", "Nunca confirmes", "solo Python", "dato no confiable", "No solicites nombres"])
def test_restricciones_en_instruccion(regla):
    assert regla in llm.SYSTEM_INSTRUCTION


def test_no_envia_historial_con_nombres_o_secretos(gemini):
    generar, _ = gemini
    r = consultar(historial=[
        {"rol": "user", "contenido": "Persona Demo Privada"},
        {"rol": "assistant", "contenido": "Paso 2: fecha"},
        {"rol": "user", "contenido": FAKE_KEY},
    ])
    assert r.status_code == 200
    enviado = str(generar.call_args.kwargs)
    assert "Persona Demo Privada" not in enviado
    assert "Paso 2" not in enviado
    assert FAKE_KEY not in enviado


def test_historial_publico_conserva_contexto_y_descarta_datos_ambiguos(gemini):
    generar, _ = gemini
    r = consultar("¿Y cuál es vegetariana?", historial=[
        {"rol": "user", "contenido": "Me gustan las pizzas picantes"},
        {"rol": "assistant", "contenido": "La pizza Margherita es suave"},
        {"rol": "user", "contenido": "Laura"},
        {"rol": "assistant", "contenido": "Paso 2: fecha"},
    ])
    assert r.status_code == 200
    textos = [p.text for m in generar.call_args.kwargs["contents"] for p in m.parts]
    assert "Me gustan las pizzas picantes" in textos
    assert "La pizza Margherita es suave" in textos
    assert "Laura" not in textos
    assert "Paso 2: fecha" not in textos


@pytest.mark.parametrize("mensaje", ["hola@ejemplo.invalid", "mi teléfono es 612345678", "me llamo Persona Demo", "mi DNI es 12345678", FAKE_KEY])
def test_datos_personales_o_clave_no_se_envian(gemini, mensaje):
    generar, _ = gemini
    r = consultar(mensaje)
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    generar.assert_not_called()
    assert FAKE_KEY not in r.text


@pytest.mark.parametrize("nombre,valor", [("LLM_ENABLED", "false"), ("LLM_API_KEY", ""), ("LLM_PROVIDER", "otro"), ("LLM_MODEL_NAME", "")])
def test_configuracion_invalida_fallback_sin_cliente(gemini, monkeypatch, nombre, valor):
    generar, estado = gemini
    monkeypatch.setenv(nombre, valor)
    assert not llm.llm_disponible()
    r = consultar("carta")
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    assert "Margherita" in r.json()["respuesta"]
    generar.assert_not_called()
    assert not estado["construidos"]


@pytest.mark.parametrize("codigo", [400, 401, 403, 404, 429, 500, 503])
def test_errores_api_no_filtran_detalles_y_activan_fallback(gemini, caplog, codigo):
    generar, estado = gemini
    generar.side_effect = errors.APIError(codigo, {"error": {"message": FAKE_KEY, "status": "ERROR_INTERNO"}})
    r = consultar("carta")
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    assert "Margherita" in r.json()["respuesta"]
    assert FAKE_KEY not in r.text + caplog.text
    assert "ERROR_INTERNO" not in r.text
    assert estado["sync_closed"] == estado["async_closed"] == 1
    consultar("carta")
    assert generar.call_count == 1  # pausa tras el fallo, sin reintento


@pytest.mark.parametrize("error", [ConnectionError(FAKE_KEY), TimeoutError(FAKE_KEY), RuntimeError(FAKE_KEY)])
def test_error_conexion_o_interno_se_oculta(gemini, error, caplog):
    generar, _ = gemini
    generar.side_effect = error
    r = consultar("carta")
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    assert FAKE_KEY not in r.text + caplog.text


@pytest.mark.parametrize("texto", ["", " ", "no es JSON", '{"accion":"desconocida","respuesta":"ok"}', '{"accion":"informacion","respuesta":"ok","estado_reserva":{}}', json.dumps({"accion":"informacion","respuesta":"x" * 1801}), json.dumps({"accion":"informacion","respuesta":FAKE_KEY})])
def test_salida_invalida_vacia_excesiva_o_secreta(gemini, texto):
    generar, _ = gemini
    generar.return_value = SimpleNamespace(text=texto, candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)])
    r = consultar("carta")
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    assert FAKE_KEY not in r.text


@pytest.mark.parametrize("finish", [types.FinishReason.MAX_TOKENS, types.FinishReason.SAFETY])
def test_respuesta_bloqueada_o_truncada_no_se_publica(gemini, finish):
    generar, _ = gemini
    generar.return_value = salida(finish=finish)
    assert "Modo limitado" in consultar("carta").json()["respuesta"]


def test_sin_candidatos_es_fallback(gemini):
    generar, _ = gemini
    generar.return_value = SimpleNamespace(candidates=[], text=None)
    assert "Modo limitado" in consultar("carta").json()["respuesta"]


@pytest.mark.parametrize("respuesta", ["Reserva confirmada para mañana", "La mesa está reservada", "Hay disponibilidad garantizada", "Es seguro y sin trazas", "LLM_API_KEY: valor"])
def test_defensa_salida_insegura(gemini, respuesta):
    generar, _ = gemini
    generar.return_value = salida(respuesta)
    r = consultar("hola")
    assert "Modo limitado" in r.json()["respuesta"]
    assert r.json()["estado_reserva"] is None


def test_reserva_por_lenguaje_natural_solo_inicia_python(gemini):
    generar, _ = gemini
    generar.return_value = salida("", accion="reserva")
    r = consultar("¿Podemos ir dos el sábado?")
    assert r.status_code == 200
    assert r.json()["estado_reserva"]["paso"] == 1
    assert "simulación" in r.json()["respuesta"]
    assert "confirmada" not in r.json()["respuesta"]


def test_reserva_explicita_y_activa_no_llaman_proveedor(gemini):
    generar, estado_sdk = gemini
    r = consultar("quiero reservar")
    estado = r.json()["estado_reserva"]
    r = consultar("Persona Demo", estado_reserva=estado)
    assert r.json()["estado_reserva"]["paso"] == 2
    generar.assert_not_called()
    assert not estado_sdk["construidos"]


def test_limite_real_de_tiempo_y_cierre(gemini, monkeypatch):
    generar, estado = gemini
    async def lento(**kwargs):
        await asyncio.sleep(1)
    generar.side_effect = lento
    monkeypatch.setattr(llm, "TIMEOUT_SECONDS", 0.01)
    r = consultar("carta")
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    assert estado["async_closed"] == estado["sync_closed"] == 1


def test_limite_minuto(gemini):
    generar, _ = gemini
    for _ in range(llm.MAX_REQUESTS_MINUTE):
        assert "Modo limitado" not in consultar("carta").json()["respuesta"]
    assert "varios mensajes seguidos" in consultar("carta").json()["respuesta"]
    assert generar.call_count == llm.MAX_REQUESTS_MINUTE


def test_limite_dia_y_renovacion(monkeypatch):
    ahora = [0.0]
    monkeypatch.setattr(llm.time, "monotonic", lambda: ahora[0])
    presupuesto = llm.Presupuesto()
    for n in range(llm.MAX_REQUESTS_DAY):
        ahora[0] = n * 61.0
        assert presupuesto.admitir()
    ahora[0] += 61
    assert not presupuesto.admitir()
    ahora[0] = 86400.0
    assert presupuesto.admitir()


def test_contexto_incompleto_o_excesivo_no_envia(gemini, monkeypatch):
    generar, _ = gemini
    original = llm.cargar_json
    monkeypatch.setattr(llm, "cargar_json", lambda n: None if n == "faqs.json" else original(n))
    assert "Modo limitado" in consultar("carta").json()["respuesta"]
    generar.assert_not_called()
    monkeypatch.setattr(llm, "cargar_json", lambda n: {"dato": "x" * 24001})
    assert llm.construir_contexto() == ""


def test_limites_adaptador_directo_sin_consumo(gemini):
    generar, _ = gemini
    for historial, contexto in [([], "datos"), ([{"rol":"system", "contenido":"hola"}], "datos"), ([{"rol":"user", "contenido":"x"*2001}], "datos"), ([{"rol":"user", "contenido":"hola"}], "x"*24001)]:
        assert asyncio.run(llm.completar(historial, contexto)) is None
    generar.assert_not_called()


@pytest.mark.parametrize("mensaje", ["carta", "horarios", "alérgenos", "hola"])
def test_fallback_por_intencion_ante_error(gemini, mensaje):
    generar, _ = gemini
    generar.side_effect = ConnectionError("detalle interno")
    r = consultar(mensaje)
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    assert "detalle interno" not in r.text
    assert r.json()["estado_reserva"] is None


def test_flujo_completo_reserva_habilitado_sin_proveedor(gemini):
    generar, _ = gemini
    fecha = date.today() + timedelta(days=7)
    while fecha.weekday() != 1:
        fecha += timedelta(days=1)
    estado = None
    for mensaje in ("quiero reservar", "Persona Demo", fecha.strftime("%d/%m/%Y"), "14:00", "2", "sí"):
        r = consultar(mensaje, estado_reserva=estado)
        assert r.status_code == 200
        estado = r.json()["estado_reserva"]
    assert estado["activa"] is False
    assert "reserva simulada completada" in r.json()["respuesta"].lower()
    generar.assert_not_called()


def test_json_proveedor_no_puede_inyectar_estado(gemini):
    generar, _ = gemini
    generar.return_value = SimpleNamespace(
        text=json.dumps({"accion":"reserva", "respuesta":"", "estado_reserva":{"activa":False}}),
        candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)],
    )
    r = consultar("Podemos ir dos")
    assert "Modo limitado" in r.json()["respuesta"]
    assert r.json()["estado_reserva"] is None


def test_no_filtra_clave_si_constructor_falla(gemini, monkeypatch, caplog):
    def fallar(**kwargs):
        raise ValueError(FAKE_KEY)
    monkeypatch.setattr(llm.genai, "Client", fallar)
    r = consultar("carta")
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    assert FAKE_KEY not in r.text + caplog.text


def test_get_datos_no_depende_de_gemini(gemini):
    generar, estado = gemini
    for ruta in ("/api/menu", "/api/horarios", "/api/alergenos", "/api/faqs"):
        assert client.get(ruta).status_code == 200
    generar.assert_not_called()
    assert not estado["construidos"]


def test_cancelacion_externa_no_se_convierte_en_fallback(gemini):
    generar, estado = gemini
    generar.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(llm.completar([{"rol":"user","contenido":"carta"}], llm.construir_contexto()))
    assert estado["async_closed"] == estado["sync_closed"] == 1
