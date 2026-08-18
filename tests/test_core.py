from fastapi.testclient import TestClient

from research_agent.api import app
from research_agent.config import Settings
from research_agent.graphql_schema import schema
from research_agent.llm import get_chat_model
from research_agent.nodes import _json_from_model, should_continue
from research_agent.pinecone_store import uses_pinecone
from research_agent.rag import chunk_text
from research_agent.state import ResearchState


def test_uses_chroma_without_pinecone_key():
    assert uses_pinecone(Settings(vector_db="auto", pinecone_api_key="")) is False
    assert uses_pinecone(Settings(vector_db="chroma", pinecone_api_key="sk")) is False


def test_pinecone_mode_requires_api_key():
    try:
        uses_pinecone(Settings(vector_db="pinecone", pinecone_api_key=""))
    except RuntimeError as exc:
        assert "PINECONE_API_KEY" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_chunk_text_splits_long_input():
    text = " ".join(f"w{i}" for i in range(50))
    chunks = chunk_text(text, size=10, overlap=2)
    assert len(chunks) > 1
    assert chunks[0].startswith("w0")


def test_json_from_model_strips_fences():
    raw = '```json\n{"done": true, "gaps": []}\n```'
    assert _json_from_model(raw) == {"done": True, "gaps": []}


def test_should_continue_routes():
    done: ResearchState = {
        "question": "q",
        "plan": [],
        "findings": [],
        "sources": [],
        "report": "",
        "gaps": [],
        "loop": 1,
        "done": True,
        "ingested_urls": [],
    }
    assert should_continue(done) == "end"
    done["done"] = False
    assert should_continue(done) == "search"


def test_unknown_llm_provider():
    try:
        get_chat_model(settings=Settings(llm_provider="vertex"))
    except ValueError as exc:
        assert "azure" in str(exc)
        assert "bedrock" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_openai_and_azure_require_config():
    try:
        get_chat_model(settings=Settings(llm_provider="openai", openai_api_key=""))
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")

    try:
        get_chat_model(
            settings=Settings(
                llm_provider="azure",
                azure_openai_api_key="sk",
                azure_openai_endpoint="",
            )
        )
    except RuntimeError as exc:
        assert "AZURE_OPENAI_ENDPOINT" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_bedrock_requires_model_id():
    try:
        get_chat_model(settings=Settings(llm_provider="bedrock", bedrock_model_id=""))
    except RuntimeError as exc:
        assert "BEDROCK_MODEL_ID" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_graphql_schema_and_health_query():
    printed = str(schema)
    assert "research" in printed
    assert "health" in printed
    client = TestClient(app)
    response = client.post("/graphql", json={"query": "{ health }"})
    assert response.status_code == 200
    assert response.json()["data"]["health"] is True

