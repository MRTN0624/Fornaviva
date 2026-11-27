**English** | [Español](GEMINI.es.md)

# Gemini in the Fornaviva backend

## Configured model and SDK

The official **Google Gen AI** SDK (`google-genai==2.34.0`) is used with the Gemini Developer API and asynchronous generation. The older `google-generativeai` SDK, Vertex AI, search tools and paid services are not used.

Default model in the code: **`gemini-3.5-flash-lite`**. This model was tested during local development. Its availability and free-tier conditions should be checked in Google AI Studio before enabling production use. The backend selects the model through `LLM_MODEL_NAME`, not through the HTTP client. The code does not restrict this variable to one identifier.

Official references:

- [Recommended SDK](https://ai.google.dev/gemini-api/docs/libraries)
- [Python SDK: client, asynchronous generation and closing](https://googleapis.github.io/python-genai/)
- [Model catalogue](https://ai.google.dev/gemini-api/docs/models)
- [Pricing and free tier](https://ai.google.dev/gemini-api/docs/pricing)
- [Project rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)

## Enabling and disabling

Install dependencies in a virtual environment from the project root:

```powershell
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

For local development, configure `backend/.env` without sharing or printing its contents:

```dotenv
LLM_ENABLED=true
LLM_PROVIDER=gemini
LLM_MODEL_NAME=gemini-3.5-flash-lite
```

The private key is obtained exclusively from `LLM_API_KEY`. Neither `GEMINI_API_KEY`, `GOOGLE_API_KEY` nor `VITE_*` variables are alternative key sources. Do not commit `.env` files or private keys.

Start the local backend:

```powershell
./.venv/Scripts/python.exe -m uvicorn main:app --app-dir backend --reload --port 8000
```

To disable Gemini:

```dotenv
LLM_ENABLED=false
```

Restart the backend after configuration changes. Integration is disabled by default. Existing process environment variables take precedence over values loaded from `.env`. `PYTHON_DOTENV_DISABLED=1` disables dotenv loading and is used in automated tests, not in local execution requiring file configuration.

### Production configuration

Configure variables in the backend service's **Environment** section in Render. `LLM_API_KEY` must remain exclusively on the server. Never configure it in Vercel through a `VITE_*` variable, because those variables are included in browser-accessible code. No frontend configuration changes are required to enable Gemini in the backend.

## Flow and reservation protection

1. The backend validates HTTP requests against established limits and contracts.
2. Active or explicit reservations are handled by the deterministic Python flow independently of Gemini.
3. For eligible queries, context is built from four JSON files in `backend/data/`: `menu.json`, `alergenos.json`, `horarios.json` and `faqs.json`. If any cannot be loaded, the provider is not called.
4. Gemini receives system instructions restricting responses to supplied data. It must not invent dishes, prices, ingredients, allergens, hours, policies or availability. `null` values mean unknown information, never confirmed absence.
5. The model returns a structured response with `accion` (`informacion` or `reserva`) and `respuesta` (user-facing text).
6. If Gemini returns `accion=reserva`, Python starts the simulated reservation flow. Gemini neither confirms reservations nor directly changes their state.
7. Empty, invalid, blocked, truncated, excessively long responses or those containing certain prohibited claims are discarded.

Instructions and filters reduce error risks but are not complete semantic verification. The model may make mistakes, and text filters cannot detect every possible formulation. Reservations and their validation remain outside the model. Allergen information is indicative and never guarantees absence of traces or cross-contamination.

## Conversation and recommendations

Gemini supports natural conversations about Fornaviva, including greetings, farewells, informal questions and restaurant-related comments. It can recommend dishes according to user preferences and ask about mild or spicy flavours, cheese preferences and vegetarian options. Recommendations must be limited to dishes in the restaurant JSON files. If a requested product is not on the menu, the assistant must say so without inventing availability and may suggest documented alternatives. History retains some conversational context but is not permanent memory.

## Privacy

The backend can send Gemini up to seven recent conversation-history messages, including user and assistant messages. Before forwarding, the code discards messages that:

- Are empty.
- Exceed 2000 characters.
- Contain the configured API key.
- Match certain personal-information patterns, including email addresses, phone numbers, web addresses or explicit personal introductions.

The current question also undergoes specific checks before a Gemini call is allowed. Conservative filters cannot guarantee detection of all personal or confidential data. Do not enter real personal data in demonstration conversations.

Internal reservation state is not directly included in model context. Conversation history is filtered by patterns, not by complete semantic removal of reservation-related information. Personal details in earlier messages may escape detection.

The Gemini client does not deliberately log questions, prompts, responses or provider exceptions. Internal provider errors are not returned directly in chatbot responses. Do not enable SDK or HTTP tracing that could reveal sensitive information.

## Local limits and fallback

### HTTP input limits

- POST body: maximum 128 KiB.
- Message: 1–2000 characters.
- History: maximum 40 messages.
- Cumulative history content: maximum 20000 characters.
- Reservation state: validated against established contracts.

Invalid schemas or field limits may return HTTP 422. Oversized POST bodies return HTTP 413.

### Gemini limits

- Up to seven recent history messages, filtered before sending.
- Current question: up to 2000 characters.
- JSON context: up to 24000 characters.
- Published response: up to 1800 characters.
- Generation limited to 1024 output tokens.
- Thinking level: `low`.
- Maximum generation time: 12 seconds.
- HTTP timeout: 12000 milliseconds.
- One attempt per generation, without automatic retries.
- No tools, web search or automatic function calls.

If context exceeds the limit, fallback is used rather than sending partial context. Synchronous and asynchronous client transports are closed after completion or cancellation.

### Request limits

The backend maintains a local budget of 10 attempts per minute and 100 attempts per rolling 24-hour window. Failed attempts also consume budget. Provider exceptions temporarily block new calls for 60 seconds. Counters are shared within a single Python process, stored only in memory, reset on restart and not coordinated across processes or workers. These limits are not financial guarantees and do not replace Google quotas. A single worker and a project without billing enabled are recommended for this demonstration.

### Fallback behaviour

Gemini is optional. If disabled, misconfigured, disconnected, out of provider quota, timed out or producing an unusable response, the client returns `None`. The backend can then use deterministic chatbot responses. When the local request budget is exhausted, the client returns `__FORNAVIVA_LIMITE__` to distinguish that condition from other errors. Provider errors are not exposed directly to users. Basic Python chatbot functionality remains available without Gemini. Simulated reservations and GET endpoints do not depend on the model.

`llm_disponible()` checks whether Gemini is enabled, the configured provider is `gemini`, the model name is nonempty and an API key exists. This does not guarantee model existence, key permissions or provider responsiveness. Actual availability can only be determined through a valid call.

## Free tier and costs

The integration is designed for use without paid services, but the code cannot guarantee that an API key belongs to a free-tier project. Before enabling production Gemini, check in Google AI Studio that the key belongs to the correct project, the selected model is available, the usage conditions match the free tier and billing is disabled if costs are to be avoided.

Quotas depend on the project, model and access tier. No fixed provider request limits per minute or day are assumed. Fornaviva's local limits do not replace Google's restrictions or guarantee absence of charges. Under applicable free-tier terms, Google may use API content to improve its products. Do not send personal, private or confidential data.

## Tests

Run automated tests from the project root in PowerShell:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:LLM_ENABLED = 'false'
./.venv/Scripts/python.exe -m pytest backend/tests -q -o asyncio_default_fixture_loop_scope=function
```

Automated tests do not require a real API key. Test configuration disables Gemini and uses simulated client replacements to check integration without provider calls. Coverage includes request construction, restaurant context, response restrictions, timeouts, connection closure, request budgets, credential handling and reservation-flow protection.

Automated tests alone do not verify actual provider availability in production. Real integration verification requires a controlled test with a fictional question and no personal information.
