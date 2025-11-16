## Daisy – AI Assistant

**Daisy** is a lightweight, privacy‑minded AI assistant that helps you automate everyday tasks on your Mac.  
This repo contains several **versioned snapshots** of Daisy as the project evolved, plus screenshots and helper docs.

### What Daisy Does

- **Voice‑first assistant**: Listens for a wake word (`daisy`), talks back using TTS, and keeps conversations flowing.
- **Desktop automation**: Uses MCP desktop automation and small scripts to drive apps like Android Studio, Xcode, and more.
- **Local‑friendly**: Uses local tools where possible (e.g. Piper TTS), with plug‑in support for different LLM backends.

> **Important:** All API keys in this repo are intentionally **blank placeholders**.  
> You must add your own keys locally before Daisy can talk to LLMs.

### Version Folders

Each `Daisy -AI Assistant- X.Y` folder is a self‑contained snapshot:

- `Daisy -AI Assistant- 0.1` – First minimal end‑to‑end Daisy: wake word, LLM, and basic desktop hooks.
- `Daisy -AI Assistant- 0.2` / `0.25` – Improved reliability, better API quota handling, and early voice support.
- `Daisy -AI Assistant- 0.3` – Adds the `Praiser` app and stronger TTS/voice pipelines.
- `Daisy -AI Assistant- 0.4` – More robust voice stack, local Piper model flow, and quality‑of‑life automation upgrades.
- `Daisy -AI Assistant- 0.5` – Polished “assistant you can actually live with”: better docs, testing flows, and integration story.

You can treat each version folder as its own mini‑project: open the docs inside (`README.md`, `QUICKSTART.md`, `USAGE_GUIDE.md`, etc.) and follow the setup steps for that version.

### Getting Started (Recommended Path)

1. Open `Daisy -AI Assistant- 0.5/README.md` and `QUICKSTART.md`.  
2. Follow the setup scripts (`setup.sh`, `setup-daisy-voice.sh`) and instructions to install dependencies.  
3. Add your **OpenAI / Groq (or other)** API keys **locally only** in your own `.daisy/config.json` (do not commit them).  
4. Start the agent via the provided scripts (for example `start-daisy.sh` or `start-agent.sh`) and try a simple voice command.

### Security & API Keys

- All committed `.daisy/config.json` files ship with **empty** `openai_api_key` and `groq_api_key` fields.
- Never commit real secrets. Store keys only in your local working copy or through environment variables.
- If you accidentally commit a real key, **revoke it** in your provider’s dashboard and rotate it before pushing again.

### License

This project is open source under the **MIT License**. See `LICENSE` for details.


