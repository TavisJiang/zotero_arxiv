param(
  [string]$TaskName = "zotero_arxiv_daily"
)

$ErrorActionPreference = "Stop"

schtasks /Delete /F /TN $TaskName | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to remove scheduled task: $TaskName (exit code: $LASTEXITCODE)"
}
Write-Host "Removed scheduled task: $TaskName" -ForegroundColor Green

