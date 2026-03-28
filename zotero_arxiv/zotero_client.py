from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyzotero import zotero

from .config import ZoteroConfig


@dataclass(frozen=True)
class ZoteroTarget:
    library_id: str
    library_type: str  # "user" or "group"


def _target(cfg: ZoteroConfig) -> ZoteroTarget:
    lt = (cfg.library_type or "user").strip().lower()
    if lt not in ("user", "group"):
        raise ValueError("zotero.library_type must be user|group")
    if lt == "user":
        if not cfg.user_id:
            raise ValueError("zotero.user_id is required for user library")
        return ZoteroTarget(library_id=cfg.user_id, library_type="user")
    if not cfg.group_id:
        raise ValueError("zotero.group_id is required for group library")
    return ZoteroTarget(library_id=cfg.group_id, library_type="group")


def _client(cfg: ZoteroConfig) -> zotero.Zotero:
    if not cfg.api_key:
        raise ValueError("zotero.api_key is required")
    t = _target(cfg)
    return zotero.Zotero(t.library_id, t.library_type, cfg.api_key)


def ensure_collection(zcfg: ZoteroConfig) -> str | None:
    name = (zcfg.collection_name or "").strip()
    if not name:
        return None
    z = _client(zcfg)
    cols = z.collections()
    for c in cols:
        if (c.get("data", {}) or {}).get("name") == name:
            return c.get("key")
    created = z.create_collections([{"name": name}])
    succ = (created or {}).get("successful", {})
    if not succ:
        raise RuntimeError("failed to create collection")
    return next(iter(succ.values())).get("key")


def ensure_collection_path(zcfg: ZoteroConfig, collection_path: str | None) -> str | None:
    """
    Ensure a (possibly multi-level) Zotero collection exists.

    - collection_path examples:
      - "ArXiv_daily"
      - "Superconducting/Experiments"
    - If collection_path is None/empty/whitespace -> uses zcfg.collection_name (default path).
    """
    path = (collection_path or "").strip()
    if not path:
        return ensure_collection(zcfg)

    # Backward compatible: no "/" means single collection name.
    if "/" not in path:
        # Use the provided name directly (do not rely on zcfg.collection_name).
        z = _client(zcfg)
        cols = z.collections()
        for c in cols:
            if (c.get("data", {}) or {}).get("name") == path:
                return c.get("key")
        created = z.create_collections([{"name": path}])
        succ = (created or {}).get("successful", {})
        if not succ:
            raise RuntimeError("failed to create collection")
        return next(iter(succ.values())).get("key")

    segments = [seg.strip() for seg in path.split("/") if seg.strip()]
    if not segments:
        return ensure_collection(zcfg)

    z = _client(zcfg)
    cols = z.collections()

    parent_key: str | None = None
    for seg in segments:
        # Find child collection with matching name under current parent.
        match_key: str | None = None
        for c in cols:
            data = c.get("data", {}) or {}
            if data.get("name") != seg:
                continue
            # Zotero API uses "parentCollection" key to represent hierarchy.
            if (data.get("parentCollection") or None) == (parent_key or None):
                match_key = c.get("key")
                break

        if match_key:
            parent_key = match_key
            continue

        payload: dict[str, str | None] = {"name": seg}
        if parent_key:
            payload["parentCollection"] = parent_key
        created = z.create_collections([payload])
        succ = (created or {}).get("successful", {})
        if not succ:
            raise RuntimeError(f"failed to create collection segment: {seg}")
        parent_key = next(iter(succ.values())).get("key")

        # Refresh cached collection list so deeper creation can find the new parent.
        cols = z.collections()

    return parent_key


def list_top_level_collections(zcfg: ZoteroConfig) -> list[str]:
    """
    Return Zotero top-level collection names under the library.

    "Top-level" here means: collection has no parentCollection (or missing parentCollection).
    """
    z = _client(zcfg)
    cols = z.collections()
    names: set[str] = set()
    for c in cols:
        data = c.get("data", {}) or {}
        name = data.get("name")
        if not name:
            continue
        parent = data.get("parentCollection", None)
        # Treat missing/None/empty as top-level.
        if parent is None or parent == "":
            names.add(str(name))
    return sorted(names, key=str.lower)


def create_item_from_arxiv(
    zcfg: ZoteroConfig,
    *,
    title: str,
    authors: list[str],
    abstract: str,
    abs_url: str,
    pdf_url: str,
    arxiv_id: str,
    tags: list[str] | None = None,
    collection_key: str | None = None,
) -> dict[str, Any]:
    z = _client(zcfg)
    template = z.item_template("journalArticle")

    creators: list[dict[str, str]] = []
    for a in authors:
        a = (a or "").strip()
        if not a:
            continue
        parts = a.split()
        if len(parts) == 1:
            creators.append({"creatorType": "author", "lastName": parts[0], "firstName": ""})
        else:
            creators.append({"creatorType": "author", "lastName": parts[-1], "firstName": " ".join(parts[:-1])})

    template["title"] = title
    template["abstractNote"] = abstract
    template["url"] = abs_url
    template["extra"] = f"arXiv: {arxiv_id}\nPDF: {pdf_url}"
    template["creators"] = creators

    if tags is None:
        tags = []
    all_tags = list(dict.fromkeys([t for t in (zcfg.default_tags + tags) if (t or "").strip()]))
    template["tags"] = [{"tag": t} for t in all_tags]

    if collection_key:
        template["collections"] = [collection_key]

    res = z.create_items([template])
    return res

