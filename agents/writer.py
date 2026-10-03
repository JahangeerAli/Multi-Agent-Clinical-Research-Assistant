import re
import config
from agents.base import make_agent, run_task

ID_PATTERN = re.compile(r"^(\d{6,9}|DOC\d+-\d+)$")


def run(state):
    evidence = state["evidence"]
    if not evidence:
        return {"final": "No evidence could be retrieved for this question.",
                "citations": [], "unverified_pmids": []}

    agent = make_agent(
        role="Clinical Evidence Writer",
        goal="Write a safe, accurate, citation-backed clinical evidence summary.",
        backstory="You are a medical writer. You use ONLY the evidence you are given, "
                  "never invent a citation, hedge uncertainty, clearly state when evidence "
                  "is weak or contradictory, and never give patient-specific medical advice.",
        model=config.SMART_MODEL,
        temperature=0.3,
        max_tokens=2500,
    )
    listing = "\n\n".join(
        f"ID {e['id']} | {e['year']} | {', '.join(e['pub_types'][:3])} | {e['journal']}\n"
        f"Title: {e['title']}\nText: {e['abstract']}"
        for e in evidence
    )
    critique = state.get("critique") or {}
    description = (
        f"Clinical question: {state['question']}\n"
        f"Critic's notes: {critique.get('notes', '')}\n\nEvidence:\n{listing}\n\n"
        "Write a structured markdown summary with these sections: Background, Key Findings, "
        "Evidence Quality, Clinical Considerations, References. "
        "Cite every claim with its ID in square brackets, exactly as given above, "
        "for example [12345678] for PubMed or [DOC1-3] for a PDF. "
        "Never use an ID that is not in the evidence list."
    )
    text = run_task(agent, description, "A markdown clinical summary with bracketed ID citations.")

    # Anti-hallucination check: every cited ID must exist in our evidence
    cited = set()
    for group in re.findall(r"\[([^\]]+)\]", text):
        for token in re.split(r"[,;\s]+", group):
            if ID_PATTERN.match(token):
                cited.add(token)
    valid = {e["id"] for e in evidence}
    citations = [{**e, "cited_in_summary": e["id"] in cited} for e in evidence]
    return {"final": text, "citations": citations,
            "unverified_pmids": sorted(cited - valid)}
