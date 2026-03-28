from __future__ import annotations

from collections.abc import Callable

from .config import AppConfig
from .model import Paper
from .translator import translate_en_to_target, translate_title_en_to_target

# HTML styling (works in VS Code, GitHub, Typora, many viewers).
# - Paper titles: strong <h3> so each entry has clear hierarchy.
# - Translations: left accent only, no light “card” fill (avoids a huge white slab in dark theme).
# - TOC / translation labels: softer than body translation block.
_PAPER_TITLE_STYLE = (
    "margin:1.65em 0 0.6em 0;padding-bottom:0.4em;"
    "border-bottom:2px solid rgba(92,155,213,0.45);"
    "font-size:1.22em;font-weight:700;line-height:1.35;"
)
_TRANSL_INLINE_STYLE = "color:#4a6fa8;font-weight:500;"
_TRANSL_BLOCK_WRAP_STYLE = (
    "margin:6px 0 14px 0;padding:2px 0 0 14px;border-left:3px solid rgba(92,155,213,0.72);"
    "background:transparent;"
)
_INNER_TRANSL_STYLE = "white-space:pre-wrap;color:inherit;opacity:0.97;"
_TRANSL_HEADING_STYLE = "color:inherit;opacity:0.78;font-weight:600;font-size:0.95em;"


def _md_escape(s: str) -> str:
    return (s or "").replace("\n", " ").strip()


def _html_escape(s: str, *, preserve_newlines: bool = False) -> str:
    """Escape text embedded in HTML; optionally keep newlines for pre-wrap blocks."""
    t = s or ""
    if not preserve_newlines:
        t = t.replace("\n", " ").strip()
    return (
        t.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _wrap_translation_inline(text: str) -> str:
    return f'<span style="{_TRANSL_INLINE_STYLE}">{_html_escape(text)}</span>'


def _wrap_translation_block(text: str) -> str:
    inner = _html_escape(text, preserve_newlines=True)
    return (
        f'<div style="{_TRANSL_BLOCK_WRAP_STYLE}">'
        f'<div style="{_INNER_TRANSL_STYLE}">{inner}</div></div>'
    )


def render_markdown(
    cfg: AppConfig,
    date_str: str,
    papers: list[Paper],
    *,
    import_link: str | None = None,
    zotero_top_collections: list[str] | None = None,
    default_collection_display: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> str:
    def _p(msg: str) -> None:
        if progress:
            progress(msg)

    lines: list[str] = []
    lines.append(f"## arXiv Daily Digest — {date_str}")
    lines.append("")
    lines.append(f"- **Count**: {len(papers)}")
    lines.append(f"- **Categories**: {', '.join(cfg.arxiv.categories) if cfg.arxiv.categories else 'all'}")
    lines.append(f"- **Window**: last `{cfg.arxiv.since_days}` day(s) (may auto-widen to satisfy min count)")
    lines.append("")

    if import_link:
        label = import_link.replace("\\", "/").split("/")[-1]
        lines.append(f"**导入脚本（终端执行；勾选状态以当前 md 为准）**: [{label}]({import_link})")
        lines.append("")
        lines.append(
            "*Markdown 预览中点击链接通常只会打开文件，不会执行；请在仓库根目录运行该 `.cmd`，或在资源管理器中双击。*"
        )
        lines.append("")

    # Directory / quick scan section
    translation_enabled = bool((cfg.translation.api_key or "").strip()) and (cfg.translation.provider or "").strip().lower() == "deepseek"
    n_papers = len(papers)

    if papers:
        lines.append("## 目录 / Quick scan")
        lines.append("")
        for i, p in enumerate(papers, start=1):
            t_en = _md_escape(p.title)
            # Checkbox so you can mark which ones to import later.
            if translation_enabled:
                if i == 1 or i == n_papers or i % 5 == 0:
                    _p(f"  Translation: titles {i}/{n_papers} …")
                t_target = _md_escape(translate_title_en_to_target(p.title, cfg.translation))
                t_target_html = _wrap_translation_inline(t_target)
                t_en_safe = _html_escape(t_en)
                # English stays plain; translated title is highlighted for quick scanning.
                lines.append(
                    f"- [ ] [{i}. `{p.arxiv_id}` {t_en_safe} / {t_target_html}](#p{i})"
                )
            else:
                lines.append(f"- [ ] [{i}. `{p.arxiv_id}` {t_en}](#p{i})")
        lines.append("")

    for i, p in enumerate(papers, start=1):
        lines.append(f'<a id="p{i}"></a>')
        title_safe = _html_escape(_md_escape(p.title))
        lines.append(f'<h3 style="{_PAPER_TITLE_STYLE}">{i}. {title_safe}</h3>')
        lines.append("")
        if p.authors:
            lines.append(f"- **Authors**: {', '.join(p.authors[:10])}{'…' if len(p.authors) > 10 else ''}")
        lines.append(f"- **arXiv**: `{p.arxiv_id}`")
        lines.append(f"- **Primary category**: `{p.primary_category}`")
        if p.highlights:
            lines.append(f"- **Matched terms**: {', '.join(p.highlights)}")
        lines.append(f"- **Updated**: `{p.updated}`")
        lines.append(f"- **Links**: [abs]({_md_escape(p.abs_url)}) | [pdf]({_md_escape(p.pdf_url)})")
        lines.append("")
        # Keep summaries short and readable
        summary = p.summary
        if len(summary) > 1200:
            summary = summary[:1200].rsplit(" ", 1)[0] + "…"
        lines.append("**Abstract (original)**")
        lines.append("")
        lines.append(summary)
        lines.append("")
        if translation_enabled:
            if i == 1 or i == n_papers or i % 5 == 0:
                _p(f"  Translation: abstracts {i}/{n_papers} …")
            abs_target = translate_en_to_target(summary, cfg.translation)
            if abs_target and abs_target != summary:
                lang = _html_escape(cfg.translation.target_lang)
                lines.append(
                    f'<p style="margin:0.85em 0 0.55em 0"><strong style="{_TRANSL_HEADING_STYLE}">'
                    f"摘要（翻译：{lang}）</strong></p>"
                )
                lines.append("")
                lines.append(_wrap_translation_block(abs_target))
                lines.append("")

    # Zotero collection helper section (place at the end of md).
    if zotero_top_collections is not None:
        lines.append("## Zotero 顶层 Collection（用于导入位置）")
        lines.append("")
        if zotero_top_collections:
            for name in zotero_top_collections:
                lines.append(f"- {name}")
        else:
            lines.append("- （未获取到或无权限；请检查 `zotero.user_id/api_key`）")
        lines.append("")
        if default_collection_display:
            lines.append(f"- **默认导入位置**：{default_collection_display}")
        lines.append("- 在勾选行末尾可追加：`{collection=\"Superconducting/Experiments\"}`（支持多级，按 `/` 分层创建）")
        lines.append("- 若追加 `{collection=\"\"}` 或不写 `{collection=...}`，则使用默认导入位置")
        lines.append("")

    lines.append("---")
    lines.append("Generated by `zotero_arxiv`.")
    lines.append("")
    return "\n".join(lines)


def build_index(papers: list[Paper]) -> list[dict]:
    idx: list[dict] = []
    for i, p in enumerate(papers, start=1):
        idx.append(
            {
                "id": i,
                "arxiv_id": p.arxiv_id,
                "title": p.title,
                "authors": p.authors,
                "summary": p.summary,
                "pdf_url": p.pdf_url,
                "abs_url": p.abs_url,
                "published": p.published,
                "updated": p.updated,
                "primary_category": p.primary_category,
                "categories": p.categories,
                "score": p.score,
                "highlights": p.highlights,
            }
        )
    return idx

