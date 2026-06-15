# Run OK-Script test suite
# Usage: powershell -File run_tests.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== OK-Script Test Suite ===" -ForegroundColor Cyan
Write-Host ""

$venvPython = ".\venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    Write-Host "Using venv Python: $venvPython"
    $python = $venvPython
} else {
    Write-Host "Using system Python"
    $python = "python"
}

if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
    Write-Error "Python not found"
    exit 1
}

Write-Host "Running tests with pytest..." -ForegroundColor Yellow
& $python -m pytest tests/ -v --tb=short 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== All tests passed ===" -ForegroundColor Green
} else {
    Write-Host "`n=== Some tests failed ===" -ForegroundColor Red
}

exit $LASTEXITCODE
