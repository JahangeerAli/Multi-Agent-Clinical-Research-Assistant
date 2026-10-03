import time
from crewai.tools import tool
from agents.base import make_agent, run_task
from tools.pubmed import search_pubmed
from tools.pdf_store import search
import config


def _pdf_to_evidence(c):
    return {
        "id": c["id"],
        "title": f"{c['filename']} (page {c['page']})",
        "abstract": c["text"],
        "journal": "PDF library",
        "year": "n/a",
        "pub_types": [],
        "url": "",
        "source": "pdf",
    }


def _make_tools(collector, pdf_index):
    """Create the two CrewAI tools. They store everything they find in `collector`."""

    @tool("pubmed_search")
    def pubmed_search(query: str) -> str:
        """Search PubMed for clinical research papers. Input is one short keyword query.
        Returns the PMIDs and titles of the papers found."""
        time.sleep(0.4)
        try:
            papers = search_pubmed(query, config.RESULTS_PER_QUERY)
        except Exception as e:
            return f"PubMed error: {e}"
        lines = []
        for p in papers:
            if p["abstract"]:
                collector.setdefault(p["id"], p)
                lines.append(f"PMID {p['id']} ({p['year']}): {p['title'][:120]}")
        return "\n".join(lines) or "No papers found."

    @tool("pdf_search")
    def pdf_search(query: str) -> str:
        """Search the internal PDF library by meaning. Input is one short query.
        Returns the PDF passages found."""
        lines = []
        for c in search(query, pdf_index, k=2):
            collector.setdefault(c["id"], _pdf_to_evidence(c))
            lines.append(f"{c['id']}: {c['filename']} page {c['page']}")
        return "\n".join(lines) or "No matching PDF passages."

    return [pubmed_search, pdf_search]


def run(state):
    collector = {}
    pdf_index = state.get("pdf_index")
    tools = _make_tools(collector, pdf_index)

    agent = make_agent(
        role="Medical Literature Retriever",
        goal="Collect relevant evidence from PubMed and the PDF library for every query.",
        backstory="You are a careful research assistant. You always use your search tools "
                  "and never make up papers.",
        model=config.SMART_MODEL,
        tools=tools,
        max_iter=10,
    )
    query_list = "\n".join(f"- {q}" for q in state["sub_queries"])
    description = (
        "For EACH of the search queries below, call the pubmed_search tool once "
        "and the pdf_search tool once.\n"
        f"Queries:\n{query_list}\n"
        "When all searches are done, reply with one short sentence."
    )
    try:
        run_task(agent, description, "One short sentence confirming the searches are done.")
    except Exception:
        pass  # the fallback below handles it

    # Fallback: if the agent did not use the tools properly, search directly
    if not any(e["source"] == "pubmed" for e in collector.values()):
        for q in state["sub_queries"]:
            try:
                for p in search_pubmed(q, config.RESULTS_PER_QUERY):
                    if p["abstract"]:
                        collector.setdefault(p["id"], p)
            except Exception:
                pass
            for c in search(q, pdf_index, k=2):
                collector.setdefault(c["id"], _pdf_to_evidence(c))
            time.sleep(0.4)

    found = {e["id"]: e for e in state["evidence"]}   # keep evidence from earlier rounds
    for key, item in collector.items():
        found.setdefault(key, item)

    items = list(found.values())
    pubmed = [e for e in items if e["source"] == "pubmed"][: config.MAX_EVIDENCE]
    pdfs = [e for e in items if e["source"] == "pdf"][: config.MAX_PDF_EVIDENCE]
    return {"evidence": pubmed + pdfs}
