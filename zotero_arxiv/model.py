from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    summary: str
    pdf_url: str
    abs_url: str
    published: str  # ISO
    updated: str  # ISO
    primary_category: str
    categories: list[str]
    score: float
    highlights: list[str]

