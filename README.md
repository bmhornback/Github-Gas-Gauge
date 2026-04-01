# ⛽ GitHub Gas Gauge (GGG)

A CLI tool and GitHub Action to view your GitHub Copilot premium request consumption and estimate how many simple or complex tasks you have remaining in the current billing period. Also reports GitHub Actions minutes usage and external AI provider token consumption — all in one place.

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Built with Tauri](https://img.shields.io/badge/Built%20with-Tauri%20v2-blue?logo=tauri)](https://tauri.app)
[![Built with Rust](https://img.shields.io/badge/Backend-Rust-orange?logo=rust)](https://www.rust-lang.org)
[![React Frontend](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61dafb?logo=react)](https://reactjs.org)

- **Visual gas gauge** showing used vs. remaining premium requests
- **Task estimates** – see how many simple (chat) or complex (coding agent) tasks remain
- **Per-model breakdown** of usage
- **Actions billing** – see your GitHub Actions minutes used, included, and overage cost
- **Multi-provider token gauges** – track token/credit consumption for OpenAI, Anthropic, DeepSeek, Perplexity, and Google Gemini
- **Personal or organization** usage reporting
- **GitHub Action** for automated daily reporting
- **Desktop app** (Tauri + Rust + React) — system tray icon, live gauges, threshold alerts

---

```

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

### Show only Copilot section

```bash
python gas_gauge.py --copilot-only
```

### Show only Actions billing

```bash
python gas_gauge.py --actions-only
```

### Show external AI provider gauges

```bash
# Show specific providers alongside GitHub sections
export OPENAI_API_KEY=sk-...
export OPENAI_MONTHLY_LIMIT=50
python gas_gauge.py --providers openai

# Show all configured external providers
python gas_gauge.py --providers all

# Show only external providers (skip GitHub/Actions sections)
python gas_gauge.py --providers-only

# Show specific providers only
python gas_gauge.py --providers-only --providers openai,deepseek
```

### Options

```bash
cargo tauri dev
```
usage: gas_gauge.py [-h] [--token TOKEN] [--org ORG] [--year YEAR]
                    [--month MONTH] [--quota QUOTA]
                    [--plan {free,pro,individual,business,enterprise}]
                    [--no-color] [--json]
                    [--show-actions] [--actions-only] [--copilot-only]
                    [--providers PROVIDER[,...]] [--providers-only]

options:
  --token TOKEN               GitHub personal access token (default: $GITHUB_TOKEN)
  --org ORG                   Organization name (for org-level usage)
  --year YEAR                 Year to query (default: current year)
  --month MONTH               Month to query, 1-12 (default: current month)
  --quota QUOTA               Monthly premium request quota override
  --plan PLAN                 Copilot plan: free, pro, business, enterprise (default: pro)
  --no-color                  Disable color output
  --json                      Output raw JSON usage data (Copilot only)
  --show-actions              Include Actions billing section (default: True)
  --actions-only              Show only Actions billing, skip Copilot section
  --copilot-only              Show only Copilot section, skip Actions billing
  --providers PROVIDER[,...]  External providers to show, or 'all'
                              (openai, anthropic, deepseek, perplexity, gemini)
  --providers-only            Skip GitHub sections; show only external providers
                              (implies --providers all when --providers not set)
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
