from agents import planner, retriever, critic, writer
import config


def run_pipeline(question, on_step=None, pdf_index=None):
    log = on_step or (lambda msg: None)
    state = {"question": question, "plan": "", "sub_queries": [], "evidence": [],
             "critique": None, "final": "", "loop_count": 0, "pdf_index": pdf_index}

    while True:
        log(f"🧭 Planner agent: round {state['loop_count'] + 1}")
        state.update(planner.run(state))
        log(f"   Sub-queries: {state['sub_queries']}")

        log("🔎 Retriever agent: searching PubMed and your PDFs...")
        state.update(retriever.run(state))
        log(f"   Evidence collected: {len(state['evidence'])} items")

        log("🧪 Critic agent: grading evidence...")
        state.update(critic.run(state))
        state["loop_count"] += 1
        log(f"   Score {state['critique']['score']:.2f} | sufficient: {state['critique']['sufficient']}")

        if state["critique"]["sufficient"] or state["loop_count"] >= config.MAX_LOOPS:
            break

    log("✍️ Writer agent: drafting summary...")
    state.update(writer.run(state))
    return state
