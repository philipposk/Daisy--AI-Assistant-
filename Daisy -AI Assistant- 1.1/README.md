# Daisy 1.1 — Mac Keychain secrets

API keys (OpenAI, Anthropic, etc.) no longer sit in plain-text config files. They go in the macOS Keychain — the same secure storage your Mac uses for WiFi passwords. Manage them from the UI or via API; deleting a key wipes it from the Keychain.

## New in 1.1

- **`services/keychain.py`** — wrapper around macOS `security` CLI, zero pip dependencies
- **Known keys**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`
- **Config loader overlay order**: defaults → file → **Keychain** → env vars (Keychain inserted in 1.1)
- **API endpoints**:
  - `GET /api/keychain` → `{available, known_keys, set_keys}`
  - `POST /api/keychain` → `{name, value}` stores in Keychain
  - `DELETE /api/keychain/{name}` removes from Keychain
- 8 new tests (mocked `subprocess.run`)

## Tests

125/125 passing.

## Quick start

```bash
./setup.sh
# Store key in Keychain (one time):
python3 -c "from services.keychain import set_secret; set_secret('OPENAI_API_KEY', 'sk-...')"
python3 daisy_app.py --port 5188 --no-ui
```
