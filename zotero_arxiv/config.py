from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class OutputConfig:
    dir: str
    # Reserved for future use (e.g. report locale); not read by the current pipeline.
    language: str
    max_papers: int
    min_papers: int
    timezone: str


@dataclass(frozen=True)
class KeywordConfig:
    include_any: list[str]
    include_all: list[str]
    exclude_any: list[str]


@dataclass(frozen=True)
class ArxivConfig:
    since_days: int
    categories: list[str]
    keywords: KeywordConfig
    extra_query: str


@dataclass(frozen=True)
class ZoteroConfig:
    type: str
    user_id: str
    api_key: str
    library_type: str
    group_id: str
    collection_name: str
    default_tags: list[str]


@dataclass(frozen=True)
class SelectionConfig:
    dir: str
    index_filename: str


@dataclass(frozen=True)
class TranslationConfig:
    # Translation provider name: currently only "deepseek" is supported.
    provider: str
    # If api_key is empty, translation is disabled and no translation blocks are rendered.
    api_key: str
    base_url: str
    model: str
    # Source/target languages for the LLM prompt (best-effort strings).
    source_lang: str
    target_lang: str


@dataclass(frozen=True)
class AppConfig:
    output: OutputConfig
    arxiv: ArxivConfig
    zotero: ZoteroConfig
    selection: SelectionConfig
    translation: TranslationConfig


def _get(d: dict[str, Any], key: str, default: Any = None) -> Any:
    return d[key] if key in d else default


def load_config(path: str | Path) -> AppConfig:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping")

    out = data.get("output", {}) or {}
    arx = data.get("arxiv", {}) or {}
    zot = data.get("zotero", {}) or {}
    sel = data.get("selection", {}) or {}
    tr = data.get("translation", {}) or {}

    kw = (arx.get("keywords", {}) or {}) if isinstance(arx, dict) else {}
    kwc = KeywordConfig(
        include_any=list(_get(kw, "include_any", []) or []),
        include_all=list(_get(kw, "include_all", []) or []),
        exclude_any=list(_get(kw, "exclude_any", []) or []),
    )

    cfg = AppConfig(
        output=OutputConfig(
            dir=str(_get(out, "dir", "daily")),
            language=str(_get(out, "language", "both")),
            max_papers=int(_get(out, "max_papers", 15)),
            min_papers=int(_get(out, "min_papers", 10)),
            timezone=str(_get(out, "timezone", "Asia/Shanghai")),
        ),
        arxiv=ArxivConfig(
            since_days=int(_get(arx, "since_days", 1)),
            categories=list(_get(arx, "categories", []) or []),
            keywords=kwc,
            extra_query=str(_get(arx, "extra_query", "") or ""),
        ),
        zotero=ZoteroConfig(
            type=str(_get(zot, "type", "webapi")),
            user_id=str(_get(zot, "user_id", "") or ""),
            api_key=str(_get(zot, "api_key", "") or ""),
            library_type=str(_get(zot, "library_type", "user")),
            group_id=str(_get(zot, "group_id", "") or ""),
            collection_name=str(_get(zot, "collection_name", "") or ""),
            default_tags=list(_get(zot, "default_tags", []) or []),
        ),
        selection=SelectionConfig(
            dir=str(_get(sel, "dir", _get(out, "dir", "daily"))),
            index_filename=str(_get(sel, "index_filename", "index_{date}.json")),
        ),
        translation=TranslationConfig(
            provider=str(_get(tr, "provider", "deepseek") or "deepseek"),
            api_key=str(_get(tr, "api_key", "") or ""),
            base_url=str(_get(tr, "base_url", "https://api.deepseek.com/v1") or "https://api.deepseek.com/v1"),
            model=str(_get(tr, "model", "deepseek-chat") or "deepseek-chat"),
            source_lang=str(_get(tr, "source_lang", "English") or "English"),
            target_lang=str(_get(tr, "target_lang", "Chinese") or "Chinese"),
        ),
    )
    return cfg

