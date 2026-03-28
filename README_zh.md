## zotero_arxiv（中文）

切换：[英文 `README.md`](./README.md) | 当前为中文说明

根据你在 `config.yaml` 中设定的兴趣与关键词，从 arXiv 抓取论文，生成 **每日 Markdown 日报**；可选用 **DeepSeek** 翻译标题与摘要；并可把选中的论文 **导入 Zotero**。

---

### 安装与配置

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
copy config.example.yaml config.yaml
```

- **`pip install -e .`**：把本包以可编辑方式装进当前虚拟环境，之后可在任意目录执行 `python -m zotero_arxiv`。
- 编辑 **`config.yaml`**：填写 arXiv 分类/关键词、Zotero Web API（`user_id`、`api_key`、默认 collection 等）。

---

### 翻译（可选）

在 `config.yaml` 的 **`translation:`** 中配置 DeepSeek：

- **`api_key` 为空**：不翻译，日报中仅英文标题与摘要。
- **`target_lang`**：目标语言，例如 `"Chinese"`、`"German"`。

启用翻译后，日报里会对译文做轻量 HTML 标注（目录中的译文标题、正文中的译文段落），英文论文标题使用加粗的 `<h3>` 与分隔线，便于扫读。

---

### 生成日报

```powershell
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml
```

同一天可多次运行，会覆盖该日期对应的 `daily/arxiv_YYYY-MM-DD.md` 与同目录下的 `index_YYYY-MM-DD.json`。

常用参数：

```powershell
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml --max-papers 20
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml --since-days 3
```

临时报告（不覆盖常规日报文件名）：

```powershell
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml --temp
.\.venv\Scripts\python -m zotero_arxiv generate --config config.yaml --temp --run-id try1
```

---

### 导入到 Zotero

1. **按编号导入**（编号来自当日的 index 或 `list` 输出）：

```powershell
.\.venv\Scripts\python -m zotero_arxiv list --config config.yaml --date 2026-03-19
.\.venv\Scripts\python -m zotero_arxiv zotero-add --config config.yaml --date 2026-03-19 --ids 3 7 9
```

2. **交互选择**：

```powershell
.\.venv\Scripts\python -m zotero_arxiv pick --config config.yaml --date 2026-03-19
```

3. **在日报里勾选再导入**：把目录里对应行从 `- [ ]` 改成 `- [x]`，保存后**在终端执行** `import_cmds` 下对应的 `.cmd`（例如在项目根目录：`.\import_cmds\import_arxiv_YYYY-MM-DD.cmd`）。日报顶部的链接在 Markdown 预览里**通常只能打开/跳转文件，不会执行导入**，实际导入须用命令行或资源管理器中双击该 `.cmd`。

4. **指定导入到某个 Collection**（支持多级，自动创建），在勾选行末尾追加，例如：

```markdown
- [x] [1. `2504.11028v2` ...](#p1) {collection="Superconducting/Experiments"}
```

不写或 `{collection=""}` 时使用 `config.yaml` 里的默认 `zotero.collection_name`。

---

### 定时任务（Windows）

| 文件 | 作用 |
|------|------|
| `scripts/install_daily_task.ps1` | 安装每日任务（默认任务名 `zotero_arxiv_daily`，默认时间可改） |
| `scripts/uninstall_daily_task.ps1` | 卸载该任务 |
| `scripts/run_daily_generate.cmd` | 供任务计划程序调用：先进入项目根目录再执行 `generate` |

安装示例（例如每天 08:30）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_daily_task.ps1 -Time "08:30"
```

若从未生成日报，请确认已执行 **`pip install -e .`**，并**重新运行**上面的安装脚本（任务应指向当前的 `run_daily_generate.cmd`）。也可手动运行 `scripts\run_daily_generate.cmd` 检查是否能正常写出 `daily\` 下的文件。

查看任务状态（可选）：

```powershell
schtasks /Query /TN "zotero_arxiv_daily" /V /FO LIST
```
