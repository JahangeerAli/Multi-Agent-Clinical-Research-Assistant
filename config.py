import os
import streamlit as st


def get_secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, default)


GROQ_API_KEY = get_secret("GROQ_API_KEY")
PUBMED_EMAIL = get_secret("PUBMED_EMAIL", "you@example.com")

# CrewAI settings (must be set before crewai is imported)
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# Groq models, the "groq/" prefix is required by CrewAI.
# If a model stops working, check https://console.groq.com/docs/models
SMART_MODEL = "groq/openai/gpt-oss-120b"   # Retriever and Writer
FAST_MODEL = "groq/openai/gpt-oss-20b"     # Planner and Critic

# Free local embeddings (no API key)
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
PDF_FOLDER = "data/pdfs"
CHUNK_SIZE = 1000        # characters per chunk
CHUNK_OVERLAP = 150
MIN_PDF_SCORE = 0.45     # ignore PDF chunks less similar than this

# Limits (kept small for the Groq free tier)
MAX_LOOPS = 2
RESULTS_PER_QUERY = 4
MAX_EVIDENCE = 10        # PubMed papers
MAX_PDF_EVIDENCE = 4     # PDF chunks
