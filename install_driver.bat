@echo off
:: Batch script to register Asus Camera DirectShow Virtual Camera Filter System-Wide (HKLM)
:: Requests Administrator privileges via UAC if not already elevated

setlocal EnableDelayedExpansion

net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo Requesting administrative privileges to register virtual camera driver...
    powershell -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\" %*\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
set "CAMNAME=Asus Camera"
if not "%~1"=="" set "CAMNAME=%~1"

echo Registering 64-bit Virtual Camera: "%CAMNAME%" ...
regsvr32.exe /s "%~dp0driver\UnityCaptureFilter64.dll" "/i:UnityCaptureName=%CAMNAME%"

if exist "%~dp0driver\UnityCaptureFilter32.dll" (
    echo Registering 32-bit Virtual Camera: "%CAMNAME%" ...
    regsvr32.exe /s "%~dp0driver\UnityCaptureFilter32.dll" "/i:UnityCaptureName=%CAMNAME%"
)

echo.
echo ======================================================
echo Successfully registered "%CAMNAME%" as a Windows Virtual Camera!
echo ======================================================
echo.
timeout /t 3 >nul
exit /b 0
