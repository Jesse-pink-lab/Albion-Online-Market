$ErrorActionPreference = 'Stop'

# Clean
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

# PyInstaller build
pyinstaller --noconfirm --clean `
  --name AlbionTradeOptimizer `
  --icon resources\icon.ico `
  main.py

# Optionally sync version from a module
$version = (python - <<'PY'
try:
    from app_version import __version__; print(__version__)
except Exception:
    print("0.9.0")
PY
).Trim()

# Update version in .iss
(Get-Content installer\AlbionTradeOptimizer.iss) `
  -replace '(?<=AppVersion ")[^"]+', $version `
  | Set-Content installer\AlbionTradeOptimizer.iss

# Compile installer (Inno Setup must be installed; ISCC.exe in PATH)
iscc installer\AlbionTradeOptimizer.iss

Write-Host "Installer built at dist\installer"
