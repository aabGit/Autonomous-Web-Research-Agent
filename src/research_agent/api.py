from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from research_agent.graph import AGENT
from research_agent.graphql_schema import graphql_router
from research_agent.nodes import initial_state

STEP_LABELS = {
    "plan": "Planning search queries (LLM)",
    "search": "Searching the web and fetching pages",
    "ingest": "Storing webpage chunks (RAG)",
    "synthesize": "Writing the cited report",
    "critique": "Checking if the answer is good enough",
}

load_dotenv()

app = FastAPI(title="Autonomous Web Research Agent", version="0.1.0")
app.include_router(graphql_router, prefix="/graphql")

HOME_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Research agent</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; color: #111; }
    textarea { width: 100%; min-height: 6rem; font: inherit; padding: 0.6rem; }
    button { margin-top: 0.6rem; padding: 0.5rem 1rem; font: inherit; cursor: pointer; }
    button:disabled { opacity: 0.6; cursor: wait; }
    .muted { color: #555; font-size: 0.9rem; }
    #loader { display: none; align-items: center; gap: 0.85rem; margin: 1rem 0; padding: 0.85rem 1rem; background: #f0faf8; border: 1px solid #bfe8e0; border-radius: 8px; }
    #loader.on { display: flex; }
    .spin { width: 28px; height: 28px; border: 3px solid #d5ebe7; border-top-color: #0F9B8E; border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .timer { font-variant-numeric: tabular-nums; font-size: 1.35rem; font-weight: 650; }
    .step { margin: 0; }
    .result { margin-top: 1.25rem; }
    .result h2 { font-size: 1.05rem; margin: 1.2rem 0 0.4rem; color: #0B7268; }
    .result h3, .result h4 { font-size: 1rem; margin: 0.9rem 0 0.35rem; }
    .result ul, .result ol { padding-left: 1.25rem; margin: 0.35rem 0 0.7rem; }
    .result li { margin: 0.28rem 0; line-height: 1.45; }
    .result p { line-height: 1.5; margin: 0.4rem 0; }
    .result a { color: #0B7268; word-break: break-all; }
    .result .fail { background: #fdecea; padding: 0.8rem; border-radius: 8px; }
  </style>
</head>
<body>
  <h1>Autonomous web research agent</h1>
  <p class="muted">Type a question and submit. Typical time is 1–3 minutes. The timer is elapsed time. The report is formatted as lists and headings — not raw JSON.</p>
  <p class="muted">JSON ping is <a href="/health">/health</a>. API form is <a href="/docs">/docs</a>. GraphQL is <a href="/graphql">/graphql</a>.</p>
  <textarea id="q" placeholder="How does MCP differ from a LangChain tool?"></textarea>
  <div><button id="go" type="button">Run research</button></div>
  <div id="loader">
    <div class="spin" aria-hidden="true"></div>
    <div>
      <div class="timer" id="clock">0:00</div>
      <p class="step" id="status">Starting…</p>
      <p class="muted" id="hint">Typical 1–3 min. Do not close this tab.</p>
    </div>
  </div>
  <article id="out" class="result"></article>
  <script>
    const q = document.getElementById("q");
    const go = document.getElementById("go");
    const status = document.getElementById("status");
    const hint = document.getElementById("hint");
    const out = document.getElementById("out");
    const loader = document.getElementById("loader");
    const clock = document.getElementById("clock");
    const TYPICAL = 120;
    function fmt(sec) {
      const m = Math.floor(sec / 60);
      const s = String(sec % 60).padStart(2, "0");
      return m + ":" + s;
    }
    function esc(text) {
      return String(text == null ? "" : text)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
    function safeHref(href) {
      const raw = String(href || "").trim();
      if (!/^https?:\/\//i.test(raw)) return "";
      return raw.replace(/"/g, "");
    }
    function inlineMd(text) {
      let t = esc(text);
      t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function (_m, label, url) {
        const href = safeHref(url);
        return href ? ('<a href="' + href + '" target="_blank" rel="noopener noreferrer">' + label + "</a>") : label;
      });
      t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
      t = t.replace(/(https?:\/\/[^\s<]+)/g, function (url) {
        const href = safeHref(url);
        return href ? ('<a href="' + href + '" target="_blank" rel="noopener noreferrer">' + esc(url) + "</a>") : esc(url);
      });
      return t;
    }
    function reportHtml(md) {
      const lines = String(md || "No report.").split(/\n/);
      let html = "";
      let list = null;
      function closeList() {
        if (list) { html += list === "ul" ? "</ul>" : "</ol>"; list = null; }
      }
      for (const line of lines) {
        const h = line.match(/^(#{1,3})\s+(.*)$/);
        const ul = line.match(/^[-*]\s+(.*)$/);
        const ol = line.match(/^\d+\.\s+(.*)$/);
        if (h) {
          closeList();
          const tag = "h" + Math.min(h[1].length + 1, 4);
          html += "<" + tag + ">" + inlineMd(h[2]) + "</" + tag + ">";
        } else if (ul) {
          if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
          html += "<li>" + inlineMd(ul[1]) + "</li>";
        } else if (ol) {
          if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
          html += "<li>" + inlineMd(ol[1]) + "</li>";
        } else if (!line.trim()) {
          closeList();
        } else {
          closeList();
          html += "<p>" + inlineMd(line) + "</p>";
        }
      }
      closeList();
      return html;
    }
    function showError(text) {
      out.innerHTML = '<p class="fail">' + esc(text) + "</p>";
    }
    function showResult(data) {
      const plan = Array.isArray(data.plan) ? data.plan : [];
      const sources = Array.isArray(data.sources) ? data.sources : [];
      let html = "<h2>Question</h2><p>" + inlineMd(data.question || "") + "</p>";
      html += "<h2>Plan</h2>";
      html += plan.length
        ? "<ol>" + plan.map(function (item) { return "<li>" + inlineMd(item) + "</li>"; }).join("") + "</ol>"
        : "<p class='muted'>No plan returned.</p>";
      html += "<h2>Report</h2>" + reportHtml(data.report || "");
      html += "<h2>Sources</h2>";
      if (!sources.length) {
        html += "<p class='muted'>No sources.</p>";
      } else {
        html += "<ul>";
        for (const src of sources) {
          const href = safeHref(src);
          html += href
            ? ('<li><a href="' + href + '" target="_blank" rel="noopener noreferrer">' + esc(src) + "</a></li>")
            : ("<li>" + esc(src) + "</li>");
        }
        html += "</ul>";
      }
      if (data.loops != null) html += "<p class='muted'>Loops: " + esc(data.loops) + "</p>";
      out.innerHTML = html;
    }
    go.onclick = async () => {
      const question = q.value.trim();
      if (!question) { status.textContent = "Type a question first."; loader.classList.add("on"); return; }
      go.disabled = true;
      loader.classList.add("on");
      const spin = loader.querySelector(".spin");
      if (spin) spin.style.animation = "";
      out.innerHTML = "";
      const started = Date.now();
      const tick = setInterval(() => {
        const elapsed = Math.floor((Date.now() - started) / 1000);
        clock.textContent = fmt(elapsed);
        const left = Math.max(0, TYPICAL - elapsed);
        hint.textContent = left
          ? ("Elapsed " + fmt(elapsed) + " · typical remaining ~" + fmt(left) + " (not a guarantee)")
          : ("Elapsed " + fmt(elapsed) + " · past the typical 2 min. Still working if the spinner is on.");
      }, 250);
      try {
        const res = await fetch("/research/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question }),
          signal: AbortSignal.timeout(240000)
        });
        if (!res.ok || !res.body) {
          status.textContent = "Request failed (" + res.status + ").";
          showError(await res.text());
          return;
        }
        const reader = res.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const chunks = buf.split("\n\n");
          buf = chunks.pop();
          for (const chunk of chunks) {
            const line = chunk.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim()).join("");
            if (!line) continue;
            let msg;
            try { msg = JSON.parse(line); } catch { continue; }
            if (msg.type === "status") status.textContent = msg.label || msg.step;
            if (msg.type === "error") {
              status.textContent = "Failed.";
              showError(msg.detail || JSON.stringify(msg));
            }
            if (msg.type === "done") {
              status.textContent = "Done in " + fmt(Math.floor((Date.now() - started) / 1000)) + ".";
              hint.textContent = "Typical 1–3 min. This run finished.";
              showResult(msg.result || {});
            }
          }
        }
      } catch (err) {
        status.textContent = "Stopped.";
        showError(String(err));
      } finally {
        clearInterval(tick);
        go.disabled = false;
        const spinEl = loader.querySelector(".spin");
        if (spinEl) spinEl.style.animation = "none";
      }
    };
  </script>
</body>
</html>
"""


class ResearchRequest(BaseModel):
    question: str


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HOME_PAGE


@app.get("/health")
def health() -> dict:
    return {"ok": True}


def _payload(final: dict) -> dict:
    return {
        "question": final["question"],
        "plan": final.get("plan"),
        "report": final.get("report"),
        "sources": list(dict.fromkeys(final.get("sources") or [])),
        "loops": final.get("loop"),
    }


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@app.post("/research")
def research(body: ResearchRequest) -> dict:
    try:
        final = AGENT.invoke(initial_state(body.question))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:800]) from exc
    return _payload(final)


@app.post("/research/stream")
def research_stream(body: ResearchRequest) -> StreamingResponse:
    def events():
        state = initial_state(body.question)
        yield _sse({"type": "status", "step": "start", "label": "Starting the research loop"})
        try:
            for update in AGENT.stream(state, stream_mode="updates"):
                node = next(iter(update))
                patch = update[node]
                if isinstance(patch, dict):
                    state = {**state, **patch}
                yield _sse(
                    {
                        "type": "status",
                        "step": node,
                        "label": STEP_LABELS.get(node, f"Step: {node}"),
                    }
                )
            yield _sse({"type": "done", "result": _payload(state)})
        except Exception as exc:
            yield _sse({"type": "error", "detail": str(exc)[:800]})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "research_agent.api:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8001")),
        reload=False,
    )


if __name__ == "__main__":
    main()
