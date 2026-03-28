param(
  [string]$Time = "08:30",
  [string]$TaskName = "zotero_arxiv_daily"
)

$ErrorActionPreference = "Stop"

$proj = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $proj ".venv\\Scripts\\python.exe"
$runner = Join-Path $proj "scripts\\run_daily_generate.cmd"

if (-not (Test-Path $python)) {
  throw "Missing venv python: $python. Please run setup first."
}
if (-not (Test-Path $runner)) {
  throw "Missing runner script: $runner"
}

# Run the .cmd wrapper (not python.exe directly). Scheduled tasks default to
# cwd like System32; without cd to project root, "python -m zotero_arxiv" fails.
$action = "`"$runner`""

# Use Register-ScheduledTask with S4U logon so the task runs whether or not the
# user is interactively logged on (no password stored, works on Win10/11).
$h, $m = $Time -split ":"
$trigger = New-ScheduledTaskTrigger -Daily -At "$($h):$($m)"
$actionObj = New-ScheduledTaskAction -Execute $runner
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $actionObj -Trigger $trigger `
  -Settings $settings -Principal $principal -Force | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Failed to install scheduled task: $TaskName"
}

Write-Host "Installed scheduled task: $TaskName at $Time" -ForegroundColor Green
Write-Host "Runner: $runner" -ForegroundColor DarkGray
Write-Host "Tip: translation and API keys are read from config.yaml (not env vars)." -ForegroundColor Yellow

