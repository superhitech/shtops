"""
Test LLM integration with mock data.

This script demonstrates the LLM client without needing actual cache files.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from clients.llm_client import LLMClient, LLMConfig


def main():
    # Create a temporary test directory with mock cache data
    test_cache_dir = Path(__file__).parent.parent / "cache"
    
    if not test_cache_dir.exists():
        print(f"Cache directory not found: {test_cache_dir}")
        print("Run collectors first: shtops collect")
        return 1
    
    # Check if LLM is configured (via environment variable)
    import os
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("Error: No API key found.")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable.")
        print()
        print("Example:")
        print("  export OPENAI_API_KEY='sk-...'")
        print("  python test_llm_integration.py")
        return 1
    
    # Determine provider based on which key is set
    if os.getenv("OPENAI_API_KEY"):
        provider = "openai"
        model = "gpt-4"
    elif os.getenv("ANTHROPIC_API_KEY"):
        provider = "anthropic"
        model = "claude-3-sonnet-20240229"
    else:
        provider = "openai"
        model = "gpt-4"
    
    print(f"Using {provider} with model {model}")
    print(f"Cache directory: {test_cache_dir}")
    print()
    
    # Create LLM config
    config = LLMConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        temperature=0.7,
        max_tokens=1000,
    )
    
    # Create client
    client = LLMClient(config, test_cache_dir)
    
    # Test queries
    test_queries = [
        "What needs attention in my infrastructure?",
        "Show me the status of all VMs.",
        "Are there any devices that are down?",
        "What's the overall health status?",
    ]
    
    print("Testing LLM integration...\n")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        
        result = client.query(query)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(result["response"])
        
        print()
    
    print("=" * 60)
    print("\nInteractive mode: Enter your questions (or 'quit' to exit)")
    print()
    
    while True:
        try:
            query = input("You: ").strip()
            if not query:
                continue
            if query.lower() in ["quit", "exit", "q"]:
                break
            
            result = client.query(query)
            
            if "error" in result:
                print(f"Error: {result['error']}\n")
            else:
                print(f"Assistant: {result['response']}\n")
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            break
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
