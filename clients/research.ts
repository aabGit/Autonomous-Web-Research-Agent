/**
 * Tiny REST client for the research agent. Not a product UI.
 *
 * Usage (Node 18+):
 *   import { runResearch } from "./research.ts";
 *   const result = await runResearch("What is LangGraph?");
 */
export type ResearchResponse = {
  question: string;
  plan: string[];
  report: string;
  sources: string[];
  loops: number;
};

export async function runResearch(
  question: string,
  baseUrl = "http://127.0.0.1:8001",
): Promise<ResearchResponse> {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    throw new Error(`Research API ${response.status}: ${await response.text()}`);
  }
  return (await response.json()) as ResearchResponse;
}
