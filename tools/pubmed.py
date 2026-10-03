import time
import requests
import xml.etree.ElementTree as ET
import config

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def search_pubmed(query, max_results=4):
    """Return a list of papers with id, title, abstract, journal, year, pub_types, url."""
    r = requests.get(
        f"{BASE}/esearch.fcgi",
        params={"db": "pubmed", "term": query, "retmax": max_results,
                "retmode": "json", "sort": "relevance", "email": config.PUBMED_EMAIL},
        timeout=20,
    )
    r.raise_for_status()
    ids = r.json()["esearchresult"]["idlist"]
    if not ids:
        return []

    time.sleep(0.4)  # NCBI allows about 3 requests per second without a key
    r = requests.get(
        f"{BASE}/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml",
                "email": config.PUBMED_EMAIL},
        timeout=30,
    )
    r.raise_for_status()
    root = ET.fromstring(r.content)

    papers = []
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//MedlineCitation/PMID")
        title_el = art.find(".//ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""
        abstract = " ".join(
            "".join(t.itertext()) for t in art.findall(".//Abstract/AbstractText")
        )
        papers.append({
            "id": pmid,
            "title": title,
            "abstract": abstract[:1200],
            "journal": art.findtext(".//Journal/Title") or "",
            "year": art.findtext(".//JournalIssue/PubDate/Year") or "n/a",
            "pub_types": [p.text for p in art.findall(".//PublicationType") if p.text],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "source": "pubmed",
        })
    return papers
