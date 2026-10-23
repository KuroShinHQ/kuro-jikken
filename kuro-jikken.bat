@echo off
:: Kuro-Jikken launcher (degistirme: go.ps1 tek-bootstrap)
title Kuro-Jikken Control Deck
cd /d %~dp0
where python >nul 2>nul || (echo [UYARI] python bulunamadi & pause & exit /b 1)
powershell -NoProfile -ExecutionPolicy Bypass -File "script\go.ps1"
pause
