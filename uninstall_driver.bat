@echo off
:: Batch script to unregister Asus Camera DirectShow Virtual Camera Filter System-Wide
setlocal EnableDelayedExpansion

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    powershell -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\" %*\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo Unregistering Virtual Camera Filter...
regsvr32.exe /u /s "%~dp0driver\UnityCaptureFilter64.dll"
if exist "%~dp0driver\UnityCaptureFilter32.dll" (
    regsvr32.exe /u /s "%~dp0driver\UnityCaptureFilter32.dll"
)

echo Virtual Camera uninstalled successfully.
timeout /t 2 >nul
exit /b 0
