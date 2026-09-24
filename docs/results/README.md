# Real runs

Transcripts behind [the example prompts](../examples.md). Nothing is edited:
tool calls and tool outputs are verbatim, only the model's hidden reasoning is
left out.

| File | Model | Notes |
|---|---|---|
| [01-geriatric-clinic.md](01-geriatric-clinic.md) | — | final answer only, run by the author |
| [02-compare-regions.md](02-compare-regions.md) | Qwen3.8-27B (Hugging Face) | |
| [03-nuts3-fallback.md](03-nuts3-fallback.md) | Qwen3.8-27B (OpenRouter) | |
| [04-tourism.md](04-tourism.md) | Qwen3.8-27B (OpenRouter) | after the `list_codes` fix |
| [04-tourism-before-fix.md](04-tourism-before-fix.md) | Qwen3.8-27B (OpenRouter) | misses Canarias — see example 4 |
| [05-new-indicator-yaml.md](05-new-indicator-yaml.md) | Qwen3.8-27B (OpenRouter) | |

## How they were produced

Harness [pi](https://github.com/badlogic/pi-mono) with the `pi-mcp-adapter`
package, the server declared with direct tools in a `.mcp.json`:

```json
{ "mcpServers": { "nutshell": {
    "url": "https://nutshell.scamp.fr/mcp", "directTools": true, "lifecycle": "eager" } } }
```

```bash
pi -p --approve --no-context-files --no-skills --no-builtin-tools --no-session \
   --provider openrouter --model qwen/qwen3.8-27b --thinking low --mode json \
   "<prompt>" </dev/null > run.jsonl
```

`--no-builtin-tools` leaves the model with the nutshell tools only (plus the
adapter's own `mcp` / `mcpScript` helpers, which it tried once in example 5 to
write a file — the sandbox refused). Reasoning level `low`, as recommended for
27B models. The JSON event stream was then turned into Markdown.
