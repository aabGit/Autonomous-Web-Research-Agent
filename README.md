# Autonomous Web Research Agent

A teaching project: one Python agent that **plans**, **searches the web**, **stores notes in RAG**, **writes a report**, then **critiques itself** and loops until the answer is good enough.

Stack: **Python 3.11+ · LangChain · LangGraph · MCP · Chroma RAG · LangSmith**

## What you are building (classroom map)

| Piece | File | Job |
| --- | --- | --- |
| Config | `src/research_agent/config.py` | Reads `.env` |
| LLM layer | `src/research_agent/llm.py` | One function, many providers |
| Tools | `src/research_agent/tools.py` | Search + fetch pages |
| MCP | `src/research_agent/mcp_server.py` | Same tools over the MCP protocol |
| RAG | `src/research_agent/rag.py` | Remember pages in Chroma |
| State | `src/research_agent/state.py` | The graph's notebook |
| Nodes | `src/research_agent/nodes.py` | One function per step |
| Graph | `src/research_agent/graph.py` | Wires the loop |
| CLI | `src/research_agent/cli.py` | Run from terminal |
| API | `src/research_agent/api.py` | FastAPI backend |

Read [TEACHING.md](TEACHING.md) for the full lesson.

## Setup

```bash
cd ~/Projects/autonomous-web-research-agent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Put at least one LLM key in `.env` (`OPENAI_API_KEY` is the default path). Search works with free DuckDuckGo. Add `TAVILY_API_KEY` later if you want higher-quality search. Add `LANGCHAIN_API_KEY` to watch traces in LangSmith.

## Run a research job

```bash
python -m research_agent.cli "How does MCP differ from a normal LangChain tool?"
```

## Run the backend

```bash
python -m research_agent.api
# POST http://127.0.0.1:8001/research  {"question": "..."}
```

## Run the MCP server (for Cursor / other hosts)

```bash
python -m research_agent.mcp_server
```

Example Cursor MCP config:

```json
{
  "mcpServers": {
    "research-tools": {
      "command": "/Users/YOU/Projects/autonomous-web-research-agent/.venv/bin/python",
      "args": ["-m", "research_agent.mcp_server"]
    }
  }
}
```

## Tests (no API key needed)

```bash
pytest
```
