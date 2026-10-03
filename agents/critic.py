import config
from agents.base import make_agent, run_task, parse_json


def run(state):
    evidence = state["evidence"]
    if not evidence:
        return {"critique": {"sufficient": False, "score": 0.0,
                             "notes": "No evidence found.", "gaps": ["No evidence retrieved"]}}

    agent = make_agent(
        role="Clinical Evidence Critic",
        goal="Judge whether the retrieved evidence is strong enough to answer the question.",
        backstory="You are a strict evidence-based-medicine reviewer. You rank "
                  "meta-analyses and RCTs above cohort studies and case reports, and you "
                  "check relevance, recency and contradictions.",
        model=config.FAST_MODEL,
    )
    listing = "\n".join(
        f"[{e['id']}] ({e['year']}) {', '.join(e['pub_types'][:3])} | {e['title']} | {e['abstract'][:350]}"
        for e in evidence
    )
    description = (f"Clinical question: {state['question']}\n\nEvidence:\n{listing}\n\n"
                   "Score how sufficient this evidence is for answering the question.")
    expected = ('Only a JSON object with three keys: "score" (a number from 0.0 to 1.0), '
                '"notes" (a short assessment string) and "gaps" (a list of missing topics). '
                "No other text.")

    out = parse_json(run_task(agent, description, expected))
    try:
        score = float(out.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    return {"critique": {"sufficient": score >= 0.6, "score": score,
                         "notes": out.get("notes", ""), "gaps": out.get("gaps", [])}}
