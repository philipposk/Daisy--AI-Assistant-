# Daisy 1.3 — Long-term memory + compression

Daisy now remembers things across conversations. Tell her once "I prefer Python", "my dog's name is Rex", or "I work at Acme Corp", and she'll still know next week. She also auto-summarizes long conversations so she doesn't lose context (or rack up huge token bills) when you've been chatting for hours.

## New in 1.3

- **`services/memory.py`** — SQLite-backed `MemoryStore` (`memory.db`) + `ConversationSummarizer`
  - `MemoryStore`: `remember / recall / search / forget / list_all` — keyword scoring, no embeddings
  - `ConversationSummarizer`: compresses oldest 10 messages into 1 system summary when history > `max_turns`. Extractive fallback; LLM summary if brain service available
- **Pipeline integration**: every `process_text` call:
  1. Compresses old turns
  2. Searches memory for top-3 relevant facts to current input
  3. Injects them as system message
- **API endpoints**:
  - `GET /api/memory` — list all
  - `GET /api/memory/search?q=` — keyword search
  - `GET /api/memory/{topic}` — recall one
  - `POST /api/memory` — store/update
  - `DELETE /api/memory/{topic}` — forget
- 21 new tests

## Tests

173/173 passing.

## Example

```bash
curl -X POST localhost:5188/api/memory -d '{"topic":"fav_lang","content":"Python"}'
curl localhost:5188/api/memory/search?q=programming
```
