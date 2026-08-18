from research_agent.nodes import _json_from_model, should_continue
from research_agent.rag import chunk_text
from research_agent.state import ResearchState


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
    }
    assert should_continue(done) == "end"
    done["done"] = False
    assert should_continue(done) == "search"
