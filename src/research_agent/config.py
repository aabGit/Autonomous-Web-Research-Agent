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
    ollama_api_key: str = ""
    ollama_host: str = ""

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"

    aws_region: str = ""
    bedrock_model_id: str = ""

    tavily_api_key: str = ""

    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "autonomous-web-research-agent"

    chroma_path: str = ".chroma"
    chroma_collection: str = "research_memory"
    vector_db: str = "auto"
    pinecone_api_key: str = ""
    pinecone_index: str = "research-memory"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_embed_model: str = "llama-text-embed-v2"
    max_research_loops: int = 1
    search_results_per_query: int = 2
    max_page_chars: int = 3000
    max_pages_per_run: int = 6
    fetch_timeout_seconds: float = 8.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
