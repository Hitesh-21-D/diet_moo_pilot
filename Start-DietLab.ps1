$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Install requirements-web.txt in .venv first. See WEB_APP.md.' }
& $python -B scripts/native_database.py start
if ($LASTEXITCODE -ne 0) { throw 'Database startup failed.' }
$logs = Join-Path $PSScriptRoot '.local\logs'
New-Item -ItemType Directory -Force $logs | Out-Null
$services = @{
    api = '-B -m uvicorn backend.api:app --host 127.0.0.1 --port 8000'
    worker = '-B -m backend.worker'
}
foreach ($name in $services.Keys) {
    $arguments = $services[$name]
    $existing = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $python -and $_.CommandLine.Contains($arguments) }
    if (!$existing) {
        Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput "$logs\$name.out.log" -RedirectStandardError "$logs\$name.err.log" | Out-Null
    }
}
$ready = $false
for ($i=0; $i -lt 30; $i++) {
    try { $health = Invoke-RestMethod http://127.0.0.1:8000/api/health; $ready = $health.application -eq 'DietLab'; if ($ready) { break } } catch {}
    Start-Sleep -Seconds 1
}
if (!$ready) { throw 'API did not become ready. Check .local/logs/api.err.log.' }
Write-Host 'AmritAHARA is ready: http://127.0.0.1:8000'
Write-Host 'API, worker and PostgreSQL run in the background. Use Stop-DietLab.ps1 to stop them.'
