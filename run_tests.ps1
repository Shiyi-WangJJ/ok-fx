# Run OK-Script test suite
# Usage: powershell -File run_tests.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== OK-Script Test Suite ===" -ForegroundColor Cyan
Write-Host ""

$venvPython = ".\venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at $venvPython"
    exit 1
}

Write-Host "Running tests with pytest..." -ForegroundColor Yellow
& $venvPython -m pytest tests/ -v --tb=short 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== All tests passed ===" -ForegroundColor Green
} else {
    Write-Host "`n=== Some tests failed ===" -ForegroundColor Red
}

exit $LASTEXITCODE
