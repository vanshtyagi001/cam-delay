@echo off
echo Stopping CamDelay background process...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*cam-delay*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Done.
exit /b 0
