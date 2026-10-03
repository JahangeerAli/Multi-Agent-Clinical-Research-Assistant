import streamlit as st
import config  # keep this import first (it sets CrewAI environment variables)
from graph.pipeline import run_pipeline
from tools.pdf_store import extract_chunks, build_index, build_library, merge_indexes

st.set_page_config(page_title="Clinical Research Assistant", page_icon="🩺", layout="wide")
st.title("🩺 Multi-Agent Clinical Research Assistant")
st.caption("CrewAI agents: Planner → Retriever → Critic → Writer · Groq (Llama) + PubMed + your PDFs · free stack")
st.warning("Research/education tool only. Not a medical device and not for clinical "
           "decision-making without expert review. Never upload patient data.")

if not config.GROQ_API_KEY:
    st.error("GROQ_API_KEY is missing. Add it in Streamlit Cloud → App settings → Secrets.")
    st.stop()


@st.cache_resource(show_spinner="Building PDF knowledge base (first start only, 1-2 min)...")
def load_library():
    """Reads data/pdfs/*.pdf and creates embeddings once, then remembers them."""
    return build_library(config.PDF_FOLDER)


library = load_library()
st.session_state.setdefault("upload_cache", {})

# ---------- Sidebar ----------
with st.sidebar:
    st.header("📚 Knowledge base")
    st.write(f"Built-in library: **{len(library['chunks'])}** chunks")
    uploads = st.file_uploader("Upload extra PDFs (optional)", type="pdf",
                               accept_multiple_files=True)
    pubmed_only = st.checkbox("Ignore PDFs (PubMed only)", value=False)

indexes = [library]
for f in uploads or []:
    key = f"{f.name}-{f.size}"
    if key not in st.session_state["upload_cache"]:
        with st.spinner(f"Reading {f.name}..."):
            doc_no = 100 + len(st.session_state["upload_cache"])
            chunks = extract_chunks(f, f.name, doc_no=doc_no)
            st.session_state["upload_cache"][key] = build_index(chunks)
    indexes.append(st.session_state["upload_cache"][key])
pdf_index = None if pubmed_only else merge_indexes(indexes)

# ---------- Main ----------
examples = [
    "What is the current evidence for GLP-1 agonists in heart-failure patients?",
    "Prone positioning in acute hypoxemic respiratory failure",
    "SGLT2 inhibitors in diabetic kidney disease",
]
cols = st.columns(len(examples))
for col, ex in zip(cols, examples):
    if col.button(ex, use_container_width=True):
        st.session_state["q"] = ex

question = st.text_area("Clinical question", key="q", height=80)

if st.button("Run research", type="primary") and question.strip():
    with st.status("CrewAI agents working (1-3 minutes)...", expanded=True) as status:
        try:
            result = run_pipeline(question.strip(), on_step=st.write, pdf_index=pdf_index)
            status.update(label="Done ✅", state="complete")
        except Exception as e:
            status.update(label="Failed", state="error")
            st.error(f"Something went wrong: {e}")
            st.stop()

    st.markdown(result["final"])
    if result.get("unverified_pmids"):
        st.error(f"⚠️ Citations not found in retrieved evidence: {result['unverified_pmids']}")

    c = result["critique"]
    with st.expander(f"Critic assessment (score {c['score']:.2f})"):
        st.write(c["notes"])
        st.write("Gaps:", c["gaps"] or "none")
    with st.expander("Research plan & sub-queries"):
        st.write(result["plan"])
        st.write(result["sub_queries"])
    with st.expander(f"Sources ({len(result['evidence'])})"):
        for e in result.get("citations", []):
            used = "✅ cited" if e["cited_in_summary"] else "not cited"
            label = f"[{e['title']}]({e['url']})" if e["url"] else e["title"]
            st.markdown(f"- {label} — {e['journal']}, {e['year']} · ID {e['id']} · {used}")
