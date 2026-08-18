"""MCP server: same tools, standard protocol.

Run:  python -m research_agent.mcp_server

Cursor / Claude Desktop can attach this server and call web_search / fetch_url
without importing this Python package.
"""

from mcp.server.mcpserver import MCPServer

from research_agent.tools import fetch_url, web_search

mcp = MCPServer("research-tools")


@mcp.tool()
def search_web(query: str) -> str:
    """Search the public web and return titles, URLs, and snippets."""
    hits = web_search(query)
    if not hits:
        return "No results."
    lines = [f"- {hit['title']} | {hit['url']}\n  {hit['snippet']}" for hit in hits]
    return "\n".join(lines)


@mcp.tool()
def fetch_page(url: str) -> str:
    """Download a URL and return cleaned visible text."""
    try:
        return fetch_url(url)
    except Exception as exc:
        return f"Could not fetch {url}: {exc}"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
