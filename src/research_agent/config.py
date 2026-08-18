from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All knobs live in environment variables / .env so the code stays clean."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"
    ollama_model: str = "llama3.1"

    tavily_api_key: str = ""

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "autonomous-web-research-agent"

    chroma_path: str = ".chroma"
    chroma_collection: str = "research_memory"
    max_research_loops: int = 3
    search_results_per_query: int = 5
    max_page_chars: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
