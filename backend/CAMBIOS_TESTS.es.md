[English](CAMBIOS_TESTS.md) | **Español**

# Correcciones de pruebas del backend

## Cambios

- `chatbot/llm_client.py`: valida estrictamente el nombre del modelo configurado; rechaza campos adicionales en la salida JSON de Gemini; amplía el rechazo de afirmaciones engañosas sobre reservas, disponibilidad y alérgenos; minimiza el historial reenviado a Gemini descartando mensajes anteriores ambiguos y mensajes de reserva. Se conserva contexto previo relacionado con la carta.
- `tests/test_gemini.py`: ajusta los límites a los valores vigentes (10/minuto y 100/24 h), comprueba el aviso específico de límite, actualiza el texto de confirmación simulada y añade una regresión de filtrado de historial.
- `tests/test_backend.py`: corrige el test de confirmación de reserva y su indentación.

## Verificación

- Sintaxis Python: `compileall`, correcta.
- Pruebas: **199 passed** en un entorno de comprobación con **doble local mínimo del SDK `google.genai`**, porque el paquete real no estaba disponible en este entorno. Este resultado **no sustituye** la ejecución con `google-genai==2.34.0` en tu equipo.

Desde la raíz de Fornaviva, con `.venv` instalado y dependencias disponibles:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:LLM_ENABLED = 'false'
.\.venv\Scripts\python.exe -m pytest backend\tests -q -o asyncio_default_fixture_loop_scope=function
```

## Límite de privacidad

El historial del navegador no es fiable. El filtro reduce la exposición de datos personales y excluye mensajes anteriores sin contexto claro, pero **no puede garantizar la detección de todos los nombres y datos personales expresados en texto libre**. Para una garantía más fuerte, conviene mantener en el servidor un historial público independiente del flujo de reserva y no reenviar al modelo datos arbitrarios del cliente.
