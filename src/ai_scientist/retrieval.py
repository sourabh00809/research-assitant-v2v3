from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from typing import Iterable

from .embeddings import VectorSearchService, tokenize
from .models import ConnectorStatus, DeduplicationRecord, PaperSource, new_id, utc_now

logger = logging.getLogger(__name__)


SEED_CORPUS = [
    PaperSource(
        id="seed_react_001",
        title="Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        authors=["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus"],
        year=2020,
        abstract="Retrieval-augmented generation combines parametric generation with non-parametric document retrieval. The method improves factuality on knowledge-intensive tasks by conditioning generation on retrieved passages. Limitations include retriever quality, corpus coverage, and evaluation sensitivity.",
        url="https://arxiv.org/abs/2005.11401",
        source="seed",
        citation="Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.",
        arxiv_id="2005.11401",
    ),
    PaperSource(
        id="seed_agents_001",
        title="Communicative Agents for Software Development",
        authors=["Chen Qian", "Xin Cong", "Cheng Yang"],
        year=2023,
        abstract="Role-specialized communicative agents can decompose software development into planning, coding, reviewing, and testing. The study suggests multi-agent workflows improve task decomposition but depends on prompt design, verification, and human oversight.",
        url="https://arxiv.org/abs/2307.07924",
        source="seed",
        citation="Qian et al. (2023), Communicative Agents for Software Development.",
        arxiv_id="2307.07924",
    ),
    PaperSource(
        id="seed_science_001",
        title="The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery",
        authors=["Chris Lu", "Cong Lu", "Robert Tjarko Lange"],
        year=2024,
        abstract="An AI scientist system automates idea generation, experiment execution, paper writing, and review in machine learning research. The approach demonstrates autonomous scientific iteration, while reliability, novelty assessment, reproducibility, and evaluation quality remain central limitations.",
        url="https://arxiv.org/abs/2408.06292",
        source="seed",
        citation="Lu et al. (2024), The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery.",
        arxiv_id="2408.06292",
    ),
    PaperSource(
        id="seed_repro_001",
        title="A Survey on Reproducibility by Evaluating Deep Reinforcement Learning Algorithms",
        authors=["Peter Henderson", "Riashat Islam", "Philip Bachman"],
        year=2018,
        abstract="Evaluation of deep reinforcement learning is sensitive to random seeds, hyperparameters, reporting choices, and environment implementation. The paper recommends stronger baselines, confidence intervals, and transparent experimental reporting.",
        url="https://arxiv.org/abs/1709.06560",
        source="seed",
        citation="Henderson et al. (2018), Deep Reinforcement Learning That Matters.",
        arxiv_id="1709.06560",
    ),
    PaperSource(
        id="seed_survey_001",
        title="A Survey of Large Language Models",
        authors=["Wayne Xin Zhao", "Kun Zhou", "Junyi Li"],
        year=2023,
        abstract="Large language models show strong general capabilities across language, reasoning, and tool-use tasks. The survey organizes architectures, training, adaptation, evaluation, and applications while noting limitations in hallucination, evaluation, and alignment.",
        url="https://arxiv.org/abs/2303.18223",
        source="seed",
        citation="Zhao et al. (2023), A Survey of Large Language Models.",
        arxiv_id="2303.18223",
    ),
    PaperSource(
        id="seed_method_001",
        title="Model Cards for Model Reporting",
        authors=["Margaret Mitchell", "Simone Wu", "Andrew Zaldivar"],
        year=2019,
        abstract="Model cards document intended use, evaluation data, metrics, ethical considerations, and caveats for trained models. The method improves transparency but depends on complete reporting and incentives for adoption.",
        url="https://doi.org/10.1145/3287560.3287596",
        source="seed",
        citation="Mitchell et al. (2019), Model Cards for Model Reporting.",
        doi="10.1145/3287560.3287596",
    ),
]


class SearchService:
    def __init__(self, live_search: bool | None = None):
        self.live_search = live_search if live_search is not None else os.getenv("AI_SCIENTIST_LIVE_SEARCH") == "1"
        self.pubmed_enabled = os.getenv("AI_SCIENTIST_PUBMED_ENABLED", "false").lower() == "true"
        self.openalex_enabled = os.getenv("AI_SCIENTIST_OPENALEX_ENABLED", "true").lower() == "true"
        self.core_enabled = os.getenv("AI_SCIENTIST_CORE_ENABLED", "true").lower() == "true"
        self.crossref_enabled = os.getenv("AI_SCIENTIST_CROSSREF_ENABLED", "true").lower() == "true"
        self.last_connector_counts: dict[str, int] = {}

    def search(self, question: str, max_papers: int = 6, extra_sources: list[PaperSource] | None = None, sources: list[str] | None = None) -> list[PaperSource]:
        papers: list[PaperSource] = list(extra_sources or [])
        if self.live_search:
            arxiv = self._search_arxiv(question, max_papers=max_papers) if sources is None or "arxiv" in sources else []
            semantic = self._search_semantic_scholar(question, max_papers=max_papers) if sources is None or "semantic_scholar" in sources else []
            pubmed = self._search_pubmed(question, max_papers=max_papers) if self.pubmed_enabled and (sources is None or "pubmed" in sources) else []
            openalex = self._search_openalex(question, max_papers=max_papers) if self.openalex_enabled and (sources is None or "openalex" in sources) else []
            core = self._search_core(question, max_papers=max_papers) if self.core_enabled and (sources is None or "core" in sources) else []
            crossref = self._search_crossref(question, max_papers=max_papers) if self.crossref_enabled and (sources is None or "crossref" in sources) else []
            self.last_connector_counts = {
                "arxiv": len(arxiv),
                "semantic_scholar": len(semantic),
                "pubmed": len(pubmed),
                "openalex": len(openalex),
                "core": len(core),
                "crossref": len(crossref),
            }
            papers.extend(arxiv)
            papers.extend(semantic)
            papers.extend(pubmed)
            papers.extend(openalex)
            papers.extend(core)
            papers.extend(crossref)

        if not self.live_search:
            papers.extend(SEED_CORPUS)
        ranked = rank_papers(question, dedupe_papers(papers))
        return ranked[:max_papers]

    def connector_status(self) -> list[ConnectorStatus]:
        live_health = "ready" if self.live_search else "disabled"
        return [
            ConnectorStatus(
                source_type="arxiv",
                enabled=self.live_search,
                last_result_count=self.last_connector_counts.get("arxiv", 0),
                health=live_health,
            ),
            ConnectorStatus(
                source_type="semantic_scholar",
                enabled=self.live_search,
                last_result_count=self.last_connector_counts.get("semantic_scholar", 0),
                health=live_health,
            ),
            ConnectorStatus(
                source_type="pubmed",
                enabled=self.live_search and self.pubmed_enabled,
                last_result_count=self.last_connector_counts.get("pubmed", 0),
                health="ready" if self.live_search and self.pubmed_enabled else "disabled",
            ),
            ConnectorStatus(
                source_type="openalex",
                enabled=self.live_search and self.openalex_enabled,
                last_result_count=self.last_connector_counts.get("openalex", 0),
                health="ready" if self.live_search and self.openalex_enabled else "disabled",
            ),
            ConnectorStatus(
                source_type="core",
                enabled=self.live_search and self.core_enabled,
                last_result_count=self.last_connector_counts.get("core", 0),
                health="ready" if self.live_search and self.core_enabled else "disabled",
            ),
            ConnectorStatus(
                source_type="crossref",
                enabled=self.live_search and self.crossref_enabled,
                last_result_count=self.last_connector_counts.get("crossref", 0),
                health="ready" if self.live_search and self.crossref_enabled else "disabled",
            ),
        ]

    def _search_arxiv(self, question: str, max_papers: int) -> list[PaperSource]:
        query = urllib.parse.quote(f"all:{question}")
        category = infer_arxiv_category(question)
        category_filter = f"+AND+cat:{urllib.parse.quote(category)}" if category else ""
        url = f"https://export.arxiv.org/api/query?search_query={query}{category_filter}&start=0&max_results={max_papers}&sortBy=relevance&sortOrder=descending"
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                payload = response.read()
            root = ET.fromstring(payload)
        except Exception as exc:
            logger.warning("arXiv search failed: %s", exc)
            return []

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        papers: list[PaperSource] = []
        for entry in root.findall("atom:entry", ns):
            title = clean_text(entry.findtext("atom:title", default="", namespaces=ns))
            abstract = clean_text(entry.findtext("atom:summary", default="", namespaces=ns))
            paper_url = entry.findtext("atom:id", default="", namespaces=ns)
            arxiv_id = paper_url.rsplit("/", 1)[-1] if paper_url else None
            authors = [clean_text(author.findtext("atom:name", default="", namespaces=ns)) for author in entry.findall("atom:author", ns)]
            year = parse_year(entry.findtext("atom:published", default="", namespaces=ns))
            categories = [item.attrib.get("term", "") for item in entry.findall("atom:category", ns) if item.attrib.get("term")]
            papers.append(
                PaperSource(
                    id=f"arxiv_{arxiv_id or len(papers)}",
                    title=title,
                    authors=[author for author in authors if author],
                    year=year,
                    abstract=abstract,
                    url=paper_url,
                    source="arxiv",
                    source_type="arxiv",
                    sources=["arxiv"],
                    citation=format_citation(authors, year, title),
                    arxiv_id=arxiv_id,
                    submitted_at=entry.findtext("atom:published", default="", namespaces=ns) or None,
                    updated_at=entry.findtext("atom:updated", default="", namespaces=ns) or None,
                    categories=categories,
                )
            )
        return papers

    def _search_semantic_scholar(self, question: str, max_papers: int) -> list[PaperSource]:
        query = urllib.parse.quote(question)
        fields = "title,authors,year,abstract,url,externalIds,citationCount,influentialCitationCount,openAccessPdf"
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={max_papers}&fields={fields}"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ai-scientist-platform-mvp"})
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("Semantic Scholar search failed: %s", exc)
            return []

        papers: list[PaperSource] = []
        for item in payload.get("data", []):
            title = item.get("title") or "Untitled paper"
            abstract = item.get("abstract") or "No abstract available from Semantic Scholar."
            authors = [author.get("name", "") for author in item.get("authors", []) if author.get("name")]
            year = item.get("year")
            external = item.get("externalIds") or {}
            open_access = item.get("openAccessPdf") or {}
            paper_id = item.get("paperId") or external.get("DOI") or str(len(papers))
            papers.append(
                PaperSource(
                    id=f"s2_{paper_id}",
                    title=clean_text(title),
                    authors=authors,
                    year=year,
                    abstract=clean_text(abstract),
                    url=item.get("url") or "",
                    source="semantic_scholar",
                    source_type="semantic_scholar",
                    sources=["semantic_scholar"],
                    citation=format_citation(authors, year, title),
                    doi=external.get("DOI"),
                    arxiv_id=external.get("ArXiv"),
                    paper_id=item.get("paperId"),
                    citation_count=item.get("citationCount"),
                    influential_citation_count=item.get("influentialCitationCount"),
                    open_access_url=open_access.get("url"),
                )
            )
        return papers

    def _search_pubmed(self, question: str, max_papers: int) -> list[PaperSource]:
        key = os.getenv("NCBI_API_KEY")
        query = urllib.parse.quote(question)
        key_param = f"&api_key={urllib.parse.quote(key)}" if key else ""
        search_url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&retmode=json&retmax={max_papers}&term={query}{key_param}"
        )
        try:
            with urllib.request.urlopen(search_url, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            pmids = payload.get("esearchresult", {}).get("idlist", [])
            if not pmids:
                return []
            fetch_url = (
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                f"?db=pubmed&retmode=xml&id={','.join(pmids)}{key_param}"
            )
            with urllib.request.urlopen(fetch_url, timeout=8) as response:
                root = ET.fromstring(response.read())
        except Exception as exc:
            logger.warning("PubMed search failed: %s", exc)
            return []

        papers: list[PaperSource] = []
        for article in root.findall(".//PubmedArticle"):
            pmid = article.findtext(".//PMID", default="")
            title = clean_text(article.findtext(".//ArticleTitle", default="Untitled PubMed record"))
            abstract = clean_text(" ".join(node.text or "" for node in article.findall(".//AbstractText"))) or "No abstract available from PubMed."
            authors = []
            for author in article.findall(".//Author"):
                name = " ".join(filter(None, [author.findtext("ForeName"), author.findtext("LastName")]))
                if name.strip():
                    authors.append(clean_text(name))
            year = parse_year(article.findtext(".//PubDate/Year", default=""))
            doi = next((item.text for item in article.findall(".//ArticleId") if item.attrib.get("IdType") == "doi"), None)
            mesh_terms = [clean_text(node.findtext("DescriptorName", default="")) for node in article.findall(".//MeshHeading")]
            papers.append(
                PaperSource(
                    id=f"pubmed_{pmid or len(papers)}",
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=abstract,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    source="pubmed",
                    source_type="pubmed",
                    sources=["pubmed"],
                    citation=format_citation(authors, year, title),
                    doi=doi,
                    paper_id=pmid,
                    mesh_terms=[term for term in mesh_terms if term],
                    journal=clean_text(article.findtext(".//Journal/Title", default="")) or None,
                )
            )
        return papers


    def _search_openalex(self, question: str, max_papers: int) -> list[PaperSource]:
        query = urllib.parse.quote(question)
        url = f"https://api.openalex.org/works?search={query}&per-page={max_papers}&sort=relevance_score:desc"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ai-scientist-platform-mvp"})
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("OpenAlex search failed: %s", exc)
            return []

        papers: list[PaperSource] = []
        for item in payload.get("results", []):
            title = item.get("title") or "Untitled"
            abstract = item.get("abstract_inverted_index")
            abstract_text = reconstruct_abstract(abstract) if abstract else "No abstract available from OpenAlex."
            authors_list = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", []) if a.get("author")]
            year = item.get("publication_year")
            doi = item.get("doi", "").replace("https://doi.org/", "") if item.get("doi") else None
            open_access = item.get("open_access", {}) or {}
            concepts = [c.get("display_name", "") for c in item.get("concepts", []) if c.get("display_name")]
            papers.append(
                PaperSource(
                    id=f"openalex_{item.get('id', '').split('/')[-1] or len(papers)}",
                    title=clean_text(title),
                    authors=authors_list,
                    year=year,
                    abstract=clean_text(abstract_text),
                    url=item.get("id") or "",
                    source="openalex",
                    source_type="openalex",
                    sources=["openalex"],
                    citation=format_citation(authors_list, year, title),
                    doi=doi,
                    open_access_url=open_access.get("oa_url"),
                    concepts=concepts,
                    citation_count=item.get("cited_by_count"),
                    publisher=(item.get("primary_location") or {}).get("source", {}).get("display_name") if item.get("primary_location") else None,
                )
            )
        return papers

    def _search_core(self, question: str, max_papers: int) -> list[PaperSource]:
        api_key = os.getenv("CORE_API_KEY", "")
        if not api_key:
            logger.info("CORE search skipped: CORE_API_KEY not set")
            return []
        query = urllib.parse.quote(question)
        url = f"https://api.core.ac.uk/v3/search/works?q={query}&limit={max_papers}"
        try:
            request = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}", "User-Agent": "ai-scientist-platform-mvp"})
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("CORE search failed: %s", exc)
            return []

        papers: list[PaperSource] = []
        for item in payload.get("results", []):
            title = item.get("title") or "Untitled"
            abstract = item.get("abstract") or "No abstract available from CORE."
            authors_list = [author.get("name", "") for author in item.get("authors", []) if author.get("name")]
            year = item.get("yearOfPublication") or item.get("datePublished")
            if isinstance(year, str) and len(year) >= 4:
                year = int(year[:4])
            doi = item.get("doi")
            download_url = item.get("downloadUrl")
            papers.append(
                PaperSource(
                    id=f"core_{item.get('id', len(papers))}",
                    title=clean_text(title),
                    authors=authors_list,
                    year=year,
                    abstract=clean_text(abstract),
                    url=item.get("sourceUrl") or item.get("doi") or "",
                    source="core",
                    source_type="core",
                    sources=["core"],
                    citation=format_citation(authors_list, year, title),
                    doi=doi,
                    open_access_url=download_url or item.get("fullTextUrl"),
                    publisher=item.get("publisher"),
                )
            )
        return papers

    def _search_crossref(self, question: str, max_papers: int) -> list[PaperSource]:
        query = urllib.parse.quote(question)
        url = f"https://api.crossref.org/works?query={query}&rows={max_papers}&sort=relevance&order=desc"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ai-scientist-platform-mvp"})
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("CrossRef search failed: %s", exc)
            return []

        papers: list[PaperSource] = []
        for item in payload.get("message", {}).get("items", []):
            title = (item.get("title") or ["Untitled"])[0]
            abstract = item.get("abstract") or ""
            abstract_clean = clean_text(abstract.replace("<jats:p>", "").replace("</jats:p>", "")) if abstract else "No abstract available from CrossRef."
            authors_list = []
            for author in item.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                name = f"{given} {family}".strip()
                if name:
                    authors_list.append(name)
            year = (item.get("published-print") or item.get("published-online") or item.get("issued") or {}).get("date-parts", [[None]])[0][0]
            doi = item.get("DOI")
            container = item.get("container-title", [None])[0] if item.get("container-title") else None
            papers.append(
                PaperSource(
                    id=f"crossref_{doi or len(papers)}",
                    title=clean_text(title),
                    authors=authors_list,
                    year=year,
                    abstract=abstract_clean,
                    url=f"https://doi.org/{doi}" if doi else "",
                    source="crossref",
                    source_type="crossref",
                    sources=["crossref"],
                    citation=format_citation(authors_list, year, title),
                    doi=doi,
                    journal=container,
                    publisher=item.get("publisher"),
                )
            )
        return papers


def reconstruct_abstract(inverted_index: dict) -> str:
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def rank_papers(question: str, papers: Iterable[PaperSource]) -> list[PaperSource]:
    scorer = VectorSearchService()
    ranked = []
    for paper in papers:
        score = scorer.score(question, f"{paper.title} {paper.abstract}")
        paper.relevance_score = round(score.final_score, 3)
        paper.embedding_status = "embedded"
        haystack = tokenize(f"{paper.title} {paper.abstract}")
        overlap = tokenize(question) & haystack
        if any(term in haystack for term in ["method", "evaluation", "limitation", "baseline", "dataset", "metric"]):
            paper.relevance_score = min(1.0, round(paper.relevance_score + 0.05, 3))
        paper.relevance_reason = relevance_reason(overlap, paper, score.semantic_score, score.keyword_score)
        ranked.append(paper)
    return sorted(ranked, key=lambda item: item.relevance_score, reverse=True)


def dedupe_papers(papers: Iterable[PaperSource]) -> list[PaperSource]:
    seen: dict[str, PaperSource] = {}
    result: list[PaperSource] = []
    for paper in papers:
        key = dedupe_key(paper)
        if key in seen:
            merge_source(seen[key], paper)
            continue
        paper.sources = sorted(set(paper.sources or [paper.source_type]))
        seen[key] = paper
        result.append(paper)
    return result


def relevance_reason(overlap: set[str], paper: PaperSource, semantic_score: float, sparse_score: float) -> str:
    if overlap:
        terms = ", ".join(sorted(list(overlap))[:5])
        return f"Hybrid match via semantic={semantic_score:.2f}, keyword={sparse_score:.2f}; shared terms: {terms}."
    return f"Semantic match from {paper.source} (semantic={semantic_score:.2f}, keyword={sparse_score:.2f})."


def dedupe_key(paper: PaperSource) -> str:
    if paper.doi:
        return f"doi:{paper.doi.lower()}"
    if paper.arxiv_id:
        return f"arxiv:{paper.arxiv_id.lower()}"
    return f"title:{normalize_title(paper.title)}"


def merge_source(target: PaperSource, duplicate: PaperSource) -> DeduplicationRecord:
    target.sources = sorted(set((target.sources or [target.source_type]) + (duplicate.sources or [duplicate.source_type])))
    target.citation_count = max(filter(lambda value: value is not None, [target.citation_count, duplicate.citation_count]), default=None)
    target.influential_citation_count = max(
        filter(lambda value: value is not None, [target.influential_citation_count, duplicate.influential_citation_count]),
        default=None,
    )
    target.open_access_url = target.open_access_url or duplicate.open_access_url or (duplicate.url if duplicate.source_type == "arxiv" else None)
    target.abstract = target.abstract if len(target.abstract) >= len(duplicate.abstract) else duplicate.abstract
    target.categories = sorted(set(target.categories + duplicate.categories))
    target.mesh_terms = sorted(set(target.mesh_terms + duplicate.mesh_terms))
    return DeduplicationRecord(
        id=new_id("dedupe"),
        kept_source_id=target.id,
        duplicate_source_id=duplicate.id,
        match_type="doi" if target.doi and target.doi == duplicate.doi else "arxiv_id" if target.arxiv_id and target.arxiv_id == duplicate.arxiv_id else "title",
        score=1.0,
        created_at=utc_now(),
    )


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def infer_arxiv_category(question: str) -> str | None:
    lowered = question.lower()
    if any(term in lowered for term in ["biology", "biomedical", "clinical", "drug", "pubmed"]):
        return "q-bio"
    if any(term in lowered for term in ["language", "llm", "nlp", "retrieval", "rag"]):
        return "cs.CL"
    if any(term in lowered for term in ["learning", "agent", "model", "neural"]):
        return "cs.AI"
    return None


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def parse_year(value: str) -> int | None:
    match = re.match(r"(\d{4})", value or "")
    return int(match.group(1)) if match else None


def format_citation(authors: list[str], year: int | None, title: str) -> str:
    if not authors:
        lead = "Unknown authors"
    elif len(authors) == 1:
        lead = authors[0]
    else:
        lead = f"{authors[0]} et al."
    date = year or "n.d."
    return f"{lead} ({date}), {title}."
