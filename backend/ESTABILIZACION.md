**English** | [Español](ESTABILIZACION.es.md)

> Historical record of the earlier stabilization phase. Its results (138 tests) are retained for reference. The provisional adapter described here has been replaced by the optional integration documented in [GEMINI.md](GEMINI.md).

# Backend verification and stabilization

The Fornaviva API and simulated reservations are retained. No LLM provider is integrated in this phase. The provisional adapter always reports that no provider is available; every structured fallback response includes a limited-mode notice, even if a key is configured.

## Validation

- Intents: reservations, allergens, opening hours, menu and FAQ, in that order. Keywords are matched using word boundaries.
- An active reservation retains its flow before new intents are classified.
- Step and party size require actual integers; booleans are rejected.
- Name: 2–100 characters and at least two letters. Unicode letters, diacritics, spaces, apostrophes, hyphens and periods are allowed. Numbers, control characters and markup are rejected. Validation also applies to state.
- Invalid active states restart the flow without confirming a reservation.
- Confirmation continues to revalidate date, time and party size.

## HTTP limits

- POST body: actual 128 KiB, including chunked transfer. Excess: HTTP 413 before JSON processing.
- Message: 1–2000 characters, not whitespace-only.
- History: up to 40 messages, `user`/`assistant` roles, content of 1–2000 characters and a cumulative maximum of 20000 characters.
- State: up to 16 fields; keys up to 64 characters; scalar values up to 100 characters or integers between -1000000 and 1000000. Business fields are subsequently validated against their specific ranges.
- Unknown request/history fields are rejected. Extra scalar state fields are discarded as before.
- Invalid schema or field limits: HTTP 422.

The client must trim the oldest history before exceeding the limits. Reservations and history are not stored on the server.

## PowerShell tests (from the root)

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
$env:PYTHON_DOTENV_DISABLED = '1'
$env:LLM_API_KEY = ''
./.venv/Scripts/python.exe -m pytest backend/tests -q -o asyncio_default_fixture_loop_scope=function
```

Tests require neither a key nor provider access. The virtual environment is excluded from Git. Do not commit `.env` files.

## Verification results for this phase

- Python 3.14.7, local `.venv` virtual environment.
- FastAPI 0.162.0, Pydantic 2.14.2, Starlette 1.10.0 and pytest 9.2.0.
- Baseline commit 9475f6b, without environment files: 64 passing tests.
- Stabilized backend: 138 passing tests (64 original and 74 new).
- `pip check`: no incompatible dependencies.
- One Starlette deprecation warning concerning the httpx-based test client. No transport change or new dependency in this phase.
- Tests were run with dotenv loading disabled.
