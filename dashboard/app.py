from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template_string, request

from clients.llm_client import create_llm_client
from shtops.config import load_app_config, load_raw_config
from shtops.status import collect_status


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_path(repo_root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (repo_root / p)


app = Flask(__name__)


TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset=\"utf-8\"/>
    <title>SHTops Dashboard</title>
    <style>
      body { 
        font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; 
        margin: 0;
        display: flex;
        flex-direction: column;
        height: 100vh;
      }
      .header {
        padding: 24px;
        border-bottom: 1px solid #ddd;
      }
      .main-content {
        display: flex;
        flex: 1;
        overflow: hidden;
      }
      .status-panel {
        flex: 1;
        padding: 24px;
        overflow-y: auto;
      }
      .chat-panel {
        width: 400px;
        border-left: 1px solid #ddd;
        display: flex;
        flex-direction: column;
        background: #f8f9fa;
      }
      .chat-header {
        padding: 16px;
        border-bottom: 1px solid #ddd;
        background: white;
      }
      .chat-messages {
        flex: 1;
        padding: 16px;
        overflow-y: auto;
      }
      .chat-input-container {
        padding: 16px;
        border-top: 1px solid #ddd;
        background: white;
      }
      .chat-input {
        width: 100%;
        padding: 12px;
        border: 1px solid #ddd;
        border-radius: 4px;
        font-family: inherit;
        font-size: 14px;
      }
      .message {
        margin-bottom: 16px;
        padding: 12px;
        border-radius: 8px;
      }
      .message.user {
        background: #e3f2fd;
        margin-left: 20px;
      }
      .message.assistant {
        background: white;
        margin-right: 20px;
        border: 1px solid #ddd;
      }
      .message.error {
        background: #ffebee;
        border: 1px solid #ef5350;
      }
      .message-label {
        font-size: 0.85em;
        font-weight: 600;
        margin-bottom: 6px;
        color: #666;
      }
      .grid { 
        display: grid; 
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); 
        gap: 12px; 
        margin-bottom: 24px;
      }
      .tile { border: 1px solid #ddd; border-radius: 8px; padding: 12px; background: white; }
      .sev-ok { color: #0a7a20; }
      .sev-warn { color: #b36b00; }
      .sev-critical { color: #b00020; }
      .muted { color: #666; font-size: 0.9em; }
      a { color: inherit; }
      .loading {
        opacity: 0.6;
        pointer-events: none;
      }
      .chat-disabled {
        padding: 16px;
        text-align: center;
        color: #666;
        font-size: 0.9em;
      }
    </style>
  </head>
  <body>
    <div class=\"header\">
      <h1 style=\"margin: 0;\">SHTops</h1>
      <p class=\"muted\" style=\"margin: 8px 0 0 0;\">Overall: <strong class=\"sev-{{ overall }}\">{{ overall.upper() }}</strong></p>
    </div>
    
    <div class=\"main-content\">
      <div class=\"status-panel\">
        <div class=\"grid\">
          {% for s in systems %}
            <div class=\"tile\">
              <h2 style=\"margin: 0 0 8px 0; font-size: 1.2em;\">{{ s.name }}</h2>
              {% if s.url %}<p style=\"margin: 4px 0;\"><a href=\"{{ s.url }}\" target=\"_blank\" rel=\"noreferrer\">Open native UI</a></p>{% endif %}
              <p class=\"muted\" style=\"margin: 4px 0;\">Cache: {{ s.cache_state }}</p>
              <p style=\"margin: 4px 0;\">Attention: <span class=\"sev-critical\">{{ s.critical }}</span> critical, <span class=\"sev-warn\">{{ s.warn }}</span> warn</p>
            </div>
          {% endfor %}
        </div>

        <h2>Attention</h2>
        {% if attention %}
          <ul>
            {% for a in attention %}
              <li><strong class=\"sev-{{ a.severity }}\">{{ a.severity }}</strong> {{ a.system }} — {{ a.message }}</li>
            {% endfor %}
          </ul>
        {% else %}
          <p class=\"muted\">none</p>
        {% endif %}
      </div>
      
      <div class=\"chat-panel\">
        <div class=\"chat-header\">
          <h3 style=\"margin: 0; font-size: 1em;\">Intelligence Layer</h3>
          <p class=\"muted\" style=\"margin: 4px 0 0 0; font-size: 0.85em;\">Ask questions about your infrastructure</p>
        </div>
        
        <div class=\"chat-messages\" id=\"chatMessages\">
          {% if llm_enabled %}
            <div class=\"message assistant\">
              <div class=\"message-label\">Assistant</div>
              <div>Hello! I can help you understand your infrastructure. Try asking:<br>
              • "What needs attention?"<br>
              • "Show me stopped VMs"<br>
              • "Are there any down devices?"<br>
              • "What's the status of FreePBX?"</div>
            </div>
          {% else %}
            <div class=\"chat-disabled\">
              LLM integration not configured.<br><br>
              Add an 'llm' section to config.yaml:<br>
              <pre style=\"text-align: left; background: white; padding: 12px; border-radius: 4px; font-size: 0.85em;\">llm:
  enabled: true
  provider: openai  # or anthropic, github
  api_key: $OPENAI_API_KEY
  model: gpt-4</pre>
            </div>
          {% endif %}
        </div>
        
        {% if llm_enabled %}
        <div class=\"chat-input-container\">
          <form id=\"chatForm\" onsubmit=\"sendMessage(event)\">
            <input type=\"text\" 
                   class=\"chat-input\" 
                   id=\"chatInput\" 
                   placeholder=\"Ask about your infrastructure...\" 
                   autocomplete=\"off\">
          </form>
        </div>
        {% endif %}
      </div>
    </div>
    
    {% if llm_enabled %}
    <script>
      async function sendMessage(event) {
        event.preventDefault();
        
        const input = document.getElementById('chatInput');
        const messages = document.getElementById('chatMessages');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message
        const userDiv = document.createElement('div');
        userDiv.className = 'message user';
        userDiv.innerHTML = '<div class=\"message-label\">You</div><div>' + escapeHtml(message) + '</div>';
        messages.appendChild(userDiv);
        
        // Clear input and scroll
        input.value = '';
        messages.scrollTop = messages.scrollHeight;
        
        // Add loading message
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message assistant loading';
        loadingDiv.innerHTML = '<div class=\"message-label\">Assistant</div><div>Thinking...</div>';
        messages.appendChild(loadingDiv);
        messages.scrollTop = messages.scrollHeight;
        
        // Send to backend
        try {
          const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
          });
          
          const data = await response.json();
          
          // Remove loading message
          messages.removeChild(loadingDiv);
          
          // Add response
          const responseDiv = document.createElement('div');
          if (data.error) {
            responseDiv.className = 'message error';
            responseDiv.innerHTML = '<div class=\"message-label\">Error</div><div>' + escapeHtml(data.error) + '</div>';
          } else {
            responseDiv.className = 'message assistant';
            responseDiv.innerHTML = '<div class=\"message-label\">Assistant</div><div>' + escapeHtml(data.response) + '</div>';
          }
          messages.appendChild(responseDiv);
          
        } catch (error) {
          messages.removeChild(loadingDiv);
          const errorDiv = document.createElement('div');
          errorDiv.className = 'message error';
          errorDiv.innerHTML = '<div class=\"message-label\">Error</div><div>Failed to send message: ' + escapeHtml(error.message) + '</div>';
          messages.appendChild(errorDiv);
        }
        
        messages.scrollTop = messages.scrollHeight;
      }
      
      function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
      }
    </script>
    {% endif %}
  </body>
</html>
"""


@app.get("/")
def index():
    repo_root = _repo_root()
    config_path = Path(os.environ.get("SHTOPS_CONFIG") or (repo_root / "config" / "config.yaml"))

    raw = load_raw_config(config_path=config_path)
    app_cfg = load_app_config(config_path=config_path)

    cache_dir = _resolve_path(repo_root, str(app_cfg.cache.directory))
    ttl = int(app_cfg.cache.default_ttl_seconds)

    report = collect_status(cache_dir=cache_dir, ttl_seconds=ttl)

    def cache_state(system: str) -> str:
        cf = report.cache.get(system)
        if not cf:
            return "missing"
        if cf.error:
            return "error"
        if not cf.exists:
            return "missing"
        return "fresh" if cf.is_fresh else "stale"

    def counts(system: str) -> dict[str, int]:
        warn = sum(1 for a in report.attention if a.system == system and a.severity == "warn")
        crit = sum(1 for a in report.attention if a.system == system and a.severity == "critical")
        return {"warn": warn, "critical": crit}

    systems = [
        {"key": "librenms", "name": "LibreNMS", "url": (raw.get("librenms", {}) or {}).get("url")},
        {"key": "proxmox", "name": "Proxmox", "url": (raw.get("proxmox", {}) or {}).get("url")},
        {"key": "freepbx", "name": "FreePBX", "url": (raw.get("freepbx", {}) or {}).get("url")},
        {"key": "unifi", "name": "UniFi", "url": (raw.get("unifi", {}) or {}).get("url")},
    ]

    for s in systems:
        c = counts(s["key"])
        s["warn"] = c["warn"]
        s["critical"] = c["critical"]
        s["cache_state"] = cache_state(s["key"])

    # Check if LLM is configured
    llm_enabled = raw.get("llm", {}).get("enabled", False) if raw.get("llm") else False
    
    return render_template_string(
        TEMPLATE,
        overall=report.overall_status,
        systems=systems,
        attention=report.attention,
        llm_enabled=llm_enabled,
    )


@app.post("/api/chat")
def chat():
    """Handle LLM chat queries."""
    repo_root = _repo_root()
    config_path = Path(os.environ.get("SHTOPS_CONFIG") or (repo_root / "config" / "config.yaml"))
    
    raw = load_raw_config(config_path=config_path)
    app_cfg = load_app_config(config_path=config_path)
    
    cache_dir = _resolve_path(repo_root, str(app_cfg.cache.directory))
    
    # Create LLM client
    llm_client = create_llm_client(raw, cache_dir)
    
    if not llm_client:
        return jsonify({"error": "LLM not configured"}), 400
    
    # Get user message
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400
    
    user_message = data["message"]
    
    # Query LLM
    result = llm_client.query(user_message)
    
    if "error" in result:
        return jsonify(result), 500
    
    return jsonify(result)


def main() -> int:
    app.run(host=os.environ.get("SHTOPS_HOST", "127.0.0.1"), port=int(os.environ.get("SHTOPS_PORT", "5000")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
