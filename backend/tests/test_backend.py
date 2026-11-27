"""
test_backend.py — Pruebas automatizadas del backend de Fornaviva.

Cubre:
  - Endpoints GET (menu, horarios, alergenos, faqs)
  - Endpoint POST /api/chat (modo fallback, intenciones, flujo de reserva)
  - Casos límite horarios post-medianoche
  - Sanitización de estado manipulado
  - Revalidación en Paso 5
  - Confirmación explícita obligatoria
"""

import sys
import os
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

# Asegurar que backend/ está en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from chatbot.reservas import (
    _sanitizar_estado,
    _validar_fecha,
    _validar_hora,
    _validar_personas,
    _minutos_desde_mediodia,
    _ultima_reserva,
    _fmt_hora,
    gestionar_reserva,
)

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fecha_futura(dias=7, dia_semana=None) -> str:
    """Devuelve una fecha futura en formato DD/MM/AAAA. Opcionalmente en un día concreto."""
    d = date.today() + timedelta(days=dias)
    if dia_semana is not None:
        # Ajustar al próximo día de la semana pedido (0=lunes)
        offset = (dia_semana - d.weekday()) % 7
        if offset == 0:
            offset = 7
        d += timedelta(days=offset)
    return d.strftime("%d/%m/%Y")

def proximo_martes() -> str:
    return fecha_futura(dia_semana=1)   # 1 = martes

def proximo_viernes() -> str:
    return fecha_futura(dia_semana=4)   # 4 = viernes

def proximo_lunes() -> str:
    return fecha_futura(dia_semana=0)   # 0 = lunes (cerrado)

def fecha_pasada() -> str:
    d = date.today() - timedelta(days=1)
    return d.strftime("%d/%m/%Y")


# ===========================================================================
# GET /api/menu
# ===========================================================================

class TestGetMenu:
    def test_devuelve_200(self):
        r = client.get("/api/menu")
        assert r.status_code == 200

    def test_tiene_carta(self):
        r = client.get("/api/menu")
        data = r.json()
        assert "carta" in data

    def test_tiene_18_platos(self):
        r = client.get("/api/menu")
        total = sum(len(c["platos"]) for c in r.json()["carta"])
        assert total == 18

    def test_todos_tienen_id(self):
        r = client.get("/api/menu")
        for cat in r.json()["carta"]:
            for plato in cat["platos"]:
                assert "id" in plato, f"Plato sin id: {plato['nombre']}"

    def test_ids_unicos(self):
        r = client.get("/api/menu")
        ids = [p["id"] for c in r.json()["carta"] for p in c["platos"]]
        assert len(ids) == len(set(ids))

    def test_nombre_restaurante(self):
        r = client.get("/api/menu")
        assert r.json()["nombre_restaurante"] == "Fornaviva"


# ===========================================================================
# GET /api/horarios
# ===========================================================================

class TestGetHorarios:
    def test_devuelve_200(self):
        assert client.get("/api/horarios").status_code == 200

    def test_tiene_7_dias(self):
        r = client.get("/api/horarios")
        assert len(r.json()["horarios"]) == 7

    def test_lunes_cerrado(self):
        r = client.get("/api/horarios")
        lunes = next(d for d in r.json()["horarios"] if d["dia"] == "Lunes")
        assert lunes["abierto"] is False

    def test_viernes_dia_siguiente(self):
        r = client.get("/api/horarios")
        viernes = next(d for d in r.json()["horarios"] if d["dia"] == "Viernes")
        assert viernes["turno_noche"]["dia_siguiente"] is True
        assert viernes["turno_noche"]["cierre"] == "01:00"

    def test_minutos_antes_cierre(self):
        r = client.get("/api/horarios")
        assert r.json()["minutos_antes_cierre"] == 90


# ===========================================================================
# GET /api/alergenos
# ===========================================================================

class TestGetAlergenos:
    def test_devuelve_200(self):
        assert client.get("/api/alergenos").status_code == 200

    def test_tiene_18_platos(self):
        r = client.get("/api/alergenos")
        assert len(r.json()["platos"]) == 18

    def test_piz07_alergenos_null(self):
        r = client.get("/api/alergenos")
        piz07 = next(p for p in r.json()["platos"] if p["id"] == "piz-07")
        assert piz07["alergenos"] is None

    def test_platos_vegetariano_null(self):
        r = client.get("/api/alergenos")
        nulos = [p["id"] for p in r.json()["platos"] if p["vegetariano"] is None]
        assert set(nulos) == {"piz-03", "piz-06", "piz-07", "dol-02"}

    def test_ids_coinciden_con_menu(self):
        ids_menu = {
            p["id"]
            for c in client.get("/api/menu").json()["carta"]
            for p in c["platos"]
        }
        ids_alerg = {p["id"] for p in client.get("/api/alergenos").json()["platos"]}
        assert ids_menu == ids_alerg


# ===========================================================================
# GET /api/faqs
# ===========================================================================

class TestGetFaqs:
    def test_devuelve_200(self):
        assert client.get("/api/faqs").status_code == 200

    def test_tiene_10_preguntas(self):
        r = client.get("/api/faqs")
        assert len(r.json()["preguntas_frecuentes"]) == 10

    def test_contiene_telefono_canonico(self):
        r = client.get("/api/faqs")
        texto = str(r.json())
        assert "910 123 456" in texto

    def test_sin_la_buena_mesa(self):
        r = client.get("/api/faqs")
        assert "La Buena Mesa" not in str(r.json())


# ===========================================================================
# POST /api/chat — modo fallback y routing
# ===========================================================================

class TestChatFallback:
    def _post(self, mensaje, estado=None):
        return client.post("/api/chat", json={
            "mensaje": mensaje,
            "historial": [],
            "estado_reserva": estado,
        })

    def test_hola_devuelve_200(self):
        assert self._post("hola").status_code == 200

    def test_respuesta_tiene_campo_respuesta(self):
        r = self._post("hola")
        assert "respuesta" in r.json()

    def test_mensaje_vacio_devuelve_422(self):
        r = client.post("/api/chat", json={"mensaje": "", "historial": []})
        assert r.status_code == 422

    def test_sin_campo_mensaje_devuelve_422(self):
        r = client.post("/api/chat", json={"historial": []})
        assert r.status_code == 422

    def test_aviso_modo_limitado_presente(self):
        r = self._post("qué pizzas tenéis")
        assert "Modo limitado" in r.json()["respuesta"]

    def test_intencion_menu(self):
        r = self._post("qué pizzas tenéis")
        assert "Fornaviva" in r.json()["respuesta"]
        assert "Margherita" in r.json()["respuesta"]

    def test_intencion_horarios(self):
        r = self._post("a qué hora cerráis")
        resp = r.json()["respuesta"]
        assert "Lunes" in resp or "Martes" in resp

    def test_intencion_alergenos_sin_plato(self):
        r = self._post("información sobre alérgenos")
        assert "vegetariano" in r.json()["respuesta"].lower() or "alérgeno" in r.json()["respuesta"].lower()

    def test_intencion_faq(self):
        # Usamos una consulta sin tildes para evitar problemas de encoding en el terminal de test
        r = self._post("donde estais ubicados")
        resp = r.json()["respuesta"]
        # Puede devolver la respuesta directa o la lista de FAQs; en ambos casos
        # debe contener información de Fornaviva (dirección o lista de preguntas)
        assert "Via della Fornace" in resp or "Fornaviva" in resp

    def test_estado_reserva_null_en_respuesta_no_reserva(self):
        r = self._post("qué pizzas tenéis")
        assert r.json()["estado_reserva"] is None


# ===========================================================================
# POST /api/chat — flujo de reserva completo
# ===========================================================================

class TestFlujoReserva:
    def _post(self, mensaje, estado=None):
        return client.post("/api/chat", json={
            "mensaje": mensaje,
            "historial": [],
            "estado_reserva": estado,
        })

    def test_iniciar_reserva(self):
        r = self._post("quiero reservar una mesa")
        data = r.json()
        assert data["estado_reserva"] is not None
        assert data["estado_reserva"]["activa"] is True
        assert data["estado_reserva"]["paso"] == 1
        assert "simulación" in data["respuesta"].lower() or "simulada" in data["respuesta"].lower()

    def test_paso1_nombre(self):
        # Iniciar
        r1 = self._post("quiero reservar")
        estado = r1.json()["estado_reserva"]
        # Enviar nombre
        r2 = self._post("María García", estado)
        data = r2.json()
        assert data["estado_reserva"]["paso"] == 2
        assert data["estado_reserva"]["nombre"] == "María García"

    def test_paso2_fecha_valida(self):
        r1 = self._post("quiero reservar")
        estado = r1.json()["estado_reserva"]
        r2 = self._post("María", estado)
        estado = r2.json()["estado_reserva"]
        r3 = self._post(proximo_martes(), estado)
        data = r3.json()
        assert data["estado_reserva"]["paso"] == 3

    def test_paso2_lunes_rechazado(self):
        r1 = self._post("quiero reservar")
        estado = r1.json()["estado_reserva"]
        r2 = self._post("María", estado)
        estado = r2.json()["estado_reserva"]
        r3 = self._post(proximo_lunes(), estado)
        data = r3.json()
        assert data["estado_reserva"]["paso"] == 2   # sigue en paso 2
        assert "cerrado" in data["respuesta"].lower()

    def test_paso2_fecha_pasada_rechazada(self):
        r1 = self._post("quiero reservar")
        estado = r1.json()["estado_reserva"]
        r2 = self._post("María", estado)
        estado = r2.json()["estado_reserva"]
        r3 = self._post(fecha_pasada(), estado)
        data = r3.json()
        assert data["estado_reserva"]["paso"] == 2
        assert "pasado" in data["respuesta"].lower() or "pasada" in data["respuesta"].lower()

    def test_paso3_hora_valida_mediodia(self):
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("María", e).json()["estado_reserva"]
        e = self._post(proximo_martes(), e).json()["estado_reserva"]
        r = self._post("14:00", e)
        data = r.json()
        assert data["estado_reserva"]["paso"] == 4

    def test_paso3_hora_limite_viernes_noche_acepta_2330(self):
        """Viernes 23:30 debe ser aceptado (es exactamente el límite)."""
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Carlos", e).json()["estado_reserva"]
        e = self._post(proximo_viernes(), e).json()["estado_reserva"]
        r = self._post("23:30", e)
        data = r.json()
        assert data["estado_reserva"]["paso"] == 4, (
            f"Se esperaba paso 4, got {data['estado_reserva']['paso']}. "
            f"Respuesta: {data['respuesta']}"
        )

    def test_paso3_hora_limite_viernes_noche_rechaza_2331(self):
        """Viernes 23:31 debe ser rechazado (supera el límite de 90 min antes de 01:00)."""
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Carlos", e).json()["estado_reserva"]
        e = self._post(proximo_viernes(), e).json()["estado_reserva"]
        r = self._post("23:31", e)
        data = r.json()
        assert data["estado_reserva"]["paso"] == 3, (
            f"Se esperaba paso 3 (rechazo), got {data['estado_reserva']['paso']}. "
            f"Respuesta: {data['respuesta']}"
        )
        assert "23:30" in data["respuesta"]   # el bot informa de la hora límite

    def test_paso3_sabado_0030_rechazado(self):
        """Sábado 00:30 no es un turno válido (es madrugada del día natural siguiente)."""
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Ana", e).json()["estado_reserva"]
        # Usamos un sábado
        sab = fecha_futura(dia_semana=5)
        e = self._post(sab, e).json()["estado_reserva"]
        r = self._post("00:30", e)
        data = r.json()
        assert data["estado_reserva"]["paso"] == 3
        assert "disponible" in data["respuesta"].lower() or "horario" in data["respuesta"].lower()

    def test_paso4_personas_validas(self):
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Juan", e).json()["estado_reserva"]
        e = self._post(proximo_martes(), e).json()["estado_reserva"]
        e = self._post("14:00", e).json()["estado_reserva"]
        r = self._post("4", e)
        data = r.json()
        assert data["estado_reserva"]["paso"] == 5
        assert data["estado_reserva"]["personas"] == 4

    def test_paso4_personas_mayor_40_rechazado(self):
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Juan", e).json()["estado_reserva"]
        e = self._post(proximo_martes(), e).json()["estado_reserva"]
        e = self._post("14:00", e).json()["estado_reserva"]
        r = self._post("50", e)
        data = r.json()
        assert data["estado_reserva"]["paso"] == 4
        assert "910 123 456" in data["respuesta"]   # teléfono canónico de Fornaviva

    def test_paso5_confirmacion_si(self):
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Laura", e).json()["estado_reserva"]
        e = self._post(proximo_martes(), e).json()["estado_reserva"]
        e = self._post("14:00", e).json()["estado_reserva"]
        e = self._post("2", e).json()["estado_reserva"]

        r = self._post("sí", e)
        data = r.json()
        assert data["estado_reserva"]["activa"] is False
        assert "reserva simulada completada" in data["respuesta"].lower()
        assert "simulada" in data["respuesta"].lower() or "simulación" in data["respuesta"].lower()

    def test_paso5_confirmacion_no(self):
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Pedro", e).json()["estado_reserva"]
        e = self._post(proximo_martes(), e).json()["estado_reserva"]
        e = self._post("20:00", e).json()["estado_reserva"]
        e = self._post("3", e).json()["estado_reserva"]
        r = self._post("no", e)
        data = r.json()
        assert data["estado_reserva"]["activa"] is False
        assert "cancelada" in data["respuesta"].lower()

    def test_paso5_sin_confirmacion_explicita_repite(self):
        """Respuesta ambigua en paso 5 no confirma la reserva."""
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Ana", e).json()["estado_reserva"]
        e = self._post(proximo_martes(), e).json()["estado_reserva"]
        e = self._post("14:00", e).json()["estado_reserva"]
        e = self._post("2", e).json()["estado_reserva"]
        r = self._post("quizás", e)
        data = r.json()
        assert data["estado_reserva"]["paso"] == 5   # sigue en paso 5
        assert data["estado_reserva"]["activa"] is True

    def test_cancelar_en_cualquier_paso(self):
        r1 = self._post("quiero reservar")
        e = r1.json()["estado_reserva"]
        e = self._post("Ana", e).json()["estado_reserva"]
        r = self._post("cancelar", e)
        data = r.json()
        assert data["estado_reserva"]["activa"] is False


# ===========================================================================
# Sanitización de estado manipulado
# ===========================================================================

class TestSanitizacion:
    def test_estado_none_devuelve_none(self):
        assert _sanitizar_estado(None) is None

    def test_estado_no_dict_devuelve_none(self):
        assert _sanitizar_estado("hack") is None
        assert _sanitizar_estado([1, 2, 3]) is None
        assert _sanitizar_estado(42) is None

    def test_campo_extra_ignorado(self):
        estado = {
            "activa": True, "paso": 1,
            "nombre": None, "fecha": None, "hora": None, "personas": None,
            "campo_inyectado": "malicioso",
        }
        resultado = _sanitizar_estado(estado)
        assert resultado is not None
        assert "campo_inyectado" not in resultado

    def test_paso_fuera_de_rango_devuelve_none(self):
        for paso in (0, 6, -1, 100):
            estado = {"activa": True, "paso": paso, "nombre": None,
                      "fecha": None, "hora": None, "personas": None}
            assert _sanitizar_estado(estado) is None, f"paso={paso} debería devolver None"

    def test_paso5_sin_datos_previos_devuelve_none(self):
        """Saltar al paso 5 sin haber rellenado los anteriores debe rechazarse."""
        estado = {
            "activa": True, "paso": 5,
            "nombre": None, "fecha": None, "hora": None, "personas": None,
        }
        assert _sanitizar_estado(estado) is None

    def test_estado_manipulado_via_endpoint(self):
        """Enviar paso=5 con datos vacíos directamente al endpoint debe reiniciar."""
        r = client.post("/api/chat", json={
            "mensaje": "sí",
            "historial": [],
            "estado_reserva": {
                "activa": True, "paso": 5,
                "nombre": None, "fecha": None, "hora": None, "personas": None,
            },
        })
        data = r.json()
        assert r.status_code == 200
        # Debe reiniciar o devolver error, nunca confirmar una reserva vacía
        assert "confirmada" not in data["respuesta"].lower()

    def test_fecha_invalida_en_estado_devuelve_none(self):
        estado = {
            "activa": True, "paso": 3,
            "nombre": "Hack", "fecha": "no-es-fecha", "hora": None, "personas": None,
        }
        assert _sanitizar_estado(estado) is None

    def test_hora_invalida_en_estado_devuelve_none(self):
        estado = {
            "activa": True, "paso": 4,
            "nombre": "Hack", "fecha": "25/12/2026", "hora": "99:99", "personas": None,
        }
        assert _sanitizar_estado(estado) is None

    def test_personas_fuera_de_rango_devuelve_none(self):
        estado = {
            "activa": True, "paso": 5,
            "nombre": "Hack", "fecha": "25/12/2026", "hora": "14:00", "personas": 999,
        }
        assert _sanitizar_estado(estado) is None


# ===========================================================================
# Lógica de minutos post-medianoche
# ===========================================================================

class TestLogicaPostMedianoche:
    def test_mediodia_es_cero(self):
        assert _minutos_desde_mediodia("12:00") == 0

    def test_2000_es_480(self):
        assert _minutos_desde_mediodia("20:00") == 480

    def test_0100_dia_siguiente_es_780(self):
        # 01:00 + 1440 - 720 = 780
        assert _minutos_desde_mediodia("01:00", dia_siguiente=True) == 780

    def test_ultima_reserva_viernes_noche(self):
        # cierre 01:00 dia_siguiente, margen 90 → 780 - 90 = 690
        assert _ultima_reserva("01:00", True, 90) == 690

    def test_fmt_hora_690(self):
        # 690 + 720 = 1410 → 23:30
        assert _fmt_hora(690) == "23:30"

    def test_fmt_hora_480(self):
        # 480 + 720 = 1200 → 20:00
        assert _fmt_hora(480) == "20:00"

    def test_ultima_reserva_martes_noche(self):
        # cierre 23:30, no dia_siguiente, margen 90
        # _minutos_desde_mediodia("23:30") = 23*60+30 - 720 = 690
        # 690 - 90 = 600 → 22:00
        lim = _ultima_reserva("23:30", False, 90)
        assert _fmt_hora(lim) == "22:00"

    def test_validar_hora_viernes_2330_acepta(self):
        fecha_v = date.today()
        # Buscar próximo viernes
        while fecha_v.weekday() != 4:
            fecha_v += timedelta(days=1)
        resultado = _validar_hora("23:30", fecha_v)
        assert resultado == "23:30", f"Esperado '23:30', got '{resultado}'"

    def test_validar_hora_viernes_2331_rechaza(self):
        fecha_v = date.today()
        while fecha_v.weekday() != 4:
            fecha_v += timedelta(days=1)
        resultado = _validar_hora("23:31", fecha_v)
        assert isinstance(resultado, str) and resultado != "23:31"
        assert "23:30" in resultado   # el mensaje informa del límite

    def test_validar_hora_sabado_0030_rechaza(self):
        fecha_s = date.today()
        while fecha_s.weekday() != 5:
            fecha_s += timedelta(days=1)
        resultado = _validar_hora("00:30", fecha_s)
        assert isinstance(resultado, str) and resultado != "00:30"


def test_identidad_publica_fornaviva():
    """La identidad actual es coherente en metadatos, datos y respuestas."""
    assert client.get("/").json()["proyecto"] == "Fornaviva"
    assert client.get("/openapi.json").json()["info"]["title"] == "Fornaviva API"
    for ruta in ("/api/menu", "/api/horarios", "/api/alergenos", "/api/faqs"):
        r = client.get(ruta)
        assert r.status_code == 200
        assert "Forno Rosso" not in r.text
        assert "fornorosso" not in r.text
        assert "La Buena Mesa" not in r.text
    assert "info@fornaviva.example" in client.get("/api/faqs").text
    for mensaje in ("carta", "horario", "quiero reservar"):
        r = client.post("/api/chat", json={"mensaje": mensaje})
        assert r.status_code == 200
        assert "Fornaviva" in r.json()["respuesta"]
