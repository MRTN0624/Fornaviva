"""Regresiones de la estabilización; sin proveedor externo ni datos personales."""
import asyncio
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from main import app
from chatbot.intenciones import detectar_intencion
from chatbot.reservas import _sanitizar_estado, gestionar_reserva
from chatbot import llm_client
from request_limits import MAX_BODY_BYTES, RequestSizeLimitMiddleware

client = TestClient(app)


def estado_confirmacion():
    fecha = date.today() + timedelta(days=7)
    while fecha.weekday() != 1:
        fecha += timedelta(days=1)
    return dict(activa=True, paso=5, nombre="Persona Demo", fecha=fecha.strftime("%d/%m/%Y"), hora="14:00", personas=2)


@pytest.mark.parametrize("mensaje,intencion", [
    ("alérgenos de la pizza Margherita", "alergenos"),
    ("¿La pizza Quattro Formaggi es vegetariana?", "alergenos"),
    ("¿Qué platos hay sin gluten?", "alergenos"),
    ("quiero reservar a las 21:00, ¿qué horario tenéis?", "reserva"),
    ("quiero una mesa para comer pizza", "reserva"),
    ("quiero reservar, soy alérgico al gluten", "reserva"),
    ("qué pizzas tenéis", "menu"),
    ("a qué hora abrís", "horarios"),
    ("donde estais ubicados", "faq"),
    ("el mesado", "desconocido"),
])
def test_prioridad_intenciones(mensaje, intencion):
    assert detectar_intencion(mensaje) == intencion


@pytest.mark.parametrize("mensaje,esperado", [
    ("alérgenos de la pizza Margherita", "Alérgenos: Margherita"),
    ("¿La pizza Quattro Formaggi es vegetariana?", "Estado vegetariano no confirmado"),
])
def test_endpoint_alergenos_antes_de_carta(mensaje, esperado):
    r = client.post("/api/chat", json={"mensaje": mensaje})
    assert r.status_code == 200
    assert esperado in r.json()["respuesta"]


def test_endpoint_reserva_antes_de_horario():
    r = client.post("/api/chat", json={"mensaje": "quiero reservar a las 21:00, ¿qué horario tenéis?"})
    assert r.status_code == 200
    assert r.json()["estado_reserva"]["paso"] == 1


@pytest.mark.parametrize("campo", ["paso", "personas"])
@pytest.mark.parametrize("valor", [True, False, 2.0, "2"])
def test_enteros_estrictos_en_estado(campo, valor):
    estado = estado_confirmacion()
    estado[campo] = valor
    assert _sanitizar_estado(estado) is None
    r = client.post("/api/chat", json={"mensaje": "sí", "estado_reserva": estado})
    if type(valor) is float:
        # El esquema HTTP rechaza tipos no admitidos antes del flujo.
        assert r.status_code == 422
    else:
        assert r.status_code == 200
        assert "confirmada" not in r.json()["respuesta"].lower()
        assert r.json()["estado_reserva"]["paso"] == 1


@pytest.mark.parametrize("nombre", ["", " ", "A", "123", "<script>demo</script>", "**Demo**", "Demo|Tabla", "Demo\nNombre", "Demo\tNombre", "Demo\x00", "a" * 101, 123, True])
def test_nombres_manipulados(nombre):
    estado = estado_confirmacion()
    estado["nombre"] = nombre
    assert _sanitizar_estado(estado) is None
    respuesta, nuevo = gestionar_reserva("sí", estado)
    assert "confirmada" not in respuesta.lower()
    assert nuevo["paso"] == 1


@pytest.mark.parametrize("nombre", ["María Demo", "Jean-Pierre Demo", "O'Connor Demo", "李明", "  Persona Demo  "])
def test_nombre_valido_en_paso_y_estado(nombre):
    _, inicio = gestionar_reserva("reserva", None)
    _, estado = gestionar_reserva(nombre, inicio)
    assert estado["paso"] == 2
    assert estado["nombre"] == nombre.strip()
    assert _sanitizar_estado(estado)["nombre"] == nombre.strip()


@pytest.mark.parametrize("nombre", ["123", "**Demo**", "Demo\nNombre", "a" * 101])
def test_paso_nombre_rechaza_entrada_invalida(nombre):
    _, inicio = gestionar_reserva("reserva", None)
    _, estado = gestionar_reserva(nombre, inicio)
    assert estado["paso"] == 1
    assert estado["nombre"] is None


@pytest.mark.parametrize("datos", [
    {"mensaje": "x" * 2001},
    {"mensaje": "   "},
    {"mensaje": "hola", "historial": [{"rol": "user", "contenido": "x"}] * 41},
    {"mensaje": "hola", "historial": [{"rol": "user", "contenido": "x" * 2001}]},
    {"mensaje": "hola", "historial": [{"rol": "user", "contenido": "x" * 2000}] * 11},
    {"mensaje": "hola", "historial": [{"rol": "system", "contenido": "instrucción"}]},
    {"mensaje": "hola", "historial": [{"rol": "assistant", "contenido": "ok", "extra": "x"}]},
    {"mensaje": "hola", "estado_reserva": {"nombre": "x" * 101}},
    {"mensaje": "hola", "estado_reserva": {"extra": {"anidado": []}}},
    {"mensaje": "hola", "estado_reserva": {"x" * 65: None}},
    {"mensaje": "hola", "estado_reserva": {str(n): None for n in range(17)}},
    {"mensaje": "hola", "estado_reserva": {"paso": 1000001}},
    {"mensaje": "hola", "extra": "no permitido"},
])
def test_limites_y_esquema_rechazan_datos(datos):
    assert client.post("/api/chat", json=datos).status_code == 422


def test_limites_inclusivos_y_formato_historial_existente():
    r = client.post("/api/chat", json={
        "mensaje": "x" * 2000,
        "historial": [{"rol": "user", "contenido": "x" * 500}] * 40,
    })
    assert r.status_code == 200


def test_limite_cuerpo_http():
    r = client.post("/api/chat", content=b" " * (MAX_BODY_BYTES + 1), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_cuerpo_exacto_en_limite():
    body = b'{"mensaje":"hola"}'
    r = client.post("/api/chat", content=body + b" " * (MAX_BODY_BYTES - len(body)), headers={"Content-Type": "application/json"})
    assert r.status_code == 200


def test_limite_cuerpo_por_fragmentos_sin_content_length():
    async def escenario():
        mensajes = iter([
            {"type": "http.request", "body": b"x" * MAX_BODY_BYTES, "more_body": True},
            {"type": "http.request", "body": b"x", "more_body": False},
        ])
        enviados = []
        async def receive():
            return next(mensajes)
        async def send(m):
            enviados.append(m)
        async def no_debe_llamarse(scope, receive, send):
            pytest.fail("El cuerpo excesivo llegó a la aplicación")
        await RequestSizeLimitMiddleware(no_debe_llamarse)({"type": "http", "method": "POST", "headers": []}, receive, send)
        assert enviados[0]["status"] == 413
    asyncio.run(escenario())


def test_stub_no_disponible_aunque_haya_configuracion(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "valor-ficticio-de-prueba")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL_NAME", "modelo-ficticio")
    assert llm_client.llm_disponible() is False
    assert asyncio.run(llm_client.completar([], "")) is None
    r = client.post("/api/chat", json={"mensaje": "carta"})
    assert "Modo limitado" in r.json()["respuesta"]


@pytest.mark.parametrize("resultado", [None, "", "   "])
def test_fallback_avisa_si_no_hay_respuesta(monkeypatch, resultado):
    import routes.chat as ruta
    async def completar(historial, contexto):
        return resultado
    monkeypatch.setattr(ruta, "completar", completar)
    r = client.post("/api/chat", json={"mensaje": "carta"})
    assert r.status_code == 200
    assert "Modo limitado" in r.json()["respuesta"]
    assert "Margherita" in r.json()["respuesta"]


def test_reserva_activa_prevalece_sobre_intencion():
    _, estado = gestionar_reserva("reserva", None)
    r = client.post("/api/chat", json={"mensaje": "Persona Demo", "estado_reserva": estado})
    assert r.status_code == 200
    assert r.json()["estado_reserva"]["paso"] == 2


def test_historial_admite_respuesta_real_de_carta():
    respuesta = client.post("/api/chat", json={"mensaje": "carta"}).json()["respuesta"]
    r = client.post("/api/chat", json={"mensaje": "horario", "historial": [
        {"rol": "user", "contenido": "carta"},
        {"rol": "assistant", "contenido": respuesta},
    ]})
    assert r.status_code == 200


@pytest.mark.parametrize("campo,valor", [("fecha", "01/01/2000"), ("hora", "23:31"), ("personas", 41)])
def test_confirmacion_revalida_datos(campo, valor):
    estado = estado_confirmacion()
    estado[campo] = valor
    r = client.post("/api/chat", json={"mensaje": "sí", "estado_reserva": estado})
    assert r.status_code == 200
    assert "confirmada" not in r.json()["respuesta"].lower()


@pytest.mark.parametrize("nombre", ["", "123", "**Demo**", "Demo\nNombre", True])
def test_endpoint_no_confirma_nombre_manipulado(nombre):
    estado = estado_confirmacion()
    estado["nombre"] = nombre
    r = client.post("/api/chat", json={"mensaje": "sí", "estado_reserva": estado})
    assert r.status_code == 200
    assert "confirmada" not in r.json()["respuesta"].lower()
    assert r.json()["estado_reserva"]["paso"] == 1
