@echo off
REM Launch albiondata-client.exe with proper quoting
set "CLIENT_EXE=%~dp0bin\albiondata-client.exe"

if not exist "%CLIENT_EXE%" (
    echo albiondata-client.exe not found at "%CLIENT_EXE%"
    exit /b 1
)

"%CLIENT_EXE%" %*
