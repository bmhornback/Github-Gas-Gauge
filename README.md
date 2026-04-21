# ⛽ GitHub Gas Gauge (GGG)

A CLI tool and desktop application to view your GitHub Copilot premium request consumption and estimate how many simple or complex tasks you have remaining in the current billing period. Also reports GitHub Actions minutes usage and external AI provider token consumption — all in one place.

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
- **Session Analytics** — local token consumption tracking by model, project, and session (no upload)

---

GitHub Gas Gauge (GGG) is available as both a **Python CLI tool** and a **cross-platform desktop application** (Windows + macOS). The CLI provides quick terminal-based reporting, while the desktop app monitors your usage continuously from the system tray.

### Features

- ⛽ **Visual Gas Gauge** — color-coded bar (CLI) or SVG arc gauge (desktop) with green / yellow / red zones
- 🔔 **Desktop Notifications** — OS notifications at 75%, 90%, and 100% usage thresholds
- 🗂️ **System Tray Integration** — Lives quietly in your system tray; left-click to open
- 📊 **Usage Breakdown** — Requests or minutes used by model, product, and runner OS
- 📈 **Session Analytics** — Local Copilot session token insights by model, project, and session
- ⚠️ **Overage Panel** — Shows paid overage minutes and estimated cost
- ⚙️ **Settings** — PAT input, org/personal toggle, polling interval, notification thresholds
- 🔄 **Auto-polling** — Configurable polling interval (5 min / 15 min / 30 min / 1 hour)
- 🌙 **Dark Mode UI** — Clean, minimal dark theme

---

## Screenshots

> _Screenshots will be added once the app is built and running._

---

## Prerequisites

### CLI Tool

| Tool | Version | Install |
|---|---|---|
| **Python** | 3.8+ | [python.org](https://www.python.org) |

### Desktop Application

Before building, ensure you have the following installed:

| Tool | Version | Install |
|---|---|---|
| **Rust** | 1.70+ | [rustup.rs](https://rustup.rs) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org) |
| **Tauri CLI** | v2 | `cargo install tauri-cli --version "^2"` |

#### Platform-Specific Prerequisites

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

### 2a. CLI Tool Setup

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Set your GitHub token and run:

```bash
export GITHUB_TOKEN=ghp_...
python gas_gauge.py
```

### 2b. Desktop App Setup

Install frontend dependencies:

```bash
npm install
```

Run the app in development mode:

```bash
cargo tauri dev
```

Build a distributable installer:

```bash
cargo tauri build
```

Built installers will appear in `src-tauri/target/release/bundle/`.

---

## CLI Usage

### Basic usage

```bash
# Check your personal GitHub Copilot usage (reads GITHUB_TOKEN from environment)
python gas_gauge.py

# Check an organization's usage
python gas_gauge.py --org my-org

# Show only Copilot section
python gas_gauge.py --copilot-only

# Show only Actions billing
python gas_gauge.py --actions-only
```

### External AI provider gauges

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

### CLI Options

```
usage: gas_gauge.py [-h] [--token TOKEN] [--org ORG] [--year YEAR]
                    [--month MONTH] [--quota QUOTA]
                    [--plan {free,pro,individual,business,enterprise}]
                    [--no-color] [--json] [--actions-only] [--copilot-only]
                    [--providers PROVIDER[,...]] [--providers-only]

options:
  --token TOKEN               GitHub personal access token (default: $GITHUB_TOKEN)
  --org ORG                   Organization name (for org-level usage)
  --year YEAR                 Year to query (default: current year)
  --month MONTH               Month to query, 1-12 (default: current month)
  --quota QUOTA               Monthly premium request quota override
  --plan PLAN                 Copilot plan: free, pro, individual, business, enterprise (default: pro)
  --no-color                  Disable color output
  --json                      Output raw JSON usage data (Copilot only)
  --actions-only              Show only Actions billing, skip Copilot section
  --copilot-only              Show only Copilot section, skip Actions billing
  --providers PROVIDER[,...]  External providers to show, or 'all'
                              (openai, anthropic, deepseek, perplexity, gemini)
  --providers-only            Skip GitHub sections; show only external providers
                              (implies --providers all when --providers not set)
  --session-analytics         Show Copilot session analytics (local files, no upload)
  --session-period PERIOD     Period for session analytics: today, week (default),
                              month, all, or YYYY-MM-DD:YYYY-MM-DD
  --session-dir DIR           Override the Copilot session-state directory
                              (default: ~/.copilot/session-state)
  --session-json              Output session analytics as JSON and exit
```

---

## Optional Session Analytics

> **All session analytics data is read locally from your machine. Nothing is uploaded or shared with any external service.**

GitHub Gas Gauge can read Copilot's local session state files to report **output token consumption** by model, project, and session — giving you insight into which work consumed the most tokens even before API billing data is available.

### What it reads

Copilot writes session state files when you use GitHub Copilot in agent or chat mode:

```
~/.copilot/session-state/
└── <session-id>/
    ├── events.jsonl      ← JSONL stream of model changes and assistant messages
    └── workspace.yaml    ← Optional; contains the working directory
```

Each `events.jsonl` file contains events such as:
- `session.model_change` — which model is active
- `assistant.message` — output token count for each reply

### Limitations

- **Only output tokens are recorded.** Input tokens are not logged in Copilot session files. Reported token counts will be lower than actual API usage.
- Session files are only created when Copilot is used in **agent or chat mode** (not inline completions).

### CLI usage

```bash
# Add session analytics section to the normal output
python gas_gauge.py --session-analytics

# Filter to the current week (default)
python gas_gauge.py --session-analytics --session-period week

# Filter to today only
python gas_gauge.py --session-analytics --session-period today

# Full history (all sessions, no date filter)
python gas_gauge.py --session-analytics --session-period all

# Custom date range
python gas_gauge.py --session-analytics --session-period 2026-04-01:2026-04-30

# Export as JSON (no GitHub token required — standalone)
python gas_gauge.py --session-json

# Override the session state directory
python gas_gauge.py --session-analytics --session-dir /custom/path

# Combine with --providers-only (skip GitHub API calls)
python gas_gauge.py --providers-only --session-analytics
```

### Desktop app

The **Analytics** tab in the desktop application shows the same session data with:
- **Summary stats** — total output tokens, session count
- **Daily token usage chart** — SVG bar chart of the last 14 days
- **Breakdown by model** — horizontal bars showing each model's share
- **Breakdown by project** — derived from the `cwd` field in `workspace.yaml`
- **Top sessions leaderboard** — highest-token sessions ranked

### Caching

Parsed session results are cached in `~/.cache/github-gas-gauge/session-cache.json` keyed by file path and modification time. Files are re-parsed only when they change, keeping repeated runs fast.

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

## Environment Variables

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (required for GitHub sections) |
| `COPILOT_PLAN` | Copilot plan: `free`, `pro`, `business`, `enterprise` (default: `pro`) |
| `COPILOT_QUOTA` | Monthly premium request quota override |
| `OPENAI_API_KEY` | OpenAI API key (enables OpenAI usage gauge) |
| `OPENAI_MONTHLY_LIMIT` | Monthly spending limit in USD (enables OpenAI gauge bar) |
| `DEEPSEEK_API_KEY` | DeepSeek API key (enables DeepSeek balance gauge) |
| `DEEPSEEK_MONTHLY_LIMIT` | Credit limit in USD (enables DeepSeek gauge bar) |
| `ANTHROPIC_API_KEY` | Anthropic API key (set for future API support) |
| `ANTHROPIC_MONTHLY_LIMIT` | Monthly spending limit for Anthropic |
| `PERPLEXITY_API_KEY` | Perplexity API key (set for future API support) |
| `PERPLEXITY_MONTHLY_LIMIT` | Monthly spending limit for Perplexity |
| `GEMINI_API_KEY` | Google Gemini API key (set for future API support) |
| `GEMINI_MONTHLY_LIMIT` | Monthly spending limit for Gemini |

---

## Project Structure

```
├── gas_gauge.py             # Python CLI tool
├── test_gas_gauge.py        # CLI unit tests
├── requirements.txt         # Python dependencies
├── src-tauri/
│   ├── src/
│   │   ├── main.rs          # App entry point, system tray setup, Tauri commands
│   │   ├── billing.rs       # GitHub Billing REST API calls
│   │   ├── config.rs        # PAT storage and user settings
│   │   ├── alerts.rs        # Threshold logic and desktop notifications
│   │   ├── session.rs       # Local Copilot session analytics parser
│   │   └── lib.rs           # Tauri command exports
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── build.rs
├── src/
│   ├── components/
│   │   ├── GasGauge.tsx              # SVG-based circular/arc gauge component
│   │   ├── OveragePanel.tsx          # Shows overage spend if applicable
│   │   ├── BalancePanel.tsx          # Shows usage summary and breakdown
│   │   ├── ProviderGauges.tsx        # External AI provider gauge cards
│   │   ├── SessionAnalyticsPanel.tsx # Local Copilot session analytics
│   │   └── Settings.tsx              # PAT input, polling interval, threshold config
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
