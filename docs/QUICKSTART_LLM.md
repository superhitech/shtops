# Quick Start: LLM Intelligence Layer

Get the Intelligence Layer running in 3 steps.

## Step 1: Install Dependencies

```bash
cd /home/superht/shtops
pip install -r requirements.txt
```

## Step 2: Configure LLM

Edit `config/config.yaml` and add:

```yaml
llm:
  enabled: true
  provider: "openai"  # or anthropic, github
  api_key: "$OPENAI_API_KEY"  # reads from environment variable
  model: "gpt-4"  # or gpt-3.5-turbo, claude-3-sonnet-20240229
```

Set your API key:
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Alternative providers:**
```bash
# Anthropic Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# GitHub Models
export GITHUB_TOKEN="ghp_..."
```

## Step 3: Start Dashboard

```bash
python -m dashboard.app
```

Open http://localhost:5000 in your browser.

## What You'll See

```
┌─────────────────────────────────────────────────────┐
│ SHTops                                              │
│ Overall: OK                                         │
├─────────────────────────────────┬───────────────────┤
│                                 │ Intelligence Layer│
│ [LibreNMS] [Proxmox]           │                   │
│ [FreePBX]  [UniFi]             │ Ask questions...  │
│                                 │                   │
│ Status tiles with health...     │ [Chat interface]  │
│                                 │                   │
│ Attention items...              │                   │
│                                 │                   │
└─────────────────────────────────┴───────────────────┘
```

## Example Questions

Try these in the chat panel:

✅ "What needs attention?"  
✅ "Show me all stopped VMs"  
✅ "Are there any devices down?"  
✅ "What's the status of FreePBX?"  
✅ "Give me a health summary"  

## Testing Without Dashboard

```bash
python test_llm_integration.py
```

This runs test queries and enters interactive mode.

## Troubleshooting

**"LLM not configured" error:**
- Check `llm.enabled: true` in config.yaml
- Verify API key environment variable is set
- Check provider name matches (openai/anthropic/github)

**"Module not found" error:**
- Run: `pip install -r requirements.txt`
- Check you're in the correct directory

**No cache files:**
- Run collectors first: `python -m collectors.librenms.collect`
- Or: `shtops collect`

## What's Next?

Once the Intelligence Layer is working:

1. **Automate collection** - Set up systemd timer for regular updates
2. **Deploy dashboard** - Run as systemd service
3. **Add more interfaces** - VS Code extension, Slack bot, CLI chat
4. **Enable automation** - Start with low-risk tasks (snapshots, restarts)

See [VISION.md](../VISION.md) for the full roadmap.
