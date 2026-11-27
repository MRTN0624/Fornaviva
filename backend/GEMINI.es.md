[English](GEMINI.md) | **Español**

# Gemini en el backend Fornaviva

## Modelo configurado y SDK

Se utiliza el SDK oficial **Google Gen AI**, paquete `google-genai==2.34.0`,
con Gemini Developer API y generación asíncrona.

No se utiliza el SDK antiguo `google-generativeai`, Vertex AI,
herramientas de búsqueda ni servicios de pago.

Modelo configurado por defecto en el código: **`gemini-3.5-flash-lite`**.

Este modelo ya se ha probado durante el desarrollo local de Fornaviva.
Su disponibilidad y las condiciones del nivel gratuito deben comprobarse
en el proyecto de Google AI Studio antes de activarlo en producción.

El modelo se selecciona desde el backend mediante `LLM_MODEL_NAME`,
no desde el cliente HTTP. El código actual no restringe esta variable
a un único identificador.

Fuentes oficiales de referencia:

- [SDK recomendado](https://ai.google.dev/gemini-api/docs/libraries)
- [SDK Python: cliente, generación asíncrona y cierre](https://googleapis.github.io/python-genai/)
- [Catálogo de modelos](https://ai.google.dev/gemini-api/docs/models)
- [Precios y nivel gratuito](https://ai.google.dev/gemini-api/docs/pricing)
- [Límites por proyecto](https://ai.google.dev/gemini-api/docs/rate-limits)

## Activar y desactivar

Instala las dependencias en un entorno virtual desde la raíz del proyecto:

```powershell
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

Para desarrollo local, configura `backend/.env` sin compartir ni imprimir
su contenido:

```dotenv
LLM_ENABLED=true
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-3.5-flash-lite
```

La clave privada se obtiene exclusivamente de la variable `LLM_API_KEY`.

No se emplean `GEMINI_API_KEY`, `GOOGLE_API_KEY` ni variables `VITE_*`
como fuentes alternativas de la clave.

No incluyas archivos `.env` ni claves privadas en Git.

Para arrancar el backend localmente:

```powershell
./.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --port 8000
```

Para desactivar Gemini:

```dotenv
LLM_ENABLED=false
```

Reinicia el backend después de modificar la configuración.

La integración está desactivada por defecto.

Las variables de entorno existentes en el proceso tienen prioridad
sobre los valores cargados desde `.env`.

`PYTHON_DOTENV_DISABLED=1` desactiva la carga de archivos dotenv.
Se utiliza durante las pruebas automatizadas, no durante la ejecución
local cuando se necesita la configuración del archivo.

### Configuración en producción

En Render, las variables deben configurarse desde la sección
**Environment** del servicio backend.

La clave `LLM_API_KEY` debe permanecer exclusivamente en el servidor.

Nunca debe configurarse en Vercel mediante una variable `VITE_*`,
porque esas variables se incorporan al código accesible desde
el navegador.

La configuración del frontend no necesita modificarse para activar
Gemini en el backend.

## Flujo y protección de reservas

1. El backend valida la petición HTTP mediante los límites y contratos
   establecidos.

2. Las reservas activas o explícitas se gestionan mediante el flujo
   determinista de Python, sin depender de Gemini.

3. Para las consultas que pueden enviarse al modelo, se construye
   un contexto utilizando cuatro archivos JSON de `backend/data/`:

   - `menu.json`
   - `alergenos.json`
   - `horarios.json`
   - `faqs.json`

   Si alguno no puede cargarse, no se realiza la llamada al proveedor.

4. Gemini recibe instrucciones de sistema que restringen sus respuestas
   a los datos proporcionados.

   No debe inventar platos, precios, ingredientes, alérgenos, horarios,
   políticas ni disponibilidad.

   Los valores `null` se consideran información desconocida,
   nunca ausencia confirmada.

5. El modelo devuelve una respuesta estructurada con dos campos:

   - `accion`: `informacion` o `reserva`.
   - `respuesta`: texto destinado al usuario.

6. Si Gemini devuelve `accion=reserva`, Python inicia el flujo
   de reserva simulada.

   Gemini no confirma reservas ni modifica directamente su estado.

7. Las respuestas vacías, inválidas, bloqueadas, truncadas,
   excesivamente largas o que incluyan determinadas afirmaciones
   prohibidas se descartan.

Las instrucciones y los filtros reducen el riesgo de errores,
pero no constituyen una verificación semántica completa.

El modelo puede equivocarse y los filtros de texto no detectan
todas las formulaciones posibles.

Las reservas y su validación permanecen fuera del modelo.

Los datos de alérgenos son orientativos y nunca garantizan
ausencia de trazas o contaminación cruzada.

## Conversación y recomendaciones

Gemini puede mantener conversaciones naturales relacionadas
con Fornaviva.

Puede responder a saludos, despedidas, preguntas informales
y comentarios relacionados con el restaurante.

También puede recomendar platos en función de los gustos
expresados por el usuario.

Para ello, sus instrucciones le permiten realizar preguntas
sobre preferencias, por ejemplo:

- Sabores suaves o picantes.
- Preferencia por el queso.
- Opciones vegetarianas.

Las recomendaciones deben limitarse a los platos presentes
en los archivos JSON del restaurante.

Si el usuario pregunta por un producto que no aparece en la carta,
el asistente debe indicarlo sin inventar su disponibilidad.

Puede proponer alternativas que sí consten en los datos.

El historial enviado al modelo permite conservar parte del contexto
de la conversación, pero no constituye memoria permanente.

## Privacidad

El backend puede enviar a Gemini hasta los siete mensajes más recientes
del historial de conversación.

Estos mensajes pueden incluir intervenciones del usuario
y respuestas anteriores del asistente.

Antes de enviarlos, el código descarta mensajes que:

- Estén vacíos.
- Superen los 2000 caracteres.
- Contengan la clave API configurada.
- Coincidan con determinados patrones de información personal,
  como correos electrónicos, teléfonos, direcciones web
  o presentaciones personales explícitas.

La pregunta actual también se somete a comprobaciones específicas
antes de permitir una llamada a Gemini.

Los filtros son conservadores y no garantizan detectar todos
los datos personales o confidenciales.

Por tanto, no deben introducirse datos personales reales
en las conversaciones de demostración.

El estado interno de las reservas no se incorpora directamente
al contexto enviado al modelo.

Sin embargo, el historial conversacional se filtra por patrones,
no mediante una eliminación semántica completa de información
relacionada con reservas.

No se garantiza que cualquier dato personal escrito en un mensaje
anterior sea detectado por esos filtros.

El código del cliente Gemini no registra deliberadamente
preguntas, prompts, respuestas ni excepciones del proveedor.

Los errores internos del proveedor no se devuelven directamente
al usuario mediante la respuesta del chatbot.

No deben activarse trazas del SDK o de HTTP que puedan revelar
información sensible.

## Límites locales y fallback

### Límites de entrada HTTP

Se conservan las validaciones del backend:

- Cuerpo POST: máximo de 128 KiB.
- Mensaje: entre 1 y 2000 caracteres.
- Historial: máximo de 40 mensajes.
- Contenido acumulado del historial: máximo de 20000 caracteres.
- Estado de reserva: validado mediante los contratos establecidos.

Las peticiones que incumplen el esquema o los límites de campos
pueden devolver HTTP 422.

Los cuerpos POST que superan el límite establecido devuelven HTTP 413.

### Límites de Gemini

- Hasta siete mensajes recientes del historial, filtrados antes del envío.
- Pregunta actual de hasta 2000 caracteres.
- Contexto JSON de hasta 24000 caracteres.
- Respuesta publicada de hasta 1800 caracteres.
- Generación limitada a 1024 tokens de salida.
- Nivel de pensamiento configurado como `low`.
- Tiempo máximo de generación de 12 segundos.
- Timeout HTTP configurado en 12000 milisegundos.
- Un único intento por generación, sin reintentos automáticos.
- Sin herramientas, búsqueda web ni llamadas automáticas a funciones.

Si el contexto supera el límite establecido, se utiliza
el comportamiento de respaldo sin enviarlo parcialmente.

Los transportes síncrono y asíncrono del cliente se cierran
al finalizar la operación o durante su cancelación.

### Límites de solicitudes

El backend mantiene un presupuesto local de:

- 10 intentos por minuto.
- 100 intentos por ventana móvil de 24 horas.

Los intentos fallidos también consumen presupuesto.

Cuando se produce una excepción durante una llamada al proveedor,
las nuevas llamadas se bloquean temporalmente durante 60 segundos.

Los contadores son compartidos dentro de un mismo proceso Python.

Se almacenan únicamente en memoria, se reinician al reiniciar
el servidor y no se coordinan entre múltiples procesos o workers.

Estos límites no constituyen una garantía económica
ni sustituyen las cuotas configuradas por Google.

Para esta demostración se recomienda utilizar un único worker
y un proyecto sin facturación habilitada.

### Comportamiento de respaldo

Gemini es una integración opcional.

Si no está habilitado, falta configuración, falla la conexión,
se agota la cuota del proveedor, se produce un timeout
o la respuesta no resulta utilizable, el cliente devuelve `None`.

El backend puede entonces utilizar las respuestas deterministas
del chatbot.

Cuando se alcanza el presupuesto local de solicitudes,
el cliente devuelve la señal interna `__FORNAVIVA_LIMITE__`,
que permite distinguir esta situación de otros errores.

Los errores del proveedor no se exponen directamente al usuario.

El chatbot conserva el funcionamiento básico mediante Python
cuando Gemini no está disponible.

Las reservas simuladas y los endpoints GET no dependen
de la disponibilidad del modelo.

La función `llm_disponible()` comprueba que Gemini esté habilitado,
que el proveedor configurado sea `gemini`, que exista un nombre
de modelo no vacío y que haya una clave API.

Esta comprobación no garantiza que el modelo exista,
que la clave tenga permisos ni que el proveedor responda.

La disponibilidad real solo puede determinarse al realizar
una llamada válida.

## Nivel gratuito y costes

La integración está diseñada para utilizarse sin activar
servicios de pago.

Sin embargo, el código no puede garantizar que una clave API
pertenezca a un proyecto del nivel gratuito.

Antes de activar Gemini en producción, se debe comprobar
en Google AI Studio:

- Que el proyecto asociado a la clave es el correcto.
- Que el modelo seleccionado está disponible.
- Que las condiciones de uso corresponden al nivel gratuito.
- Que no existe facturación habilitada si se desea evitar costes.

Las cuotas dependen del proyecto, del modelo y del nivel de acceso.

No se asumen valores fijos de solicitudes por minuto o por día
para el proveedor.

Los límites locales de Fornaviva no sustituyen las restricciones
de Google ni garantizan la ausencia de cargos.

En el nivel gratuito, Google puede utilizar contenido enviado
a la API para mejorar sus productos, según las condiciones aplicables.

No se deben enviar datos personales, privados o confidenciales.

## Pruebas

Para ejecutar las pruebas automatizadas desde la raíz del proyecto
en PowerShell:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:LLM_ENABLED = 'false'
./.venv/Scripts/python.exe -m pytest backend/tests -q -o asyncio_default_fixture_loop_scope=function
```

Las pruebas automatizadas no necesitan una clave API real.

La configuración de pruebas desactiva Gemini y utiliza
sustituciones simuladas del cliente para comprobar
la integración sin realizar llamadas al proveedor.

Entre los aspectos comprobados se incluyen:

- Construcción de peticiones.
- Contexto del restaurante.
- Restricciones de respuesta.
- Tiempos de espera.
- Cierre de conexiones.
- Presupuestos de solicitudes.
- Tratamiento de credenciales.
- Protección del flujo de reservas.

Las pruebas automatizadas no verifican por sí solas
la disponibilidad real del proveedor en producción.

Para comprobar la integración real será necesaria
una prueba controlada con una pregunta ficticia
y sin información personal.
