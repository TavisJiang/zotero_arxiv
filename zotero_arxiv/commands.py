from __future__ import annotations

from pathlib import Path
import os
import re
import sys

from .arxiv_client import fetch_papers
from .config import load_config
from .render import build_index, render_markdown
from .utils import dump_json, ensure_dir, load_json, since_dt_iso, today_str
from .zotero_client import (
    create_item_from_arxiv,
    ensure_collection,
    ensure_collection_path,
    list_top_level_collections,
)


def _project_root() -> Path:
    # d:\projects\zotero_arxiv/zotero_arxiv/commands.py -> parents[1] is repo root
    return Path(__file__).resolve().parents[1]


def _report_paths(cfg, date_str: str, *, temp: bool, run_id: str | None) -> tuple[Path, Path, str]:
    """
    Returns:
      md_path, idx_path, report_slug
    """
    out_dir = Path(cfg.output.dir)
    ensure_dir(out_dir)
    sel_dir = Path(cfg.selection.dir)
    ensure_dir(sel_dir)

    if not temp:
        md_path = out_dir / f"arxiv_{date_str}.md"
        idx_name = cfg.selection.index_filename.format(date=date_str)
        idx_path = sel_dir / idx_name
        return md_path, idx_path, date_str

    # Temp mode: do not overwrite the regular daily report.
    # User requirement: no date in temp filenames; a single name is overwritten by default.
    run = (run_id or "").strip()
    if not run:
        md_path = out_dir / "arxiv_temp_manual.md"
        idx_path = sel_dir / "index_temp_manual.json"
        return md_path, idx_path, "manual"

    md_path = out_dir / f"arxiv_temp_manual_{run}.md"
    idx_path = sel_dir / f"index_temp_manual_{run}.json"
    return md_path, idx_path, run


def _paths(cfg, date_str: str) -> tuple[Path, Path]:
    md_path, idx_path, _ = _report_paths(cfg, date_str, temp=False, run_id=None)
    return md_path, idx_path


def _write_import_cmd(
    *,
    cmd_path: Path,
    python_exe: Path,
    config_path: Path,
    date_str: str,
    md_path: Path,
    idx_path: Path,
) -> None:
    # A .cmd wrapper is more likely to be executed when clicked from markdown viewers on Windows.
    cmd = (
        "@echo off\r\n"
        "setlocal\r\n"
        "pushd \""
        + str(_project_root())
        + "\"\r\n"
        f"\"{python_exe}\" -m zotero_arxiv zotero-add-from-md --config \"{config_path}\" --date \"{date_str}\" "
        f"--md-path \"{md_path}\" --index-path \"{idx_path}\"\r\n"
        "echo.\r\n"
        "echo Import command finished. Errorlevel=%errorlevel%\r\n"
        "pause\r\n"
        "endlocal\r\n"
    )
    cmd_path.write_text(cmd, encoding="utf-8")


def _progress(msg: str) -> None:
    """Print progress to stderr so stdout stays clean if piped."""
    print(msg, file=sys.stderr, flush=True)


def cmd_generate(args) -> int:
    cfg = load_config(args.config)
    date_str = args.date or today_str(cfg.output.timezone)
    _progress(f"zotero_arxiv: generating digest for {date_str}")

    if getattr(args, "max_papers", None) is not None:
        if args.max_papers < 10:
            raise ValueError("--max-papers must be >= 10")
        cfg = cfg.__class__(
            output=cfg.output.__class__(
                dir=cfg.output.dir,
                language=cfg.output.language,
                max_papers=int(args.max_papers),
                min_papers=cfg.output.min_papers,
                timezone=cfg.output.timezone,
            ),
            arxiv=cfg.arxiv,
            zotero=cfg.zotero,
            selection=cfg.selection,
            translation=cfg.translation,
        )

    since_days0 = cfg.arxiv.since_days if getattr(args, "since_days", None) is None else int(args.since_days)
    since_days = max(1, int(since_days0))

    # Best-effort widen window to satisfy min_papers.
    papers = []
    used_since_days = since_days
    for widen in (0, 1, 2, 4, 7, 14):
        used_since_days = max(since_days, widen) if widen else since_days
        since_dt = since_dt_iso(cfg.output.timezone, used_since_days)
        _progress(
            f"Fetching arXiv (papers updated within last {used_since_days} day(s), need ≥{cfg.output.min_papers}) …"
        )
        papers = fetch_papers(
            cfg.arxiv,
            cfg.output,
            since_dt=since_dt,
            max_results=800,
            progress=_progress,
        )
        if len(papers) >= cfg.output.min_papers:
            break
    _progress(f"→ {len(papers)} paper(s) kept after ranking (target up to {cfg.output.max_papers}).")

    md_path, idx_path, report_slug = _report_paths(
        cfg,
        date_str,
        temp=bool(getattr(args, "temp", False)),
        run_id=getattr(args, "run_id", None),
    )

    _progress("Creating import script …")

    import_link: str | None = None
    try:
        project_root = _project_root()
        python_exe = project_root / ".venv" / "Scripts" / "python.exe"
        config_path = Path(args.config).resolve()
        import_cmd_name = f"import_{md_path.stem}.cmd"
        cmd_dir = project_root / "import_cmds"
        ensure_dir(cmd_dir)
        import_cmd_path = cmd_dir / import_cmd_name
        # Make a relative markdown link from the md directory to the cmd.
        rel_href = os.path.relpath(str(import_cmd_path), str(md_path.parent)).replace("\\", "/")
        _write_import_cmd(
            cmd_path=import_cmd_path,
            python_exe=python_exe,
            config_path=config_path,
            date_str=date_str,
            md_path=md_path.resolve(),
            idx_path=idx_path.resolve(),
        )
        import_link = rel_href
    except Exception:
        # If import script generation fails, still generate the markdown/index.
        import_link = None

    # Best-effort: fetch Zotero top-level collection names for the end-of-md helper section.
    zotero_top_cols: list[str] | None = None
    default_display: str | None = None
    try:
        if (cfg.zotero.api_key or "").strip():
            _progress("Fetching Zotero collections (optional) …")
            zotero_top_cols = list_top_level_collections(cfg.zotero)
    except Exception:
        zotero_top_cols = None
    default_display = (cfg.zotero.collection_name or "").strip() or "Zotero 根部（未指定任何 collection）"

    translating = bool((cfg.translation.api_key or "").strip()) and (
        (cfg.translation.provider or "").strip().lower() == "deepseek"
    )
    if translating:
        _progress("(DeepSeek) Translating titles and abstracts — this step is usually the slowest …")
    else:
        _progress("Rendering markdown …")
    md = render_markdown(
        cfg,
        date_str,
        papers,
        import_link=import_link,
        zotero_top_collections=zotero_top_cols,
        default_collection_display=default_display,
        progress=_progress,
    )
    _progress("Saving files …")
    md_path.write_text(md, encoding="utf-8")

    idx = build_index(papers)
    dump_json(
        idx_path,
        {
            "date": date_str,
            "count": len(idx),
            "since_days_used": used_since_days,
            "report_slug": report_slug,
            "papers": idx,
        },
    )

    print(f"Wrote: {md_path}")
    print(f"Wrote: {idx_path}")
    return 0


def cmd_list(args) -> int:
    cfg = load_config(args.config)
    date_str = args.date
    _, idx_path = _paths(cfg, date_str)
    data = load_json(idx_path)
    papers = (data or {}).get("papers", [])
    for p in papers:
        print(f'{p["id"]:>3}  {p["arxiv_id"]}  {p["title"]}')
    return 0


def cmd_zotero_add(args) -> int:
    cfg = load_config(args.config)
    date_str = args.date
    ids = [int(x) for x in args.ids]
    return _zotero_add_common(cfg, date_str, ids)


def _zotero_add_common(cfg, date_str: str, ids: list[int]) -> int:
    if cfg.zotero.type.strip().lower() != "webapi":
        raise ValueError("config zotero.type must be webapi for zotero-add")

    _, idx_path = _paths(cfg, date_str)
    data = load_json(idx_path)
    papers = (data or {}).get("papers", [])
    by_id = {int(p["id"]): p for p in papers}

    missing = [i for i in ids if i not in by_id]
    if missing:
        raise ValueError(f"IDs not found in index: {missing}")

    col_key = ensure_collection(cfg.zotero)

    for i in ids:
        p = by_id[i]
        res = create_item_from_arxiv(
            cfg.zotero,
            title=p["title"],
            authors=p.get("authors", []),
            abstract=p.get("summary", ""),
            abs_url=p.get("abs_url", ""),
            pdf_url=p.get("pdf_url", ""),
            arxiv_id=p.get("arxiv_id", ""),
            tags=["arxiv-daily", date_str],
            collection_key=col_key,
        )
        ok = (res or {}).get("successful", {})
        if ok:
            item_key = next(iter(ok.values())).get("key")
            print(f"Imported {i}: {p['arxiv_id']} -> {item_key}")
        else:
            print(f"Failed {i}: {p['arxiv_id']} ({res})")

    return 0


def cmd_pick(args) -> int:
    """Interactive picker in terminal: show index and let user type IDs."""
    cfg = load_config(args.config)
    date_str = args.date
    _, idx_path = _paths(cfg, date_str)
    data = load_json(idx_path)
    papers = (data or {}).get("papers", [])
    if not papers:
        print("No papers found for that date.")
        return 0

    print(f"Papers for {date_str}:")
    for p in papers:
        print(f'{p["id"]:>3}  {p["arxiv_id"]}  {p["title"]}')

    try:
        raw = input("Select IDs to import (e.g. 1 3 5-7,10 or 'all' to import all, empty to cancel): ").strip()
    except EOFError:
        return 1

    if not raw:
        print("Cancelled.")
        return 0
    if raw.lower() == "all":
        ids = [int(p["id"]) for p in papers]
        return _zotero_add_common(cfg, date_str, ids)

    parts = raw.replace(",", " ").split()
    ids: list[int] = []
    for part in parts:
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                start = int(a)
                end = int(b)
            except ValueError:
                raise ValueError(f"Invalid range: {part!r}")
            if start > end:
                start, end = end, start
            ids.extend(range(start, end + 1))
        else:
            try:
                ids.append(int(part))
            except ValueError:
                raise ValueError(f"Invalid id: {part!r}")

    ids = sorted(set(ids))
    return _zotero_add_common(cfg, date_str, ids)


def cmd_zotero_add_from_md(args) -> int:
    """Parse markdown checklist and import all checked items."""
    cfg = load_config(args.config)
    date_str = args.date
    md_path: Path
    idx_path: Path

    if getattr(args, "md_path", None):
        md_path = Path(args.md_path).resolve()
    else:
        md_path, _ = _paths(cfg, date_str)

    if getattr(args, "index_path", None):
        idx_path = Path(args.index_path).resolve()
    else:
        _, idx_path = _paths(cfg, date_str)

    if not md_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
    if not idx_path.exists():
        raise FileNotFoundError(f"Index json file not found: {idx_path}")

    # Example line:
    # - [x] [1. `2504.11028v2` Title ...](#p1) {collection="Superconducting/Experiments"}
    # - [x] ... {collection=""}
    col_re = re.compile(r"\{\s*collection\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^}]*?))\s*\}")

    lines = md_path.read_text(encoding="utf-8").splitlines()
    items: dict[int, str | None] = {}

    for ln in lines:
        ln_stripped = ln.lstrip()
        if not ln_stripped.startswith("- [x]"):
            continue

        # Extract numeric id from: - [x] [<N>. ...](#pN)
        after = ln_stripped[len("- [x]") :].lstrip()
        if after.startswith("["):
            after = after[1:]
        num = ""
        for ch in after:
            if ch.isdigit():
                num += ch
            elif ch == ".":
                break
            elif num:
                break
        if not num:
            continue
        item_id = int(num)

        m = col_re.search(ln_stripped)
        if m:
            col = m.group(1) or m.group(2) or (m.group(3) or "").strip()
            col = col.strip()
            if not col:
                col = None
        else:
            col = None

        items[item_id] = col

    if not items:
        print("No checked items (- [x]) found in markdown.")
        return 0

    idx_data = load_json(idx_path)
    papers = (idx_data or {}).get("papers", [])
    by_id = {int(p["id"]): p for p in papers}

    missing = [i for i in items.keys() if i not in by_id]
    if missing:
        raise ValueError(f"IDs not found in index: {missing}")

    col_key_cache: dict[str | None, str | None] = {}

    def get_col_key(col_path: str | None) -> str | None:
        if col_path not in col_key_cache:
            col_key_cache[col_path] = ensure_collection_path(cfg.zotero, col_path)
        return col_key_cache[col_path]

    selected_ids = sorted(items.keys())
    print(f"Importing from markdown: {selected_ids}")

    for i in selected_ids:
        p = by_id[i]
        col_key = get_col_key(items.get(i))

        res = create_item_from_arxiv(
            cfg.zotero,
            title=p["title"],
            authors=p.get("authors", []),
            abstract=p.get("summary", ""),
            abs_url=p.get("abs_url", ""),
            pdf_url=p.get("pdf_url", ""),
            arxiv_id=p.get("arxiv_id", ""),
            tags=["arxiv-daily", date_str],
            collection_key=col_key,
        )

        ok = (res or {}).get("successful", {})
        if ok:
            item_key = next(iter(ok.values())).get("key")
            print(f"Imported {i}: {p['arxiv_id']} -> {item_key}")
        else:
            print(f"Failed {i}: {p['arxiv_id']} ({res})")

    return 0

