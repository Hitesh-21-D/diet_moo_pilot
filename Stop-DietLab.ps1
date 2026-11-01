$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
# Stop only this workspace's interpreter and our known application modules.
$owned = Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -eq $python -and ($_.CommandLine -match '-m (backend\.(worker|compute)|uvicorn backend\.api:app)(\s|$)')
}
foreach ($process in $owned) { & taskkill /PID $process.ProcessId /T /F 2>$null | Out-Null }
& $python -B scripts/native_database.py stop
Write-Host 'AmritAHARA stopped. Interrupted runs are marked failed when the worker restarts; saved results remain available.'
