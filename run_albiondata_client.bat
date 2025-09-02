@echo off
set "CLIENT=%~dp0bin\albiondata-client.exe"
if not "%~1"=="" set "CLIENT=%~1"

echo CLIENT: "%CLIENT%"
for %%I in ("%CLIENT%") do set "SIZE=%%~zI"
echo SIZE: %SIZE%

powershell -NoLogo -NoProfile -Command "if(-not (Test-Path '%CLIENT%')){exit 1};$b=Get-Content -Encoding Byte -TotalCount 2 -Path '%CLIENT%';if([System.Text.Encoding]::ASCII.GetString($b) -ne 'MZ'){exit 1}"
if errorlevel 1 (
    echo albiondata-client.exe failed validation.
    exit /b 1
)

echo Launching "%CLIENT%" %*
"%CLIENT%" %*
