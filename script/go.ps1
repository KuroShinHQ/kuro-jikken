# Kuro-Jikken go.ps1 — bootstrap (self-relocate + deps + menu)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# 1) python health
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Host "[UYARI] python bulunamadi (path). Kurulum gerekiyor."; exit 1 }

# 2) deps (minimal: rich)
python -c "import rich" 2>$env:NUL
if ($LASTEXITCODE -ne 0) { python -m pip install -r requirements.txt --quiet }

# 3) config-less menu start (Eleksiz boot standard: Ekran-1/2/3 menu.py icinde)
python "site\kuro_jikken_menu.py"
