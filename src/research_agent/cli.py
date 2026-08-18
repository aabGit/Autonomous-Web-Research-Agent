from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from research_agent.graph import AGENT
from research_agent.nodes import initial_state


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Autonomous web research agent")
    parser.add_argument("question", nargs="+", help="Research question")
    parser.add_argument("--json", action="store_true", help="Print raw state as JSON")
    args = parser.parse_args()
    question = " ".join(args.question)

    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
        print("LangSmith tracing is on.")

    print(f"\nResearching: {question}\n")
    final = AGENT.invoke(initial_state(question))

    if args.json:
        print(json.dumps(final, indent=2, default=str))
        return

    print("Plan:")
    for item in final.get("plan") or []:
        print(f"  - {item}")
    print("\nReport:\n")
    print(final.get("report") or "(empty)")
    print("\nSources:")
    for url in dict.fromkeys(final.get("sources") or []):
        print(f"  - {url}")


if __name__ == "__main__":
    main()
