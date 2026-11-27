[English](ESTABILIZACION.md) | **Español**

> Registro de la fase de estabilización anterior. Sus resultados (138 pruebas)
> se conservan como referencia histórica. El adaptador provisional descrito aquí
> ha sido sustituido por la integración opcional documentada en [GEMINI.md](GEMINI.es.md).

# Verificación y estabilización del backend

Se mantiene la API de Fornaviva y las reservas simuladas. No se integra
ningún proveedor LLM en esta fase. El adaptador provisional informa siempre
que no hay proveedor disponible; cada respuesta estructurada de fallback
incluye el aviso de modo limitado, aunque exista una clave configurada.

## Validación

- Intenciones: reserva, alérgenos, horarios, carta y FAQ, en ese orden.
  Las palabras clave se reconocen por límites de palabra.
- Una reserva activa conserva su flujo antes de clasificar intenciones nuevas.
- Paso y personas requieren enteros reales; los booleanos no se aceptan.
- Nombre: 2–100 caracteres y al menos dos letras. Se permiten letras Unicode,
  marcas diacríticas, espacios, apóstrofes, guiones y puntos. Se rechazan
  números, controles y marcado. La validación se aplica también al estado.
- Los estados activos inválidos reinician el flujo, sin confirmar la reserva.
- La confirmación sigue revalidando fecha, hora y número de personas.

## Límites HTTP

- Cuerpo POST: 128 KiB reales, también con transferencia fragmentada.
  Exceso: HTTP 413 antes de procesar JSON.
- Mensaje: 1–2000 caracteres, sin aceptar solo espacios.
- Historial: hasta 40 mensajes, roles `user`/`assistant`, contenido de
  1–2000 caracteres y un máximo acumulado de 20000 caracteres.
- Estado: hasta 16 campos; claves de hasta 64 caracteres; valores escalares
  de hasta 100 caracteres o enteros entre -1000000 y 1000000. Los campos
  de negocio se validan después con sus rangos específicos.
- Los campos desconocidos de petición/historial se rechazan. Los campos
  extra escalares del estado se descartan como antes.
- Esquema o límites de campos incorrectos: HTTP 422.

El cliente debe recortar el historial más antiguo antes de superar los límites.
No hay almacenamiento de reservas ni de historial en el servidor.

## Pruebas en PowerShell (desde la raíz)

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
$env:PYTHON_DOTENV_DISABLED = '1'
$env:LLM_API_KEY = ''
./.venv/Scripts/python.exe -m pytest backend/tests -q -o asyncio_default_fixture_loop_scope=function
```

Las pruebas no necesitan una clave ni acceso a un proveedor. El entorno
virtual queda excluido de Git. No se deben añadir archivos `.env` al commit.

## Resultado de la verificación de esta fase

- Python 3.14.7, entorno virtual local `.venv`.
- FastAPI 0.162.0, Pydantic 2.14.2, Starlette 1.10.0 y pytest 9.2.0.
- Base del commit 9475f6b, sin archivos de entorno: 64 pruebas correctas.
- Backend estabilizado: 138 pruebas correctas (64 originales y 74 nuevas).
- `pip check`: ninguna dependencia incompatible.
- Un aviso de deprecación de Starlette por el cliente de pruebas basado en
  httpx. No se cambia el transporte ni se añade una dependencia en esta fase.
- Las pruebas se ejecutaron con la carga de dotenv desactivada.
