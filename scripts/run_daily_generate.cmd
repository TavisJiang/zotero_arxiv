@echo off
setlocal EnableExtensions
REM Task Scheduler often starts with cwd=C:\Windows\System32, where
REM "python -m zotero_arxiv" fails (package is not installed in site-packages).
REM Always switch to project root first.
cd /d "%~dp0.." || exit /b 1

if not exist ".venv\Scripts\python.exe" (
  echo [zotero_arxiv] ERROR: missing .venv\Scripts\python.exe under project root: %CD% >&2
  exit /b 1
)

".venv\Scripts\python.exe" -m zotero_arxiv generate --config "config.yaml"
exit /b %ERRORLEVEL%
