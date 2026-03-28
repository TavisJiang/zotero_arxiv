from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import arxiv

from .config import ArxivConfig, OutputConfig
from .model import Paper
from .utils import contains_term, norm_ws


def _build_query(arxiv_cfg: ArxivConfig) -> str:
    parts: list[str] = []
    if arxiv_cfg.categories:
        cat = " OR ".join([f"cat:{c}" for c in arxiv_cfg.categories])
        parts.append(f"({cat})")
    if arxiv_cfg.extra_query.strip():
        parts.append(f"({arxiv_cfg.extra_query.strip()})")
    return " AND ".join(parts) if parts else "all:*"


def _score(
    title: str, summary: str, kw_any: list[str], kw_all: list[str]
) -> tuple[float, list[str]]:
    text = f"{title}\n{summary}"
    hits: list[str] = []
    score = 0.0

    for term in kw_any:
        if term and contains_term(text, term):
            hits.append(term)
            score += 2.0

    all_ok = True
    for term in kw_all:
        if term and not contains_term(text, term):
            all_ok = False
            break
        if term:
            hits.append(term)
    if kw_all and all_ok:
        score += 4.0

    # Prefer matches in title
    for term in kw_any + kw_all:
        if term and contains_term(title, term):
            score += 1.0

    return score, sorted(set(hits), key=str.lower)


def _excluded(title: str, summary: str, exclude_any: list[str]) -> bool:
    text = f"{title}\n{summary}"
    return any(term and contains_term(text, term) for term in exclude_any)


def fetch_papers(
    arxiv_cfg: ArxivConfig,
    out_cfg: OutputConfig,
    since_dt: datetime,
    max_results: int = 200,
    *,
    progress: Callable[[str], None] | None = None,
) -> list[Paper]:
    query = _build_query(arxiv_cfg)

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.LastUpdatedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    # export.arxiv.org sometimes fails transiently with TLS/EOF errors.
    # Increase retries/delay to make daily/temporary generation more robust.
    client = arxiv.Client(page_size=100, delay_seconds=5.0, num_retries=3)

    def _p(msg: str) -> None:
        if progress:
            progress(msg)

    papers: list[Paper] = []
    scanned = 0
    for r in client.results(search):
        scanned += 1
        if scanned == 1:
            _p("  Receiving results from arXiv API…")
        elif scanned % 80 == 0:
            _p(f"  … scanned {scanned} entries, kept {len(papers)} so far")
        title = norm_ws(r.title)
        summary = norm_ws(r.summary)

        updated = r.updated.replace(tzinfo=None) if r.updated else None
        published = r.published.replace(tzinfo=None) if r.published else None
        if updated and updated < since_dt.replace(tzinfo=None):
            # Since results are sorted by updated desc, we can stop once too old.
            break

        if _excluded(title, summary, arxiv_cfg.keywords.exclude_any):
            continue

        score, hits = _score(
            title=title,
            summary=summary,
            kw_any=arxiv_cfg.keywords.include_any,
            kw_all=arxiv_cfg.keywords.include_all,
        )

        # Keep even low-score papers to satisfy min_papers (ranking will still prefer high-score).

        authors = [a.name for a in r.authors] if r.authors else []
        cats = list(r.categories) if r.categories else []
        primary = r.primary_category or (cats[0] if cats else "")

        # Post-filter to keep the digest focused:
        # - Accept papers whose categories intersect configured categories
        # - Allow `cs.LG` papers only when they clearly mention quantum in title/abstract
        allowed = set(arxiv_cfg.categories or [])
        text_l = f"{title}\n{summary}".lower()
        has_quantum_signal = (
            ("quantum" in text_l) or ("qubit" in text_l) or ("qec" in text_l)
        )

        # If it's a cs.LG paper, only keep it when it clearly mentions quantum.
        if ("cs.LG" in cats or primary == "cs.LG") and not has_quantum_signal:
            continue

        cat_ok = bool(allowed.intersection(set(cats))) if allowed else True
        if not cat_ok:
            # Allow cross-listed non-config categories only when quantum signal is present.
            if not has_quantum_signal:
                continue

        abs_url = r.entry_id
        pdf_url = r.pdf_url

        papers.append(
            Paper(
                arxiv_id=r.get_short_id(),
                title=title,
                authors=authors,
                summary=summary,
                pdf_url=pdf_url,
                abs_url=abs_url,
                published=r.published.isoformat() if r.published else "",
                updated=r.updated.isoformat() if r.updated else "",
                primary_category=primary,
                categories=cats,
                score=score,
                highlights=hits,
            )
        )

    if scanned > 0:
        _p(f"  Done scanning arXiv ({scanned} entries → {len(papers)} kept before ranking).")

    papers.sort(key=lambda p: (p.score, p.updated), reverse=True)
    # Ensure at least min_papers when possible (limited by availability).
    take = max(int(out_cfg.min_papers), int(out_cfg.max_papers))
    return papers[:take][: out_cfg.max_papers]
