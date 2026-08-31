$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
  & $pythonCommand.Source ".\src\server.py"
  exit $LASTEXITCODE
}

$pyCommand = Get-Command py -ErrorAction SilentlyContinue
if ($pyCommand) {
  & $pyCommand.Source -3 ".\src\server.py"
  exit $LASTEXITCODE
}

Write-Host "未找到 Python 3。请安装 Python 3.10+ 后重新运行 .\run.ps1。" -ForegroundColor Red
exit 1
