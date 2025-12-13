"""LLM Client for SHTops Intelligence Layer

Provides natural language interface to cached operational data.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    provider: str  # "openai", "anthropic", "github"
    api_key: str
    model: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000


class LLMClient:
    """Client for LLM interaction with cached operational data."""

    def __init__(self, config: LLMConfig, cache_dir: Path):
        self.config = config
        self.cache_dir = cache_dir

    def _load_cache_context(self) -> str:
        """Load all cache files and format as context for LLM."""
        context_parts = ["# SHTops Operational Context\n"]
        
        cache_files = ["librenms.json", "proxmox.json", "freepbx.json", "unifi.json"]
        
        for cache_file in cache_files:
            cache_path = self.cache_dir / cache_file
            if cache_path.exists():
                try:
                    with open(cache_path) as f:
                        data = json.load(f)
                    
                    system_name = cache_file.replace(".json", "").upper()
                    context_parts.append(f"\n## {system_name} Data\n")
                    context_parts.append(f"Collected: {data.get('collected_at', 'unknown')}\n")
                    
                    # Summarize key data for each system
                    if "devices" in data:  # LibreNMS
                        total = len(data["devices"])
                        down = sum(1 for d in data["devices"] if d.get("status") == 0)
                        context_parts.append(f"Devices: {total} total, {down} down\n")
                        if down > 0:
                            context_parts.append("Down devices:\n")
                            for d in data["devices"]:
                                if d.get("status") == 0:
                                    context_parts.append(f"  - {d.get('hostname')} ({d.get('os')})\n")
                    
                    elif "cluster" in data:  # Proxmox
                        resources = data.get("cluster", {}).get("resources", [])
                        vms = [r for r in resources if r.get("type") == "qemu"]
                        running = sum(1 for vm in vms if vm.get("status") == "running")
                        stopped = sum(1 for vm in vms if vm.get("status") == "stopped")
                        context_parts.append(f"VMs: {len(vms)} total ({running} running, {stopped} stopped)\n")
                        if stopped > 0:
                            context_parts.append("Stopped VMs:\n")
                            for vm in vms:
                                if vm.get("status") == "stopped":
                                    context_parts.append(f"  - {vm.get('name')} (VM {vm.get('vmid')})\n")
                    
                    elif "extensions" in data:  # FreePBX
                        exts = data.get("extensions", [])
                        unavailable = sum(1 for e in exts if "Unavailable" in e.get("status", ""))
                        context_parts.append(f"Extensions: {len(exts)} total, {unavailable} unavailable\n")
                    
                    # Include full data as JSON for detailed queries
                    context_parts.append(f"\nFull {system_name} data:\n```json\n")
                    context_parts.append(json.dumps(data, indent=2)[:5000])  # Limit size
                    context_parts.append("\n```\n")
                    
                except Exception as e:
                    context_parts.append(f"Error loading {cache_file}: {e}\n")
        
        return "".join(context_parts)

    def query(self, user_message: str) -> Dict[str, Any]:
        """
        Send a query to the LLM with operational context.
        
        Args:
            user_message: Natural language query from user
            
        Returns:
            Dict with 'response' (str) and optionally 'error' (str)
        """
        try:
            context = self._load_cache_context()
            
            if self.config.provider == "openai":
                return self._query_openai(user_message, context)
            elif self.config.provider == "anthropic":
                return self._query_anthropic(user_message, context)
            elif self.config.provider == "github":
                return self._query_github_models(user_message, context)
            else:
                return {"error": f"Unsupported LLM provider: {self.config.provider}"}
                
        except Exception as e:
            return {"error": f"LLM query failed: {str(e)}"}

    def _query_openai(self, user_message: str, context: str) -> Dict[str, Any]:
        """Query OpenAI API."""
        url = self.config.base_url or "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        system_prompt = (
            "You are an operational intelligence assistant for SHTops, a platform that monitors "
            "IT infrastructure across LibreNMS, Proxmox, FreePBX, and UniFi. "
            "Answer questions about system status, health, and issues based on the provided context. "
            "Be concise and actionable. Highlight critical issues first."
        )
        
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\n---\n\nUser question: {user_message}"},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return {"response": result["choices"][0]["message"]["content"]}

    def _query_anthropic(self, user_message: str, context: str) -> Dict[str, Any]:
        """Query Anthropic Claude API."""
        url = self.config.base_url or "https://api.anthropic.com/v1/messages"
        
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        system_prompt = (
            "You are an operational intelligence assistant for SHTops, a platform that monitors "
            "IT infrastructure across LibreNMS, Proxmox, FreePBX, and UniFi. "
            "Answer questions about system status, health, and issues based on the provided context. "
            "Be concise and actionable. Highlight critical issues first."
        )
        
        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": f"{context}\n\n---\n\nUser question: {user_message}"},
            ],
            "temperature": self.config.temperature,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return {"response": result["content"][0]["text"]}

    def _query_github_models(self, user_message: str, context: str) -> Dict[str, Any]:
        """Query GitHub Models API (OpenAI-compatible)."""
        url = "https://models.inference.ai.azure.com/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        system_prompt = (
            "You are an operational intelligence assistant for SHTops, a platform that monitors "
            "IT infrastructure across LibreNMS, Proxmox, FreePBX, and UniFi. "
            "Answer questions about system status, health, and issues based on the provided context. "
            "Be concise and actionable. Highlight critical issues first."
        )
        
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\n---\n\nUser question: {user_message}"},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return {"response": result["choices"][0]["message"]["content"]}


def create_llm_client(config_dict: Dict[str, Any], cache_dir: Path) -> Optional[LLMClient]:
    """
    Factory function to create an LLM client from config dict.
    
    Returns None if LLM is not configured.
    """
    if "llm" not in config_dict:
        return None
    
    llm_config_dict = config_dict["llm"]
    
    # Check if enabled
    if not llm_config_dict.get("enabled", False):
        return None
    
    # Get API key from env var if specified with $ prefix
    api_key = llm_config_dict.get("api_key", "")
    if api_key.startswith("$"):
        env_var = api_key[1:]
        api_key = os.getenv(env_var, "")
        if not api_key:
            return None
    
    llm_config = LLMConfig(
        provider=llm_config_dict.get("provider", "openai"),
        api_key=api_key,
        model=llm_config_dict.get("model", "gpt-4"),
        base_url=llm_config_dict.get("base_url"),
        temperature=llm_config_dict.get("temperature", 0.7),
        max_tokens=llm_config_dict.get("max_tokens", 2000),
    )
    
    return LLMClient(llm_config, cache_dir)
