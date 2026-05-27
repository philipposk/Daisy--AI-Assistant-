# Daisy 0.7 — Bug-fix release

A maintenance release. Voice replies stopped being silent on launch, TTS started using the right voice from your config, the safety filter stopped incorrectly blocking harmless commands, and a dozen other rough edges got sanded down. No new features — everything from 0.6 just works as intended.

## 22 fixes vs 0.6

- Deduped shebang + import block in `daisy.py`
- Startup greeting now actually plays (was written to file, never played)
- TTS uses dedicated API key (was using STT's key)
- `tempfile.NamedTemporaryFile` replaces deprecated `mktemp`
- Piper TTS implemented (shell-out to `piper`); was `NotImplementedError`
- System TTS voice from config (was hardcoded "Victoria")
- Groq model respects `config.llm.model`
- JSON extractor handles nested objects + arrays (was 1-level only)
- Note filename collision prevention (`_2`, `_3` suffix)
- Single shared `PersistenceLayer` (removed parallel DB schema in `ActionService`)
- Safety check runs once (dispatcher only); confirmation-required actions return failed `ActionResult`
- Safety checker uses `shlex` tokenisation (no more `"curl"` matching `"currently"`, `"su"` matching `"sudo"`)
- Whitelist matches `basename(token[0])` — `/usr/bin/ls` works
- Dead YAML import branch removed
- Env-var overlay includes `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- `afplay` runs via `Popen` so playback handle is killable (sets up barge-in in 0.8)
- Safety test rewritten for shlex semantics

## Tests

41/41 passing.

## Quick start

```bash
./setup.sh
python3 tests/run_tests.py
python3 daisy.py --text
```
