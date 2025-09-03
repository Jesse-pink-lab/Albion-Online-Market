# Albion Trade Optimizer

Albion Trade Optimizer helps analyze market data for Albion Online.

## Uploader

The application can launch the [Albion Data Project](https://www.albion-online-data.com/) uploader to contribute market prices. It uploads **market data only**.

* Windows: requires [Npcap](https://npcap.com) for packet capture.
* Linux: requires `libpcap` (e.g., `sudo apt-get install -y libpcap0.8`).
* Enable or disable the uploader in **Settings → Uploader**. Status messages appear in the status bar.
* Optional WebSocket broadcasts can be toggled in settings.

## Configuration

Configuration files are stored per-user using [`platformdirs`](https://pypi.org/project/platformdirs/):

* **Windows:** `%APPDATA%\AlbionTradeOptimizer\config.yaml`
* **macOS:** `~/Library/Application Support/AlbionTradeOptimizer/config.yaml`
* **Linux:** `~/.config/AlbionTradeOptimizer/config.yaml`

Writes are atomic to prevent corruption. When overriding uploader binaries, paths must be absolute and, on POSIX systems, executable.

## Packaging

`build.py` generates a PyInstaller bundle that includes the uploader binaries, license, and required data files.

## Windows Installer

**Prerequisites:** Python 3.11+, PyInstaller, and [Inno Setup](https://jrsoftware.org/isinfo.php) with `ISCC.exe` on your `PATH`.

**Build steps:**

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_installer.ps1
```

The installer is created under `dist\installer`. User data (logs, database, and `config.yaml`) persist across upgrades at:
`%APPDATA%\AlbionTradeOptimizer\{logs|data|config.yaml}`.
