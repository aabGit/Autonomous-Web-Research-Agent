"""Autonomous web research agent.

Think of this package as three layers stacked:

1. LLM layer  - one function that returns a chat model (OpenAI, Anthropic, Ollama)
2. Tools/MCP  - web search and page fetch (also exposed as an MCP server)
3. Graph      - LangGraph loop: plan -> search -> remember (RAG) -> write -> critique
"""

__version__ = "0.1.0"
