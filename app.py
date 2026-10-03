import html as _html
import re
import time
import streamlit as st
import config  # keep this import first (it sets CrewAI environment variables)
from graph.pipeline import run_pipeline
from tools.pdf_store import extract_chunks, build_index, build_library, merge_indexes

st.set_page_config(page_title="Clinical Research Assistant", page_icon="🩺", layout="wide")

# ============================== STYLES ==============================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif; }
.block-container { padding-top: 1.4rem; max-width: 1180px; }
#MainMenu, footer { visibility: hidden; }

.hero {
padding: 30px 34px; border-radius: 22px; color: #fff; margin-bottom: 14px;
background: linear-gradient(135deg, #0ea5e9, #6366f1, #a855f7, #0ea5e9);
background-size: 300% 300%; animation: shift 12s ease infinite;
box-shadow: 0 12px 40px rgba(99,102,241,.35);
}
@keyframes shift { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
.hero h1 { margin: 0; font-size: 2.2rem; font-weight: 800; letter-spacing: -.02em; color: #fff; padding: 0; }
.hero p { margin: 8px 0 16px; font-size: 1.05rem; opacity: .93; }
.pill {
display: inline-block; padding: 5px 13px; margin: 0 8px 6px 0; border-radius: 999px;
background: rgba(255,255,255,.18); border: 1px solid rgba(255,255,255,.35);
font-size: .78rem; font-weight: 600; backdrop-filter: blur(6px);
}
.notice {
padding: 10px 16px; border-radius: 12px; font-size: .85rem; margin-bottom: 18px;
background: rgba(245,158,11,.12); border: 1px solid rgba(245,158,11,.4);
}

.stButton > button {
width: 100%; border-radius: 12px; font-weight: 600; transition: all .2s ease;
border: 1px solid rgba(128,128,128,.35);
}
.stButton > button:hover { transform: translateY(-2px); border-color: #6366f1; }
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
background: linear-gradient(90deg, #0ea5e9, #6366f1, #a855f7); border: 0; color: #fff;
padding: .65rem 1.2rem; box-shadow: 0 8px 24px rgba(99,102,241,.45);
}
.stTextArea textarea { border-radius: 14px; font-size: 1rem; }

.agents { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 8px 0 14px; }
@media (max-width: 760px) { .agents { grid-template-columns: repeat(2, 1fr); } }
.agent {
position: relative; overflow: hidden; border-radius: 16px; padding: 16px;
border: 1px solid rgba(128,128,128,.28); background: rgba(128,128,128,.08); transition: all .35s ease;
}
.agent .ic { font-size: 1.7rem; }
.agent .nm { font-weight: 700; margin-top: 4px; }
.agent .ds { font-size: .78rem; opacity: .7; }
.agent .st { margin-top: 10px; font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; }
.agent.wait { opacity: .5; }
.agent.run {
border-color: #6366f1; animation: pulse 1.5s infinite;
background: linear-gradient(135deg, rgba(14,165,233,.18), rgba(168,85,247,.18));
}
.agent.run::after {
content: ""; position: absolute; left: 0; bottom: 0; height: 3px; width: 100%;
background: linear-gradient(90deg, transparent, #6366f1, transparent); animation: slide 1.2s linear infinite;
}
.agent.done { border-color: #22c55e; background: rgba(34,197,94,.11); }
.agent.done .st { color: #22c55e; }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(99,102,241,.55)} 70%{box-shadow:0 0 0 14px rgba(99,102,241,0)} 100%{box-shadow:0 0 0 0 rgba(99,102,241,0)} }
@keyframes slide { 0%{transform:translateX(-100%)} 100%{transform:translateX(100%)} }
.logbox {
font-family: ui-monospace, Menlo, Consolas, monospace; font-size: .78rem; line-height: 1.55;
background: rgba(0,0,0,.28); color: #cbd5e1; border-radius: 12px; padding: 10px 14px;
max-height: 160px; overflow: hidden; word-break: break-word;
}

.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 10px 0 20px; }
.metric {
border-radius: 16px; padding: 14px 16px; border: 1px solid rgba(128,128,128,.25);
background: rgba(128,128,128,.08); animation: rise .6s ease both;
}
.metric .v {
font-size: 1.7rem; font-weight: 800; line-height: 1.2;
background: linear-gradient(90deg, #0ea5e9, #a855f7); -webkit-background-clip: text; background-clip: text;
-webkit-text-fill-color: transparent; color: transparent;
}
.metric .l { font-size: .72rem; opacity: .7; text-transform: uppercase; letter-spacing: .07em; }
@keyframes rise { from{opacity:0; transform:translateY(12px)} to{opacity:1; transform:translateY(0)} }

.ringwrap { position: relative; width: 92px; height: 92px; }
.ring {
position: absolute; inset: 0; border-radius: 50%;
background: conic-gradient(var(--c) calc(var(--p) * 1%), rgba(128,128,128,.25) 0);
-webkit-mask: radial-gradient(farthest-side, transparent 68%, #000 70%);
mask: radial-gradient(farthest-side, transparent 68%, #000 70%);
}
.ringwrap b { position: absolute; inset: 0; display: grid; place-items: center; font-size: 1.2rem; }

.chip {
display: inline-block; padding: 4px 12px; margin: 0 6px 6px 0; border-radius: 999px; font-size: .8rem;
background: rgba(99,102,241,.15); border: 1px solid rgba(99,102,241,.4);
}
.src {
border-radius: 14px; padding: 14px 18px; margin-bottom: 12px; transition: all .25s ease;
border: 1px solid rgba(128,128,128,.25); background: rgba(128,128,128,.06);
}
.src:hover { transform: translateY(-2px); border-color: #6366f1; box-shadow: 0 8px 24px rgba(99,102,241,.18); }
.src .t { font-weight: 600; margin: 6px 0 4px; }
.src .t a { color: inherit; text-decoration: none; border-bottom: 1px dashed rgba(128,128,128,.6); }
.src .m { font-size: .78rem; opacity: .65; }
.src .snip { font-size: .8rem; opacity: .78; margin-top: 6px; }
.badge { display: inline-block; padding: 2px 10px; margin-right: 6px; border-radius: 999px; font-size: .68rem; font-weight: 700; letter-spacing: .03em; }
.badge.gold { background: rgba(245,158,11,.2); color: #f59e0b; border: 1px solid rgba(245,158,11,.5); }
.badge.green { background: rgba(34,197,94,.18); color: #22c55e; border: 1px solid rgba(34,197,94,.5); }
.badge.blue { background: rgba(14,165,233,.18); color: #38bdf8; border: 1px solid rgba(14,165,233,.5); }
.badge.red { background: rgba(239,68,68,.18); color: #f87171; border: 1px solid rgba(239,68,68,.5); }
.badge.gray { background: rgba(148,163,184,.18); color: #94a3b8; border: 1px solid rgba(148,163,184,.4); }
.badge.pdf { background: rgba(168,85,247,.2); color: #c084fc; border: 1px solid rgba(168,85,247,.5); }

.kb {
border-radius: 16px; padding: 16px; text-align: center; margin-bottom: 10px;
background: linear-gradient(135deg, rgba(14,165,233,.15), rgba(168,85,247,.15)); border: 1px solid rgba(99,102,241,.35);
}
.kb .v { font-size: 2rem; font-weight: 800; }
.kb .l { font-size: .75rem; opacity: .75; text-transform: uppercase; letter-spacing: .07em; }
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 10px; }
@media (max-width: 760px) { .steps { grid-template-columns: 1fr; } }
.step { border-radius: 16px; padding: 18px; border: 1px dashed rgba(128,128,128,.4); background: rgba(128,128,128,.05); }
.step .n { font-size: 1.6rem; }
.step .h { font-weight: 700; margin: 4px 0; }
.step .d { font-size: .85rem; opacity: .75; }
</style>
"""


def flat(s):
    """Remove line breaks and indentation so Streamlit does not treat HTML as code."""
    return "".join(line.strip() for line in s.splitlines())


def show(s, target=st):
    target.markdown(flat(s), unsafe_allow_html=True)


def esc(x):
    return _html.escape(str(x if x is not None else "")).replace("$", "&#36;")


show(CSS)

# ============================== HEADER ==============================
show("""
<div class="hero">
<h1>🩺 Clinical Research Assistant</h1>
<p>Four CrewAI agents search PubMed and your PDFs, then write an evidence-checked summary with citations.</p>
<span class="pill">🤖 CrewAI</span><span class="pill">⚡ Groq</span><span class="pill">📖 PubMed</span><span class="pill">🧠 Free embeddings</span><span class="pill">🔒 Citation check</span>
</div>
<div class="notice">⚠️ Research / education tool only. Not a medical device and not for clinical decision-making without expert review. Never upload patient data.</div>
""")

if not config.GROQ_API_KEY:
    st.error("GROQ_API_KEY is missing. Add it in Streamlit Cloud → App settings → Secrets.")
    st.stop()


@st.cache_resource(show_spinner="Building PDF knowledge base (first start only, 1-2 min)...")
def load_library():
    """Reads data/pdfs/*.pdf and creates embeddings once, then remembers them."""
    return build_library(config.PDF_FOLDER)


library = load_library()
st.session_state.setdefault("upload_cache", {})

# ============================== SIDEBAR ==============================
with st.sidebar:
    st.markdown("## 📚 Knowledge base")
    show(f'<div class="kb"><div class="v">{len(library["chunks"])}</div><div class="l">PDF chunks indexed</div></div>')
    uploads = st.file_uploader("Upload extra PDFs (optional)", type="pdf", accept_multiple_files=True)
    pubmed_only = st.toggle("PubMed only (ignore PDFs)", value=False)

    with st.expander("ℹ️ How it works"):
        st.markdown(
            "1. **Planner** turns your question into search queries\n"
            "2. **Retriever** searches PubMed + your PDFs (embeddings)\n"
            "3. **Critic** scores the evidence; weak? it loops back\n"
            "4. **Writer** drafts the summary, code checks every citation"
        )
        st.caption(f"Smart model: `{config.SMART_MODEL}`")
        st.caption(f"Fast model: `{config.FAST_MODEL}`")

    with st.expander("🛠 Diagnostics"):
        if st.button("🔧 Test Groq connection"):
            try:
                from crewai import LLM
                reply = LLM(model=config.FAST_MODEL, api_key=config.GROQ_API_KEY).call("Reply with the word OK")
                st.success(f"Groq works: {reply}")
            except Exception as e:
                st.error(f"Groq test failed: {e}")
        if st.button("📋 List my Groq models"):
            import requests
            r = requests.get("https://api.groq.com/openai/v1/models",
                             headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"}, timeout=20)
            if r.ok:
                st.write(sorted(m["id"] for m in r.json()["data"]))
            else:
                st.error(r.text)

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

# ============================== HELPERS ==============================
AGENTS = [
    ("planner", "🧭", "Planner", "Plans the search queries"),
    ("retriever", "🔎", "Retriever", "Searches PubMed + PDFs"),
    ("critic", "🧪", "Critic", "Grades the evidence"),
    ("writer", "✍️", "Writer", "Writes the cited summary"),
]
STATE_LABEL = {"wait": "Waiting", "run": "Working…", "done": "Done ✓"}


def tracker_html(states, rnd):
    cards = ""
    for key, icon, name, desc in AGENTS:
        s = states[key]
        extra = f" · round {rnd}" if key == "planner" and s != "wait" and rnd > 1 else ""
        cards += (f'<div class="agent {s}"><div class="ic">{icon}</div><div class="nm">{name}</div>'
                  f'<div class="ds">{desc}</div><div class="st">{STATE_LABEL[s]}{extra}</div></div>')
    return f'<div class="agents">{cards}</div>'


def log_html(lines):
    body = "<br>".join(esc(l.strip()) for l in lines[-6:])
    return f'<div class="logbox">{body}</div>'


def make_callback(tracker_ph, log_ph, ui):
    def cb(msg):
        ui["log"].append(msg)
        m = msg.strip()
        if "Planner agent" in m:
            r = re.search(r"round (\d+)", m)
            ui["round"] = int(r.group(1)) if r else 1
            ui["states"].update(planner="run", retriever="wait", critic="wait", writer="wait")
        elif "Retriever agent" in m:
            ui["states"].update(planner="done", retriever="run")
        elif "Critic agent" in m:
            ui["states"].update(retriever="done", critic="run")
        elif "Writer agent" in m:
            ui["states"].update(critic="done", writer="run")
        show(tracker_html(ui["states"], ui["round"]), tracker_ph)
        show(log_html(ui["log"]), log_ph)
    return cb


def evidence_badge(e):
    if e["source"] == "pdf":
        return "PDF", "pdf"
    t = " ".join(e.get("pub_types", [])).lower()
    if "meta-analysis" in t:
        return "Meta-analysis", "gold"
    if "systematic review" in t:
        return "Systematic review", "gold"
    if "randomized controlled trial" in t:
        return "RCT", "green"
    if "clinical trial" in t:
        return "Clinical trial", "green"
    if "review" in t:
        return "Review", "blue"
    if "case reports" in t:
        return "Case report", "red"
    return "Study", "gray"


def metric(value, label):
    return f'<div class="metric"><div class="v">{esc(value)}</div><div class="l">{esc(label)}</div></div>'


def ring_html(score):
    score = max(0.0, min(1.0, float(score)))
    pct = int(round(score * 100))
    color = "#22c55e" if score >= 0.7 else "#f59e0b" if score >= 0.5 else "#ef4444"
    return f'<div class="ringwrap"><div class="ring" style="--p:{pct};--c:{color}"></div><b>{pct}%</b></div>'


def render_result(r, q_text):
    evidence = r.get("evidence", [])
    pubmed_n = sum(1 for e in evidence if e["source"] == "pubmed")
    pdf_n = len(evidence) - pubmed_n
    cited_n = sum(1 for c in r.get("citations", []) if c["cited_in_summary"])
    bad = r.get("unverified_pmids", [])
    crit = r["critique"]

    show('<div class="metrics">'
         + metric(len(evidence), "Evidence items")
         + metric(pubmed_n, "PubMed papers")
         + metric(pdf_n, "PDF passages")
         + metric(f"{crit['score']:.2f}", "Critic score")
         + metric(r.get("loop_count", 1), "Research rounds")
         + metric(cited_n, "Sources cited")
         + metric(f"{r.get('elapsed', 0):.0f}s", "Time taken")
         + "</div>")

    tab1, tab2, tab3, tab4 = st.tabs(["📄 Summary", "🧪 Critic", "🧭 Plan", "📚 Sources"])

    with tab1:
        if bad:
            show(f'<span class="badge red">⚠ {len(bad)} citation ID(s) not found in evidence: {esc(", ".join(bad))}</span>')
        else:
            show('<span class="badge green">✓ All citations verified against retrieved evidence</span>')
        with st.container(border=True):
            st.markdown(r["final"])
        md = (f"# {q_text}\n\n{r['final']}\n\n---\n"
              "*Research/education tool only. Not a medical device. Not for clinical decision-making "
              "without expert review.*\n")
        st.download_button("⬇️ Download summary (.md)", data=md,
                           file_name="clinical_summary.md", mime="text/markdown")

    with tab2:
        c1, c2 = st.columns([1, 5])
        with c1:
            show(ring_html(crit["score"]))
        with c2:
            st.markdown("**Critic's assessment**")
            st.write(crit["notes"] or "No notes.")
            gaps = crit.get("gaps") or []
            if gaps:
                st.markdown("**Gaps found**")
                show("".join(f'<span class="chip">{esc(g)}</span>' for g in gaps))
            else:
                show('<span class="badge green">No gaps reported</span>')

    with tab3:
        st.markdown("**Research plan**")
        st.write(r.get("plan") or "No plan.")
        st.markdown("**Search queries used**")
        show("".join(f'<span class="chip">🔎 {esc(s)}</span>' for s in r.get("sub_queries", [])))

    with tab4:
        for e in r.get("citations", []):
            label, kind = evidence_badge(e)
            title = esc(e["title"])
            link = f'<a href="{esc(e["url"])}" target="_blank">{title}</a>' if e["url"] else title
            cited = ('<span class="badge green">✓ cited</span>' if e["cited_in_summary"]
                     else '<span class="badge gray">not cited</span>')
            snippet = esc((e.get("abstract") or "")[:230]) + "…"
            show(f'<div class="src"><span class="badge {kind}">{label}</span>{cited}'
                 f'<div class="t">{link}</div>'
                 f'<div class="m">{esc(e["journal"])} · {esc(e["year"])} · ID {esc(e["id"])}</div>'
                 f'<div class="snip">{snippet}</div></div>')


def welcome():
    show("""
<div class="steps">
<div class="step"><div class="n">1️⃣</div><div class="h">Ask a clinical question</div><div class="d">Type your own or click an example above.</div></div>
<div class="step"><div class="n">2️⃣</div><div class="h">Agents research</div><div class="d">Planner, Retriever and Critic search PubMed and your PDFs and loop until the evidence is strong.</div></div>
<div class="step"><div class="n">3️⃣</div><div class="h">Get a cited summary</div><div class="d">The Writer drafts it and the app checks that no citation is invented.</div></div>
</div>
""")


# ============================== INPUT ==============================
EXAMPLES = [
    ("💓 GLP-1 & heart failure",
     "What is the current evidence for GLP-1 receptor agonists in patients with heart failure?"),
    ("🫁 Prone positioning",
     "Does prone positioning reduce mortality in acute hypoxemic respiratory failure?"),
    ("🩸 SGLT2 & kidney disease",
     "Do SGLT2 inhibitors slow kidney disease progression in patients with type 2 diabetes?"),
]


def set_question(q):
    st.session_state["q"] = q


st.markdown("#### 💬 Try an example")
cols = st.columns(len(EXAMPLES))
for i, (col, (label, q)) in enumerate(zip(cols, EXAMPLES)):
    col.button(label, on_click=set_question, args=(q,), key=f"example_{i}")

question = st.text_area("Your clinical question", key="q", height=90,
                        placeholder="e.g. What is the evidence for SGLT2 inhibitors in heart failure?")
b1, b2 = st.columns([1, 3])
run_clicked = b1.button("🚀 Run research", type="primary")
b2.caption("⏱ Takes about 1–3 minutes · you can watch the agents work live")

# ============================== RUN ==============================
if run_clicked and question.strip():
    st.markdown("### ⚙️ Agents at work")
    tracker_ph = st.empty()
    log_ph = st.empty()
    ui = {"states": {k: "wait" for k, *_ in AGENTS}, "round": 1, "log": []}
    show(tracker_html(ui["states"], 1), tracker_ph)

    t0 = time.time()
    try:
        result = run_pipeline(question.strip(), on_step=make_callback(tracker_ph, log_ph, ui),
                              pdf_index=pdf_index)
    except Exception as e:
        import traceback
        st.error(f"Something went wrong: {e}")
        st.code(traceback.format_exc())
        st.stop()

    result["elapsed"] = time.time() - t0
    result.pop("pdf_index", None)          # keep memory small
    for k in ui["states"]:
        ui["states"][k] = "done"
    show(tracker_html(ui["states"], ui["round"]), tracker_ph)
    st.session_state["result"] = result
    st.session_state["result_q"] = question.strip()
    st.toast("Research complete ✅")
elif run_clicked:
    st.warning("Please type a clinical question first.")

# ============================== RESULTS ==============================
if "result" in st.session_state:
    st.markdown("### 📊 Results")
    render_result(st.session_state["result"], st.session_state.get("result_q", ""))
else:
    welcome()

show('<div style="text-align:center;opacity:.5;font-size:.78rem;margin-top:28px">'
     'Built with CrewAI · Groq · PubMed · Streamlit — research/education use only</div>')
