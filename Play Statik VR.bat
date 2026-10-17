@echo off
setlocal
title RevivePSVR1 - Statik
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\launch-psvr-test.ps1" -Menu -Title Statik -FovOf headset
if errorlevel 1 pause
