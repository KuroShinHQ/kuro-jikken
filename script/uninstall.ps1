# Kuro-Jikken uninstall (moduler)
$Root = Split-Path -Parent $PSScriptRoot
Write-Host "Kuro-Jikken Uninstall"
Write-Host "1) pip rich kaldir | 2) logs temizle | 3) .lang/cfg sil"
$n = Read-Host "Numara (bosluk=hepsi)"
switch ($n) {
  "1" { python -m pip uninstall rich -y }
  "2" { if (Test-Path "$Root\logs") { Remove-Item "$Root\logs\*" -Force -Recurse } }
  "3" { if (Test-Path "$Root\.lang") { Remove-Item "$Root\.lang" -Force } }
  default { python -m pip uninstall rich -y 2>$env:NUL; Remove-Item "$Root\logs","$Root\.lang" -Force -Recurse -ErrorAction SilentlyContinue }
}
Write-Host "Uninstall bitti."
