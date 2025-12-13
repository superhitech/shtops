# Dashboard

Flask web UI for unified visibility and LLM-powered intelligence.

**Status:** MVP complete with Intelligence Layer integration.

## Run

```bash
# Basic (without LLM)
python -m dashboard.app

# With LLM integration
export OPENAI_API_KEY="sk-..."
python -m dashboard.app

# Custom config
SHTOPS_CONFIG=./config/config.yaml python -m dashboard.app
```

Open http://localhost:5000

## Features

✅ System health tiles  
✅ Alert summary  
✅ Update/reboot status  
✅ Links to native UIs  
✅ **Chat panel for LLM queries** (Intelligence Layer)

## LLM Integration

The dashboard includes an interactive chat panel powered by LLM (OpenAI, Anthropic, or GitHub Models).

**Setup:**

1. Add LLM config to `config.yaml`:
   ```yaml
   llm:
     enabled: true
     provider: "openai"
     api_key: "$OPENAI_API_KEY"
     model: "gpt-4"
   ```

2. Set API key: `export OPENAI_API_KEY="sk-..."`

3. Start dashboard: `python -m dashboard.app`

See [../docs/LLM_INTEGRATION.md](../docs/LLM_INTEGRATION.md) for full details
