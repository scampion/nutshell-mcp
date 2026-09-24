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
| [06-heat-ageing.md](06-heat-ageing.md) | Qwen3.8-27B (OpenRouter) | temperatures read from 2023, labelled 2024 — see example 6 |
| [07-family-relocation.md](07-family-relocation.md) | Qwen3.8-27B (OpenRouter) | |
| [08-tourism-heat-rail.md](08-tourism-heat-rail.md) | Qwen3.8-27B (OpenRouter) | third run, after both hints |
| [08-tourism-heat-rail-run1.md](08-tourism-heat-rail-run1.md) | Qwen3.8-27B (OpenRouter) | GR search, 2023 read as 2024, invented Canaries value |
| [08-tourism-heat-rail-run2.md](08-tourism-heat-rail-run2.md) | Qwen3.8-27B (OpenRouter) | drops the tourism part |
| [09-schools-children.md](09-schools-children.md) | Qwen3.8-27B (OpenRouter) | |
| [10-east-west-convergence.md](10-east-west-convergence.md) | Qwen3.8-27B (OpenRouter) | EU 2020 mean wrong in the answer — see example 10 |
| [10-east-west-convergence-before-fix.md](10-east-west-convergence-before-fix.md) | Qwen3.8-27B (OpenRouter) | before the EU27 hint |

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
