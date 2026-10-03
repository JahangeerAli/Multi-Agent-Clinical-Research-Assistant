import glob
import os
import re
import numpy as np
from pypdf import PdfReader
import config

_model = None


def _empty_index():
    return {"chunks": [], "vectors": np.zeros((0, 384), dtype="float32")}


def _get_model():
    """Load the free embedding model once (downloads ~130 MB the first time)."""
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=config.EMBED_MODEL)
    return _model


def embed_texts(texts):
    """Turn texts into normalized number-vectors (embeddings)."""
    vectors = np.array(list(_get_model().embed(texts)), dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return vectors / norms


def extract_chunks(file, filename, doc_no):
    """Read a PDF (path or uploaded file) and cut it into overlapping text chunks."""
    chunks = []
    try:
        reader = PdfReader(file)
    except Exception:
        return chunks
    n = 0
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""
        text = re.sub(r"\s+", " ", raw).strip()
        start = 0
        while start < len(text):
            piece = text[start:start + config.CHUNK_SIZE]
            if len(piece) > 80:
                n += 1
                chunks.append({"id": f"DOC{doc_no}-{n}", "filename": filename,
                               "page": page_no, "text": piece})
            start += config.CHUNK_SIZE - config.CHUNK_OVERLAP
    return chunks


def build_index(chunks):
    """Create embeddings for chunks. Returns {'chunks': [...], 'vectors': matrix}."""
    if not chunks:
        return _empty_index()
    vectors = []
    for i in range(0, len(chunks), 64):  # small batches keep memory low
        vectors.append(embed_texts([c["text"] for c in chunks[i:i + 64]]))
    return {"chunks": chunks, "vectors": np.vstack(vectors)}


def build_library(folder):
    """Read every PDF in a folder and build one index. Used when the app starts."""
    paths = sorted(glob.glob(os.path.join(folder, "*.pdf")))
    chunks = []
    for i, path in enumerate(paths, start=1):
        chunks += extract_chunks(path, os.path.basename(path), doc_no=i)
    return build_index(chunks)


def merge_indexes(indexes):
    """Combine several indexes into one."""
    indexes = [i for i in indexes if i and len(i["chunks"])]
    if not indexes:
        return _empty_index()
    return {"chunks": [c for i in indexes for c in i["chunks"]],
            "vectors": np.vstack([i["vectors"] for i in indexes])}


def search(query, index, k=2):
    """Find the k chunks closest in meaning to the query."""
    if not index or len(index["chunks"]) == 0:
        return []
    q = embed_texts([query])[0]
    scores = index["vectors"] @ q          # cosine similarity (vectors are normalized)
    best = np.argsort(scores)[::-1][:k]
    return [index["chunks"][i] for i in best if scores[i] >= config.MIN_PDF_SCORE]
