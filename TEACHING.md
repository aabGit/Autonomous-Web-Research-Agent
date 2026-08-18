# Lesson: how this research agent thinks

Read this with the code open. Each section is one idea, then where it lives.

## 1. An agent is a loop, not a chatbot

A chatbot answers once. An **agent** has:

1. A **goal** (your question)
2. **Tools** (search, fetch)
3. **Memory** (RAG)
4. A **stop condition** (critique says "done")

LangGraph is the library that draws that loop as a graph of Python functions.

## 2. State is the shared notebook

See `state.py`. Every node receives `ResearchState` and returns only the fields it changed. That is how later nodes see earlier work.

## 3. The LLM layer hides vendors

See `llm.py`. Nodes call `get_chat_model()`. They do not care if you use OpenAI, Anthropic, or Ollama. Change `LLM_PROVIDER` in `.env`.

## 4. Tools vs MCP

`tools.py` is ordinary Python: `web_search()` and `fetch_url()`.

MCP (`mcp_server.py`) is a **protocol** so *other* apps (Cursor, Claude Desktop) can call those same functions without importing this repo. Think: USB for AI tools.

This graph calls the Python functions directly. The MCP server is for Phase-2 interoperability.

## 5. RAG (retrieval augmented generation)

If you paste 20 web pages into the prompt, the model gets lost and you pay more.

RAG:

1. Split text into chunks (`chunk_text`)
2. Store embeddings in Chroma (`ingest_finding`)
3. Ask "what is relevant to this question?" (`retrieve`)
4. Write the report from those notes only

## 6. Walk the graph with your finger

`graph.py`:

```
plan -> search -> ingest -> synthesize -> critique
            ^                               |
            +--------- if gaps -------------+
```

- **plan**: LLM turns one question into search queries
- **search**: DuckDuckGo/Tavily + page fetch
- **ingest**: write chunks into Chroma
- **synthesize**: write the markdown report
- **critique**: JSON `{done, gaps}` — if not done, search the gaps

`MAX_RESEARCH_LOOPS` in `.env` is the safety brake so it cannot loop forever.

## 7. LangSmith

Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY`. Every LLM call shows up as a trace: prompts, tokens, latency. That is how you debug agents in production (the "Phase 2" observability layer).

## 8. Exercises

1. Print `state["plan"]` in the CLI — you already can, look at `cli.py`.
2. Add a third MCP tool: `summarize_url(url)`.
3. Change `should_continue` so the agent stops after 2 sources even if critique is unhappy.
4. Swap `LLM_PROVIDER=ollama` and run locally.

When this feels clear, open the **multi-agent-orchestrator** project. That one has *several* agents and a supervisor that assigns work.
