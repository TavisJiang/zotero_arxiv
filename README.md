Switch: [`README_zh.md`](./README_zh.md) (Chinese) | **This file (English)**

Use your interests and keywords from **`config.yaml`** to pull papers from arXiv, generate a **daily Markdown digest**, optionally translate titles/abstracts with **DeepSeek**, and import selected items into **Zotero**.

---

### Install and configure

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy config.example.yaml config.yaml
```

- **`pip install -e .`** installs this package in editable mode so `python -m zotero_arxiv` works from any working directory.
- Edit **`config.yaml`**: arXiv categories/keywords, Zotero Web API (`user_id`, `api_key`, default collection, etc.).

---

### Translation (optional)

Configure DeepSeek under **`translation:`** in `config.yaml`:

- If **`api_key`** is empty, translation is off (English title/abstract only).
- **`target_lang`** sets the target language (e.g. `"Chinese"`, `"German"`).

When translation is on, the digest uses light HTML styling for translated lines; each paper’s English title is a prominent `<h3>` with a separator line for scanning.

---

### Generate the digest

```powershell
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml
```

You can run this multiple times per day; it overwrites that date’s `daily/arxiv_YYYY-MM-DD.md` and matching `index_YYYY-MM-DD.json`.

Common options:

```powershell
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml --max-papers 20
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml --since-days 3
```

Temporary report (does not use the regular daily filenames):

```powershell
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml --temp
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml --temp --run-id try1
```

---

### Import into Zotero

1. **By ID** (IDs come from `list` or the index JSON):

```powershell
.\.venv\Scripts\python -m zotero_arxiv list --config config.yaml --date 2026-03-19
.\.venv\Scripts\python -m zotero_arxiv zotero-add --config config.yaml --date 2026-03-19 --ids 3 7 9
```

2. **Interactive picker**:

```powershell
.\.venv\Scripts\python -m zotero_arxiv pick --config config.yaml --date 2026-03-19
```

3. **Checklist in markdown**: change `- [ ]` to `- [x]` for items to import, save the file, then **run** the matching script under `import_cmds\` (e.g. from the repo root: `.\import_cmds\import_arxiv_YYYY-MM-DD.cmd`). A link at the top of the digest points to that `.cmd`; **in Markdown preview, clicking it usually only opens the file—it does not run the import.** Use the terminal, or double-click the `.cmd` in File Explorer if you prefer.

4. **Per-item collection** (multi-level, created if missing), append to the checked line, e.g.:

```markdown
- [x] [1. `2504.11028v2` ...](#p1) {collection="Superconducting/Experiments"}
```

Omit or use `{collection=""}` to use the default `zotero.collection_name` from `config.yaml`.

**Note:** `--config` may appear anywhere in the command line.

---

### Scheduled task (Windows)

| File | Role |
|------|------|
| `scripts/install_daily_task.ps1` | Installs a daily task (default name `zotero_arxiv_daily`, time is configurable) |
| `scripts/uninstall_daily_task.ps1` | Removes that task |
| `scripts/run_daily_generate.cmd` | Used by Task Scheduler: `cd` to repo root, then run `generate` |

Example (daily at 08:30):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_daily_task.ps1 -Time "08:30"
```

If nothing is written under `daily\`, ensure you ran **`pip install -e .`** and **re-run** the installer so the task points at the current `run_daily_generate.cmd`. You can also run `scripts\run_daily_generate.cmd` manually to verify.

Optional: inspect the task:

```powershell
schtasks /Query /TN "zotero_arxiv_daily" /V /FO LIST
```
