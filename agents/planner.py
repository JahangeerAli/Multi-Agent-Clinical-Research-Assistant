import config
from agents.base import make_agent, run_task, parse_json


def run(state):
    agent = make_agent(
        role="Clinical Research Planner",
        goal="Turn a clinical question into focused PubMed search queries.",
        backstory="You are an experienced medical librarian who writes precise "
                  "keyword-style PubMed searches.",
        model=config.FAST_MODEL,
    )
    description = (
        f"Clinical question: {state['question']}\n"
        "Break it into 3-4 focused PubMed search queries in keyword style, for example "
        "GLP-1 receptor agonist heart failure randomized trial.\n"
    )
    if state.get("critique"):
        description += (
            f"A previous round found these gaps: {state['critique'].get('gaps')}\n"
            f"Queries already used: {state['sub_queries']}\n"
            "Write NEW queries that target the gaps.\n"
        )
    expected = ('Only a JSON object with two keys: "plan" (a 2-3 sentence research plan '
                'as a string) and "sub_queries" (a list of 3-4 query strings). No other text.')

    out = parse_json(run_task(agent, description, expected))
    queries = [q for q in out.get("sub_queries", []) if isinstance(q, str)][:4]
    return {"plan": out.get("plan", ""), "sub_queries": queries or [state["question"]]}
