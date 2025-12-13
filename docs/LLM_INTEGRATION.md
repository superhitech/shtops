# LLM Integration - Intelligence Layer

The LLM integration enables natural language queries against cached operational data.

## Features

- **Natural language queries**: Ask questions about infrastructure in plain English
- **Context-aware**: LLM has access to all cached system data (LibreNMS, Proxmox, FreePBX, UniFi)
- **Multiple providers**: Support for OpenAI, Anthropic Claude, and GitHub Models
- **Dashboard chat**: Interactive chat panel in the web dashboard
- **Actionable insights**: Correlate data across systems and highlight critical issues

## Configuration

Add to your `config.yaml`:

```yaml
llm:
  enabled: true
  provider: "openai"  # Options: openai, anthropic, github
  api_key: "$OPENAI_API_KEY"  # Use $ENV_VAR to read from environment
  model: "gpt-4"  # or gpt-3.5-turbo, claude-3-sonnet-20240229, etc.
  
  # Optional:
  # base_url: "https://api.openai.com/v1"  # Override for custom endpoints
  # temperature: 0.7
  # max_tokens: 2000
```

### Provider Options

**OpenAI:**
```yaml
llm:
  enabled: true
  provider: "openai"
  api_key: "$OPENAI_API_KEY"
  model: "gpt-4"  # or gpt-3.5-turbo, gpt-4-turbo, gpt-4o
```

**Anthropic Claude:**
```yaml
llm:
  enabled: true
  provider: "anthropic"
  api_key: "$ANTHROPIC_API_KEY"
  model: "claude-3-sonnet-20240229"  # or claude-3-opus-20240229
```

**GitHub Models:**
```yaml
llm:
  enabled: true
  provider: "github"
  api_key: "$GITHUB_TOKEN"
  model: "gpt-4o"  # Uses Azure OpenAI via GitHub
```

## Usage

### Dashboard Chat

1. Start the dashboard:
   ```bash
   export OPENAI_API_KEY="sk-..."
   python -m dashboard.app
   ```

2. Open http://localhost:5000

3. Use the chat panel on the right side to ask questions:
   - "What needs attention?"
   - "Show me all stopped VMs"
   - "Are there any devices down?"
   - "What's the status of FreePBX?"

### Testing

Test the LLM integration directly:

```bash
export OPENAI_API_KEY="sk-..."
python test_llm_integration.py
```

This will run test queries and enter interactive mode for custom questions.

## How It Works

1. **Context Loading**: When a query is received, the LLM client loads all cache files and creates a comprehensive context summary

2. **Smart Summarization**: Data is summarized to highlight key information (device counts, alerts, VM status) while keeping full data available for detailed queries

3. **System Prompt**: The LLM is given a system prompt that positions it as an operational intelligence assistant with instructions to be concise and actionable

4. **Query Processing**: User questions are sent to the LLM with the operational context, and responses are returned in real-time

## Example Queries

- **Status checks**: "What's the overall infrastructure health?"
- **Specific systems**: "Show me Proxmox VM status"
- **Problems**: "What devices are alerting?"
- **Comparisons**: "Which VMs are stopped but should be running?"
- **Trends**: "Are there any patterns in the alerts?"
- **Recommendations**: "What should I focus on first?"

## Architecture

```
User Query
    ↓
Dashboard Chat UI (JavaScript)
    ↓
Flask API Endpoint (/api/chat)
    ↓
LLM Client (clients/llm_client.py)
    ↓
Cache Files (JSON) → Context Builder
    ↓
LLM Provider API (OpenAI/Anthropic/GitHub)
    ↓
Response
    ↓
User
```

## Future Enhancements

- **Conversation history**: Remember previous questions in a session
- **Action suggestions**: "Would you like me to restart that VM?"
- **Scheduled reports**: Daily/weekly summaries pushed to Slack
- **Multi-interface**: Same LLM context in VS Code, CLI, Slack bot
- **Custom prompts**: User-defined system prompts for specific use cases
