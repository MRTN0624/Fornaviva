**English** | [Español](CAMBIOS_TESTS.es.md)

# Backend test corrections

## Changes

- `chatbot/llm_client.py`: strictly validates the configured model name; rejects additional fields in Gemini's JSON output; expands rejection of misleading claims about reservations, availability and allergens; minimizes history forwarded to Gemini by discarding ambiguous previous messages and reservation messages. Previous menu-related context is retained.
- `tests/test_gemini.py`: adjusts limits to current values (10/minute and 100/24 h), checks the specific limit notice, updates simulated confirmation text and adds a history-filtering regression test.
- `tests/test_backend.py`: corrects the reservation confirmation test and its indentation.

## Verification

- Python syntax: `compileall`, successful.
- Tests: **199 passed** in a verification environment using a **minimal local test double of the `google.genai` SDK**, because the actual package was unavailable. This result **does not replace** running the tests with `google-genai==2.34.0` locally.

From the Fornaviva root, with `.venv` and dependencies installed:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:LLM_ENABLED = 'false'
.\.venv\Scripts\python.exe -m pytest backend\tests -q -o asyncio_default_fixture_loop_scope=function
```

## Privacy limitation

Browser history is untrusted. Filtering reduces exposure of personal data and excludes previous messages without clear context, but **cannot guarantee detection of every name or personal detail expressed in free text**. For stronger guarantees, maintain a separate public conversation history on the server, independent of the reservation flow, and avoid forwarding arbitrary client data to the model.
