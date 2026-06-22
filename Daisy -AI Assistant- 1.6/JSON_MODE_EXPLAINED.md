# JSON Mode Explained

## What is JSON Mode?

**JSON mode** is a feature in OpenAI's API that forces the model to output **only valid JSON** - no extra text, no markdown, no explanations. It guarantees the response is parseable JSON.

### With JSON Mode (Supported Models):
```
Model Response: {"actions": [{"action_type": "create_note", "create_note": {...}}]}
✅ Guaranteed valid JSON
✅ No parsing needed
✅ Reliable structured output
```

### Without JSON Mode (Your Current Model):
```
Model Response: "I'll help you create a note. Here's the JSON:
```json
{
  "actions": [{
    "action_type": "create_note",
    "create_note": {
      "title": "Python Notes",
      "content": "..."
    }
  }]
}
```"
⚠️ May include explanatory text
⚠️ Needs JSON extraction
⚠️ Might need fallback parsing
```

## Why It Matters for Daisy

Daisy's **Brain Service** needs structured JSON to:
1. Parse actions (create_note, create_task, etc.)
2. Validate the structure
3. Execute the correct actions

Without JSON mode, the model might:
- Add explanatory text before/after the JSON
- Wrap JSON in markdown code blocks
- Return free-form text instead of JSON

## How Daisy Handles It

Daisy has **smart fallback parsing** that:

1. **Tries JSON mode first** (if supported)
2. **Falls back to regular mode** (if not supported)
3. **Extracts JSON from text** using multiple strategies:
   - Looks for JSON in markdown code blocks: ` ```json {...} ``` `
   - Finds JSON objects directly: `{...}`
   - Parses the entire response
   - Falls back to conversation action if no JSON found

## Is This a Problem?

**Not really!** Daisy works fine without JSON mode because:

✅ **Smart JSON extraction** handles most cases
✅ **Fallback to conversation** if JSON parsing fails
✅ **Still functional** - just needs more parsing

However, **JSON mode is better** because:
- More reliable structured output
- Less parsing needed
- Fewer edge cases

## Which Models Support JSON Mode?

**Supported:**
- `gpt-4-turbo` ✅
- `gpt-4o` ✅
- `gpt-4o-mini` ✅
- `gpt-3.5-turbo` ✅

**May Not Support:**
- Some older `gpt-4` variants ⚠️
- Custom fine-tuned models ⚠️

## How to Check Your Model

Your current model is: `gpt-4`

This might be an older variant that doesn't support JSON mode. You can:

1. **Switch to a supported model** in `~/.daisy/config.yaml`:
   ```yaml
   llm:
     model: "gpt-4-turbo"  # or "gpt-4o"
   ```

2. **Keep using current model** - Daisy will handle it with fallback parsing

## Current Behavior

When you see:
```
WARNING - JSON mode not supported for gpt-4, using regular mode
```

This means:
- ✅ Daisy is still working
- ✅ It's using fallback JSON extraction
- ✅ You can still use Daisy normally
- ⚠️ Just less reliable than with JSON mode

## Recommendation

**For best results**, switch to `gpt-4-turbo` or `gpt-4o` in your config:
```bash
# Edit config
nano ~/.daisy/config.yaml

# Change:
llm:
  model: "gpt-4-turbo"  # or "gpt-4o"
```

This will give you:
- ✅ Guaranteed JSON output
- ✅ More reliable action parsing
- ✅ Better structured responses

But **Daisy works fine** with your current model too - it just needs a bit more parsing!



