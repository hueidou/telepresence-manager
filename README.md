# Telepresence Manager

A cross-platform desktop GUI tool for managing [Telepresence](https://www.telepresence.io/) connections. Built with Python + pywebview (WebView).

[中文文档](README.zh.md)

## Features

- 🔍 **Smart config scanning** — Auto-scan `~/.kube/` for K8s config files (config, *.txt, *.yaml, multi-document YAML)
- 📋 **Context cards** — Display all contexts as a card list (name, cluster, server, source file)
- ▶️ **One-click connect / disconnect** — Toggle Telepresence connection per context
- 📊 **On-demand status** — Connection state, node count, Traffic Manager status (parallel queries)
- 📦 **Traffic Manager management** — Install / upgrade with one click
- 💻 **Context-aware shell** — Open a terminal window pre-configured for the selected context
- 🔧 **Tool auto-detect** — Finds telepresence & kubectl on all platforms (PATH, Homebrew, Snap, WinGet)
- 🔎 **Search & filter** — Filter contexts by name, cluster, server, or source file (`Ctrl+F`)
- 🔄 **Auto-refresh** — Connection status auto-refreshes at configurable interval (default 30s)
- 🌍 **i18n: Chinese + English** — Auto-detects system language, switch anytime in ⚙ Settings
- ⚙ **Settings panel** — Language selector + refresh interval configuration
- 🆕 **Auto-update** — Checks GitHub Releases on startup, one-click update with auto-restart
- ⌨️ **Keyboard shortcuts** — `Ctrl+R` scan, `Ctrl+F` search, `Esc` close panels
- 📋 **Copy context name** — One-click copy to clipboard
- 🪵 **File logging** — Operation log at `~/.kube/telepresence-manager.log`

## Screenshot

![Screenshot](./assets/screenshot.png)

## Prerequisites

| Platform | Requirements |
|----------|-------------|
| **Windows** | Windows 10/11, Edge WebView2 Runtime (built-in) |
| **macOS** | macOS 12+, WebKit (built-in) |
| **Linux** | X11/Wayland, WebKit2GTK (`apt install libwebkit2gtk-4.1-dev`) |

**Required on all platforms:**
- [telepresence](https://www.telepresence.io/) v2.x
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

## Installation

### Download (Recommended)

Download the latest release from [GitHub Releases](https://github.com/hueidou/telepresence-manager/releases):

| Artifact | Platform | Description |
|----------|----------|-------------|
| `TelepresenceManager.exe` | Windows | Standalone executable |
| `*-win.zip` | Windows | Portable package |
| `*-Setup.exe` | Windows | Inno Setup installer |
| `TelepresenceManager` | macOS | Binary for macOS |
| `*-macos.tar.gz` | macOS | Portable package |
| `*.dmg` | macOS | Disk image with .app bundle |
| `TelepresenceManager` | Linux | Binary for Linux |
| `*-linux.tar.gz` | Linux | Portable package |
| `*.deb` | Linux (Debian/Ubuntu) | Debian package |

### From Source

```bash
git clone https://github.com/hueidou/telepresence-manager.git
cd telepresence-manager
pip install -r requirements.txt
python main.py
```

### Build Locally

```bash
pip install pyinstaller
python scripts/build.py
```

The executable will be generated in `dist/`.

## Project Structure

```
telepresence-manager/
├── main.py                      # Entry point, creates pywebview window
├── VERSION                      # Version string
├── requirements.txt             # Python dependencies
├── telepresence_manager.spec    # PyInstaller build spec
├── LICENSE                      # MIT License
├── README.md                    # English documentation
├── README.zh.md                 # Chinese documentation
├── app/                         # Python backend
│   ├── __init__.py
│   ├── api.py                   # pywebview JS API bridge
│   ├── config.py                # Configuration management (~/.kube/tp-config.json)
│   ├── kubeconfig.py            # Kubeconfig discovery & parsing
│   ├── logger.py                # File logging (~/.kube/tp-manager.log)
│   ├── telepresence.py          # Telepresence / kubectl CLI wrappers
│   └── updater.py               # Version check & auto-update
├── web/                         # Frontend UI
│   ├── index.html               # Page structure
│   ├── style.css                # Dark theme styles
│   ├── app.js                   # Frontend logic
│   └── i18n.js                  # Internationalization (zh/en)
├── scripts/
│   └── build.py                 # Cross-platform build script
├── installer/
│   ├── setup.iss                # Inno Setup installer script (Windows)
│   ├── build-linux.sh           # Linux packaging helper
│   └── build-macos.sh           # macOS packaging helper
└── .github/workflows/
    └── release.yml              # CI/CD: multi-platform build & release
```

## How It Works

```
WebView window (web/)
    ↕  pywebview JS API bridge
Python backend (app/api.py)
    ├─ config.py       Manages user settings (~/.kube/tp-config.json)
    ├─ kubeconfig.py   Scans ~/.kube/, parses YAML configs
    ├─ telepresence.py Wraps telepresence / kubectl subprocess calls
    └─ updater.py      Checks GitHub Releases for updates
```

- Backend calls `telepresence` and `kubectl` CLI via `subprocess`
- All long-running operations execute in background threads (ThreadPoolExecutor)
- Tool paths are auto-searched on each platform (Homebrew, Snap, WinGet, etc.)
- Supports multi-document YAML, .txt files, and other config formats
- Auto-update downloads new binary and restarts via platform-appropriate script
- Logging to `~/.kube/telepresence-manager.log` with rotation (5 MB, 3 backups)

## Configuration

Settings are stored at `~/.kube/telepresence-manager.json`:

```json
{
  "language": "auto",
  "refreshInterval": 30
}
```

- **language**: `"auto"` (detect from system), `"zh"`, or `"en"`
- **refreshInterval**: Status auto-refresh interval in seconds (15/30/60/120)

Edit the file manually or use the ⚙ Settings panel in the app.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` / `F5` | Scan kubeconfigs |
| `Ctrl+F` | Focus search box |
| `Esc` | Close panels / dialogs |

## License

[MIT](LICENSE)
