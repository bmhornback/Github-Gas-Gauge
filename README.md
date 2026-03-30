# ⛽ GitHub Gas Gauge (GGG)

> **Know before you run out of gas.**

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Built with Tauri](https://img.shields.io/badge/Built%20with-Tauri%20v2-blue?logo=tauri)](https://tauri.app)
[![Built with Rust](https://img.shields.io/badge/Backend-Rust-orange?logo=rust)](https://www.rust-lang.org)
[![React Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61dafb?logo=react)](https://reactjs.org)

**A HornToad Labs Open Source Project**

---

## What is GitHub Gas Gauge?

GitHub Gas Gauge (GGG) is a cross-platform desktop application (Windows + macOS) that monitors your **GitHub Actions billing usage** and displays it as a visual "Gas Gauge" — so you always know how much of your included minutes remain before you incur overage charges.

### Features

- ⛽ **Visual Gas Gauge** — SVG arc-based semicircular gauge with color zones (🟢 green / 🟡 yellow / 🔴 red)
- 🔔 **Desktop Notifications** — OS notifications at 75%, 90%, and 100% usage thresholds
- 🗂️ **System Tray Integration** — Lives quietly in your system tray; left-click to open
- 📊 **Usage Breakdown** — Minutes used by Ubuntu, macOS, and Windows runners
- ⚠️ **Overage Panel** — Shows paid overage minutes and estimated cost
- ⚙️ **Settings** — PAT input, org/personal toggle, polling interval, notification thresholds
- 🔄 **Auto-polling** — Configurable polling interval (5 min / 15 min / 30 min / 1 hour)
- 🌙 **Dark Mode UI** — Clean, minimal dark theme

---

## Screenshots

> _Screenshots will be added once the app is built and running._

---

## Prerequisites

Before building, ensure you have the following installed:

| Tool | Version | Install |
|---|---|---|
| **Rust** | 1.70+ | [rustup.rs](https://rustup.rs) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org) |
| **Tauri CLI** | v2 | `cargo install tauri-cli --version "^2"` |

### Platform-Specific Prerequisites

**Windows:**
- Microsoft Visual Studio C++ Build Tools (or Visual Studio 2019/2022)
- WebView2 Runtime (included in Windows 11; download for Windows 10)

**macOS:**
- Xcode Command Line Tools: `xcode-select --install`

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/bmhornback/Github-Gas-Gauge.git
cd Github-Gas-Gauge
```

### 2. Install frontend dependencies

```bash
npm install
```

### 3. Run in development mode

```bash
cargo tauri dev
```

### 4. Build for production

```bash
# Windows
cargo tauri build

# macOS
cargo tauri build
```

Built installers will appear in `src-tauri/target/release/bundle/`.

---

## Getting a GitHub Personal Access Token (PAT)

GGG requires a GitHub PAT to call the billing API.

1. Go to [github.com/settings/tokens/new](https://github.com/settings/tokens/new)
2. Give it a descriptive name (e.g., `GitHub Gas Gauge`)
3. Select the required scopes:
   - **Personal account:** `user` → `read:user` (billing access is included)
   - **Organization:** `read:org`
4. Click **Generate token** and copy it
5. Paste it into the GGG Settings panel

> ⚠️ Your token is stored locally on your machine in the app data directory. It is never transmitted anywhere except to the GitHub API.

---

## Project Structure

```
├── src-tauri/
│   ├── src/
│   │   ├── main.rs          # App entry point, system tray setup
│   │   ├── billing.rs       # GitHub Billing REST API calls
│   │   ├── config.rs        # PAT storage and user settings
│   │   ├── alerts.rs        # Threshold logic and desktop notifications
│   │   └── lib.rs           # Tauri command exports
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── build.rs
├── src/
│   ├── components/
│   │   ├── GasGauge.tsx     # SVG-based circular/arc gauge component
│   │   ├── OveragePanel.tsx # Shows overage spend if applicable
│   │   ├── BalancePanel.tsx # Shows usage summary and breakdown
│   │   └── Settings.tsx     # PAT input, polling interval, threshold config
│   ├── App.tsx
│   ├── main.tsx
│   └── styles/
│       └── app.css
├── package.json
├── vite.config.ts
├── tsconfig.json
└── index.html
```

---

## Contributing

Contributions are welcome! This is an open source project under the MIT license.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "feat: add my feature"`
4. Push to your branch: `git push origin feature/my-feature`
5. Open a Pull Request

Please follow the existing code style and include meaningful commit messages.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## About HornToad Labs

GitHub Gas Gauge is a sub-branded project under **HornToad Labs**, a collection of open source tools and utilities.
