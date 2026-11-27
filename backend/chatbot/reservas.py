"""
reservas.py — Flujo de reserva conversacional de Fornaviva.

Diseño:
  - Los horarios se leen de horarios.json en tiempo de ejecución (fuente única).
  - _validar_hora() usa lógica post-medianoche (minutos desde mediodía del día
    de servicio), incluyendo el campo dia_siguiente del JSON.
  - La hora límite de reserva = cierre − minutos_antes_cierre (del JSON, por defecto 90).
  - _sanitizar_estado() aplica whitelist de campos y tipos antes de usar el estado
    enviado por el frontend.
  - El Paso 5 revalida fecha, hora y personas antes de confirmar.
"""

import json
import os
import unicodedata
from datetime import datetime, date

# ---------------------------------------------------------------------------
# Carga de horarios desde horarios.json (fuente única de verdad)
# ---------------------------------------------------------------------------

_RUTA_HORARIOS = os.path.join(os.path.dirname(__file__), "..", "data", "horarios.json")

_DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def _cargar_horarios() -> dict:
    """Carga horarios.json y devuelve su contenido. Lanza RuntimeError si falla."""
    try:
        with open(_RUTA_HORARIOS, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(f"No se pudo cargar horarios.json: {e}") from e


def _horario_del_dia(dia_nombre: str) -> dict | None:
    """
    Devuelve el dict del día (de horarios.json) o None si está cerrado.
    Raises RuntimeError si el día no existe en el JSON.
    """
    datos = _cargar_horarios()
    for entrada in datos["horarios"]:
        if entrada["dia"] == dia_nombre:
            return entrada if entrada["abierto"] else None
    raise RuntimeError(f"Día '{dia_nombre}' no encontrado en horarios.json")


def _minutos_desde_mediodia(hora_str: str, dia_siguiente: bool = False) -> int:
    """
    Convierte "HH:MM" a minutos desde las 12:00 del día de servicio.

    Las 12:00 = 0 min (base neutral que evita ambigüedad con medianoche).
    Las 20:00 = 480 min.
    Las 01:00 del día siguiente = 780 min (1440 − 12*60 + 60 = 780).

    Con dia_siguiente=True se suman 1440 minutos (24 h).
    """
    h, m = map(int, hora_str.split(":"))
    total = (h * 60 + m) - (12 * 60)   # relativo a mediodía
    if dia_siguiente:
        total += 1440
    return total


def _ultima_reserva(cierre_str: str, dia_siguiente: bool, margen: int) -> int:
    """Devuelve los minutos (desde mediodía) de la última reserva permitida."""
    return _minutos_desde_mediodia(cierre_str, dia_siguiente) - margen


def _fmt_hora(minutos_desde_mediodia: int) -> str:
    """Convierte minutos desde mediodía de vuelta a 'HH:MM'."""
    total = minutos_desde_mediodia + 12 * 60
    total %= 1440   # wrap a 24 h
    return f"{total // 60:02d}:{total % 60:02d}"


# ---------------------------------------------------------------------------
# Sanitización del estado recibido del frontend (no confiable)
# ---------------------------------------------------------------------------

_CAMPOS_PERMITIDOS = {"activa", "paso", "nombre", "fecha", "hora", "personas"}

# Términos ofensivos no permitidos como nombres de reserva.
# Lista inicial ampliable; se comprueban palabras completas.
_NOMBRES_OFENSIVOS = {
    # Insultos generales
    "gilipollas", "gilipuertas", "imbecil", "idiota",
    "estupido", "estupida", "subnormal", "retrasado",
    "retrasada", "tonto", "tonta", "tontaco", "tontaca",
    "tontolaba", "tontopollas", "memo", "mema",
    "capullo", "capulla", "capullazo", "capullaza",
    "cretino", "cretina", "necio", "necia",
    "inutil", "incompetente", "payaso", "payasa",
    "pringado", "pringada", "pardillo", "pardilla",
    "zoquete", "cenutrio", "cenutria", "tarado",
    "tarada", "anormal", "mongolo", "mongola",
    "mamon", "mamona", "cabron", "cabrona",
    "cabronazo", "cabronaza", "bastardo", "bastarda",
    "desgraciado", "desgraciada", "sinverguenza",
    "malnacido", "malnacida", "hijoputa",
    "hijaputa", "malparido", "malparida",

    # Vulgaridades
    "mierda", "puto", "puta", "putazo", "putaza",
    "joder", "cojones", "cojon", "cojonudo",
    "hostia", "ostia", "carajo", "carajos",
    "verga", "polla", "pollon", "pollas",
    "pene", "picha", "cipote", "rabo",
    "culo", "ojete", "ano", "chocho",
    "concha", "coño", "cona", "coñazo",
    "chichi", "potorro", "tetas", "teta",
    "tetazas", "follar", "follador", "folladora",
    "follada", "follado", "follon",
    "pajero", "pajera", "paja", "pajillero",
    "pajillera", "corrida", "corridas",
    "cagar", "cagada", "cagado", "cagada",
    "meada", "mear", "meon", "meona",
    "vomito", "vomitar",

    # Expresiones ofensivas habituales
    "hdp", "hpta", "hp", "ptm", "ctm",
    "hdlgp", "mrd", "mierdon", "mierdoso",
    "mierdosa", "asqueroso", "asquerosa",
    "repugnante", "cerdo", "cerda",
    "guarro", "guarra", "guarrindongo",
    "guarrindonga", "pervertido", "pervertida",
    "degenerado", "degenerada",

    # Insultos y vulgaridades de distintos países
    "boludo", "boluda", "pelotudo", "pelotuda",
    "forro", "forra", "forro", "forrada",
    "culiao", "culiada", "culiado", "culiadas",
    "weon", "weona", "huevon", "huevona",
    "huevudo", "huevuda", "pendejo", "pendeja",
    "pinche", "chingada", "chingado",
    "chingar", "chingon", "chingona",
    "culero", "culera", "mamaguevo",
    "mamagueva", "gonorrea", "maldito",
    "maldita", "careverga", "carepicha",
    "careculo", "carechimba", "caremondá",
    "caremonda", "soplapollas", "comemierda",
    "comepollas", "chupapollas", "chupamela",
    "chupapijas", "chupaverga",

    # Insultos en inglés
    "fuck", "fucker", "fucking", "motherfucker",
    "motherfucking", "shit", "bullshit", "asshole",
    "dumbass", "jackass", "bastard", "bitch",
    "bitches", "dick", "dickhead", "prick",
    "cunt", "twat", "wanker", "jerk",
    "moron", "retard", "retarded", "slut",
    "whore", "scumbag", "dipshit", "douchebag",
}


def _normalizar_palabra(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )


def _nombre_ofensivo(nombre: str) -> bool:
    palabras = _normalizar_palabra(nombre).replace("’", "'").split()
    return any(
        palabra.strip("'- .") in _NOMBRES_OFENSIVOS
        for palabra in palabras
    )

def _validar_nombre(nombre) -> str | None:
    """Nombre de demostración: 2–100 caracteres, sin controles ni marcado."""
    if not isinstance(nombre, str) or len(nombre) > 100:
        return None
    if any(unicodedata.category(c).startswith("C") or c in "\r\n\t" for c in nombre):
        return None
    nombre = nombre.strip()
    if len(nombre) < 2 or sum(c.isalpha() for c in nombre) < 2:
        return None
    if not all(c.isalpha() or unicodedata.category(c).startswith("M") or c in " '-’." for c in nombre):
        return None

    if _nombre_ofensivo(nombre):
        return None

    return nombre


def _sanitizar_estado(estado_raw) -> dict | None:
    """
    Valida y sanea el estado de reserva enviado por el cliente.

    Reglas:
      - Solo se aceptan los campos de _CAMPOS_PERMITIDOS.
      - activa debe ser bool.
      - paso debe ser entero 1–5.
      - nombre debe ser str o None.
      - fecha debe ser str "DD/MM/AAAA" convertible a date, o None.
      - hora debe ser str "HH:MM" o None.
      - personas debe ser int 1–40 o None.

    Devuelve el estado saneado o None si es inválido/irrecuperable.
    """
    if estado_raw is None:
        return None

    if not isinstance(estado_raw, dict):
        return None

    estado = {}

    # activa
    activa = estado_raw.get("activa")
    if not isinstance(activa, bool):
        return None
    estado["activa"] = activa

    # paso
    paso = estado_raw.get("paso")
    if type(paso) is not int or paso < 1 or paso > 5:
        return None
    estado["paso"] = paso

    # nombre
    nombre = estado_raw.get("nombre")
    if nombre is not None:
        nombre = _validar_nombre(nombre)
        if nombre is None:
            return None
    estado["nombre"] = nombre

    # fecha — aceptar str "DD/MM/AAAA", objeto date, o None
    fecha_raw = estado_raw.get("fecha")
    if fecha_raw is None:
        estado["fecha"] = None
    elif isinstance(fecha_raw, date):
        estado["fecha"] = fecha_raw
    elif isinstance(fecha_raw, str):
        try:
            estado["fecha"] = datetime.strptime(fecha_raw, "%d/%m/%Y").date()
        except ValueError:
            return None  # formato inválido → estado manipulado
    else:
        return None

    # hora
    hora = estado_raw.get("hora")
    if hora is not None:
        if not isinstance(hora, str):
            return None
        try:
            datetime.strptime(hora, "%H:%M")
        except ValueError:
            return None
    estado["hora"] = hora

    # personas
    personas = estado_raw.get("personas")
    if personas is not None:
        if type(personas) is not int or personas < 1 or personas > 40:
            return None
    estado["personas"] = personas

    # Coherencia: si paso > 1, los campos previos no pueden ser None
    if paso >= 2 and estado["nombre"] is None:
        return None
    if paso >= 3 and estado["fecha"] is None:
        return None
    if paso >= 4 and estado["hora"] is None:
        return None
    if paso == 5 and estado["personas"] is None:
        return None

    return estado


# ---------------------------------------------------------------------------
# Validaciones individuales
# ---------------------------------------------------------------------------

def _validar_fecha(texto: str):
    """
    Valida DD/MM/AAAA. Devuelve date si es válida o str de error.
    """
    try:
        fecha = datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError:
        return "Por favor, escribe la fecha en formato DD/MM/AAAA. Por ejemplo: 25/12/2025"

    if fecha < date.today():
        return "Esa fecha ya ha pasado. Por favor, elige una fecha futura."

    dia_nombre = _DIAS_SEMANA[fecha.weekday()]
    entrada = _horario_del_dia(dia_nombre)
    if entrada is None:
        return f"Lo sentimos, los {dia_nombre} estamos cerrados. Por favor, elige otro día."

    return fecha


def _validar_hora(texto: str, fecha: date):
    """
    Valida HH:MM y comprueba que caiga dentro del horario del día
    y antes del límite de reserva (minutos_antes_cierre).

    Lógica post-medianoche: todo se convierte a minutos desde mediodía
    del día de servicio, por lo que 01:00 con dia_siguiente=True es > 20:00.
    """
    try:
        hora_obj = datetime.strptime(texto.strip(), "%H:%M")
    except ValueError:
        return "Por favor, escribe la hora en formato HH:MM. Por ejemplo: 14:00 o 21:30"
    
    if fecha == date.today():
        ahora = datetime.now().time()

        if hora_obj.time() <= ahora:
            return "Esa hora ya ha pasado. Por favor, elige una hora futura."

    hora_mins = _minutos_desde_mediodia(texto.strip())

    datos = _cargar_horarios()
    margen = datos.get("minutos_antes_cierre", 90)

    dia_nombre = _DIAS_SEMANA[fecha.weekday()]
    entrada = _horario_del_dia(dia_nombre)
    if entrada is None:
        return f"Los {dia_nombre} estamos cerrados."

    med = entrada.get("turno_mediodia")
    noch = entrada.get("turno_noche")

    def en_turno(turno) -> bool:
        # La apertura es siempre en el día de servicio (dia_siguiente=False).
        # El campo dia_siguiente solo aplica al cierre.
        ap_m = _minutos_desde_mediodia(turno["apertura"], False)
        limite_m = _ultima_reserva(turno["cierre"], turno.get("dia_siguiente", False), margen)
        return ap_m <= hora_mins <= limite_m

    en_med = med is not None and en_turno(med)
    en_noch = noch is not None and en_turno(noch)

    if en_med or en_noch:
        return texto.strip()   # válida

    # Construir mensaje de error con horas límite exactas
    partes = []
    if med:
        lim_med = _fmt_hora(_ultima_reserva(med["cierre"], med.get("dia_siguiente", False), margen))
        partes.append(f"mediodía de {med['apertura']} a {lim_med} (última reserva)")
    if noch:
        lim_noch = _fmt_hora(_ultima_reserva(noch["cierre"], noch.get("dia_siguiente", False), margen))
        partes.append(f"noche de {noch['apertura']} a {lim_noch} (última reserva)")

    return (
        f"Esa hora no está disponible para reservas.\n"
        f"Los {dia_nombre} aceptamos reservas: {' | '.join(partes)}."
    )


def _validar_personas(texto: str):
    """Valida número de personas 1–40. Devuelve int o str de error."""
    try:
        n = int(texto.strip())
    except ValueError:
        return "Por favor, escribe solo el número de personas. Por ejemplo: 2"

    if n < 1:
        return "El número de personas debe ser al menos 1."
    if n > 40:
        return "Para grupos de más de 40 personas, contáctanos directamente al 910 123 456."
    return n


def _construir_fecha_bonita(fecha: date) -> str:
    dias = {
        "Monday": "lunes", "Tuesday": "martes", "Wednesday": "miércoles",
        "Thursday": "jueves", "Friday": "viernes", "Saturday": "sábado", "Sunday": "domingo",
    }
    meses = {
        "January": "enero", "February": "febrero", "March": "marzo",
        "April": "abril", "May": "mayo", "June": "junio",
        "July": "julio", "August": "agosto", "September": "septiembre",
        "October": "octubre", "November": "noviembre", "December": "diciembre",
    }
    dia_es = dias.get(fecha.strftime("%A"), fecha.strftime("%A"))
    mes_es = meses.get(fecha.strftime("%B"), fecha.strftime("%B"))
    return f"{dia_es} {fecha.day} de {mes_es} de {fecha.year}"


# ---------------------------------------------------------------------------
# Estado inicial
# ---------------------------------------------------------------------------

def _estado_inicial() -> dict:
    return {
        "activa": True,
        "paso": 1,
        "nombre": None,
        "fecha": None,
        "hora": None,
        "personas": None,
    }


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def gestionar_reserva(texto: str, estado_raw) -> tuple[str, dict]:
    """
    Gestiona el flujo de reserva paso a paso.

    Parámetros:
        texto      — mensaje del usuario.
        estado_raw — estado enviado por el frontend (no confiable). Puede ser None
                     para iniciar una nueva reserva, o un dict que se sanitizará.

    Devuelve:
        (respuesta: str, nuevo_estado: dict)
        Cuando la reserva termina o se cancela, nuevo_estado["activa"] = False.
    """
    # --- Sanitizar estado del cliente ---
    if estado_raw is None:
        estado = None
    else:
        estado = _sanitizar_estado(estado_raw)
        if estado is None:
            # Estado inválido o manipulado → reiniciamos silenciosamente
            return (
                "Ha ocurrido un problema con el estado de tu reserva. "
                "Vamos a empezar de nuevo.\n\n"
                "📅 ¡Vamos a hacer tu reserva!\n\n"
                "Puedes escribir **cancelar** en cualquier momento para salir.\n\n"
                "**Paso 1 de 5:** ¿Cuál es tu nombre?",
                _estado_inicial(),
            )

    # --- Nueva reserva ---
    if estado is None:
        return (
            "📅 ¡Vamos a hacer tu reserva!\n\n"
            "⚠️ _Recuerda que las reservas en Fornaviva son una **simulación** "
            "y no tienen validez real._\n\n"
            "Puedes escribir **cancelar** en cualquier momento para salir.\n\n"
            "**Paso 1 de 5:** ¿Cuál es tu nombre?",
            _estado_inicial(),
        )

    # --- Cancelación en cualquier momento ---
    if "cancelar" in texto.lower():
        return "Reserva cancelada. ¡Hasta pronto! 👋 ¿Puedo ayudarte en algo más?", {"activa": False}

    paso = estado["paso"]

    # ----------------------------------------------------------
    # PASO 1 — Nombre
    # ----------------------------------------------------------
    if paso == 1:
        nombre = _validar_nombre(texto)

        if nombre is None:
            if _nombre_ofensivo(texto):
                return (
                    "Ese nombre no es válido para la reserva. "
                    "Por favor, introduce otro nombre.",
                    estado,
                )

            return (
                "Por favor, escribe un nombre válido de 2 a 100 caracteres, "
                "sin números ni marcado.",
                estado,
            )

        estado["nombre"] = nombre
        estado["paso"] = 2
        return (
            f"Encantado/a, **{nombre}**. 😊\n\n"
            "**Paso 2 de 5:** ¿Qué día quieres venir?\n"
            "Escribe la fecha en formato **DD/MM/AAAA**.\n"
            "_Recuerda que los lunes estamos cerrados._"
        ), estado

    # ----------------------------------------------------------
    # PASO 2 — Fecha
    # ----------------------------------------------------------
    if paso == 2:
        resultado = _validar_fecha(texto)
        if isinstance(resultado, str):
            return f"⚠️ {resultado}", estado

        estado["fecha"] = resultado
        estado["paso"] = 3

        dia_nombre = _DIAS_SEMANA[resultado.weekday()]
        entrada = _horario_del_dia(dia_nombre)
        med = entrada["turno_mediodia"]
        noch = entrada["turno_noche"]
        datos = _cargar_horarios()
        margen = datos.get("minutos_antes_cierre", 90)

        lim_med = _fmt_hora(_ultima_reserva(med["cierre"], med.get("dia_siguiente", False), margen))
        lim_noch = _fmt_hora(_ultima_reserva(noch["cierre"], noch.get("dia_siguiente", False), margen))

        return (
            f"Perfecto, el **{dia_nombre} {resultado.strftime('%d/%m/%Y')}**. ✅\n\n"
            "**Paso 3 de 5:** ¿A qué hora queréis venir?\n"
            f"Ese día aceptamos reservas de **{med['apertura']}** a **{lim_med}** (mediodía) "
            f"y de **{noch['apertura']}** a **{lim_noch}** (noche).\n"
            "Escribe la hora en formato **HH:MM**."
        ), estado

    # ----------------------------------------------------------
    # PASO 3 — Hora
    # ----------------------------------------------------------
    if paso == 3:
        resultado = _validar_hora(texto, estado["fecha"])
        if not resultado[0].isdigit():
            return f"⚠️ {resultado}", estado

        estado["hora"] = resultado
        estado["paso"] = 4
        return (
            f"A las **{resultado}**. ✅\n\n"
            "**Paso 4 de 5:** ¿Cuántas personas sois?"
        ), estado

    # ----------------------------------------------------------
    # PASO 4 — Personas
    # ----------------------------------------------------------
    if paso == 4:
        resultado = _validar_personas(texto)
        if isinstance(resultado, str):
            return f"⚠️ {resultado}", estado

        estado["personas"] = resultado
        estado["paso"] = 5

        fecha_bonita = _construir_fecha_bonita(estado["fecha"])
        resumen = (
            "📋 **Resumen de tu reserva simulada:**\n\n"
            f" 👤 Nombre: {estado['nombre']} \n"
            f" 📅 Fecha: {fecha_bonita} \n"
            f" 🕐 Hora: {estado['hora']} \n"
            f" 👥 Personas: {estado['personas']} \n\n"
            "⚠️ _Esta es una reserva simulada. No tiene validez real._\n\n"
            "**¿Deseas confirmar esta reserva? (Sí/No)**"
        )
        return resumen, estado

    # ----------------------------------------------------------
    # PASO 5 — Confirmación + revalidación completa en backend
    # ----------------------------------------------------------
    if paso == 5:
        respuesta_usuario = texto.strip().lower()

        if respuesta_usuario not in ("sí", "si", "s", "yes", "sí.", "no", "n"):
            return (
                "⚠️ Por favor, responde **Sí** para confirmar la reserva o **No** para cancelarla."
            ), estado

        if respuesta_usuario in ("no", "n"):
            estado["activa"] = False
            return "Reserva cancelada. ¡Hasta pronto! 👋 ¿Puedo ayudarte en algo más?", estado

        # Revalidación completa antes de confirmar (el backend no confía solo en el estado)
        err_fecha = _validar_fecha(estado["fecha"].strftime("%d/%m/%Y"))
        if isinstance(err_fecha, str):
            estado["activa"] = False
            return f"⚠️ No se ha podido confirmar la reserva: {err_fecha}", estado

        err_hora = _validar_hora(estado["hora"], estado["fecha"])
        if not err_hora[0].isdigit():
            estado["activa"] = False
            return f"⚠️ No se ha podido confirmar la reserva: {err_hora}", estado

        err_personas = _validar_personas(str(estado["personas"]))
        if isinstance(err_personas, str):
            estado["activa"] = False
            return f"⚠️ No se ha podido confirmar la reserva: {err_personas}", estado

        # Todo OK → confirmar
        fecha_bonita = _construir_fecha_bonita(estado["fecha"])
        confirmacion = (
    		"✅ **¡Reserva simulada completada!** 🍕\n\n"
    		f" 👤 Nombre: {estado['nombre']} \n"
    		f" 📅 Fecha: {fecha_bonita} \n"
    		f" 🕐 Hora: {estado['hora']} \n"
    		f" 👥 Personas: {estado['personas']} \n\n"
    		"En una reserva real, la mesa se mantendría durante 15 minutos.\n\n"
    		"⚠️ _Recuerda que esta demostración no genera ninguna reserva._"
	)
        estado["activa"] = False
        return confirmacion, estado

    return (
        "Ha ocurrido un error inesperado. Por favor, escribe 'reserva' para intentarlo de nuevo.",
        {"activa": False},
    )
