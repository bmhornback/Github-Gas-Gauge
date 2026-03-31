# GitHub Gas Gauge 🔋

A CLI tool and GitHub Action to view your GitHub Copilot premium request consumption and estimate how many simple or complex tasks you have remaining in the current billing period. Also reports GitHub Actions minutes usage and external AI provider token consumption — all in one place.

## Features

- **Visual gas gauge** showing used vs. remaining premium requests
- **Task estimates** – see how many simple (chat) or complex (coding agent) tasks remain
- **Per-model breakdown** of usage
- **Actions billing** – see your GitHub Actions minutes used, included, and overage cost
- **Multi-provider token gauges** – track token/credit consumption for OpenAI, Anthropic, DeepSeek, Perplexity, and Google Gemini
- **Personal or organization** usage reporting
- **GitHub Action** for automated daily reporting
- **Desktop app** (Tauri + Rust + React) — system tray icon, live gauges, threshold alerts

## Example Output

```
============================================================
  🔋 GitHub Copilot Gas Gauge
============================================================
  User: octocat  |  Period: March 2026

  Usage   [████████████████░░░░░░░░░░░░░░░░░░░░░░░░]  40.0%

  Premium Requests Used:           120
  Premium Requests Remaining:      180
  Monthly Quota:                   300

  Remaining Task Estimates:
    Simple     (~1 req each):     180 tasks remaining
               Simple chat turn or inline suggestion with default model
    Complex    (~15 req each):     12 tasks remaining
               Copilot coding agent task or advanced model interaction

  Usage by Model:
    gpt-4o                               100 requests
    claude-3.5-sonnet                     20 requests

  Days remaining in billing period: 20
  Daily budget to stay on track:     9 requests/day
============================================================
============================================================
  ⚙️  GitHub Actions Usage
============================================================
  User: octocat

  Usage   [█████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  22.5%

  Minutes Used (this month):        450
  Included Minutes:               2,000
  Minutes Remaining:              1,550

  Paid Minutes Used (overage):        0
  Estimated Overage Cost:         $0.00
============================================================
============================================================
  🤖 OpenAI Usage
============================================================
  Spending  [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  24.9%
            $12.4500 of $50.00 monthly limit

  Usage by Model:
    GPT-4 Turbo                         $10.0000
    GPT-3.5 Turbo                        $2.4500

============================================================
============================================================
  🤖 DeepSeek Usage
============================================================
  Account Balance:  USD 45.0000

  Balance   [████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]  90.0% remaining
            USD 45.0000 of USD 50.00 remaining
============================================================
```

## Requirements

- Python 3.8+
- `requests` library
- GitHub personal access token with `read:org` scope (for org usage) or `copilot` scope (for user usage)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Personal usage

```bash
export GITHUB_TOKEN=ghp_yourtoken
python gas_gauge.py
```

### Organization usage (requires org admin access)

```bash
python gas_gauge.py --org my-org
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

### Environment variables

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (required for GitHub sections) |
| `COPILOT_PLAN` | Your Copilot plan: `free`, `pro`, `business`, `enterprise` (default: `pro`) |
| `COPILOT_QUOTA` | Monthly premium request quota override |
| `OPENAI_API_KEY` | OpenAI API key — enables OpenAI usage gauge |
| `OPENAI_MONTHLY_LIMIT` | Monthly spending limit in USD — enables OpenAI gauge bar |
| `DEEPSEEK_API_KEY` | DeepSeek API key — enables DeepSeek balance gauge |
| `DEEPSEEK_MONTHLY_LIMIT` | Credit limit in USD — enables DeepSeek gauge bar |
| `ANTHROPIC_API_KEY` | Anthropic API key (stored for future API support) |
| `PERPLEXITY_API_KEY` | Perplexity API key (stored for future API support) |
| `GEMINI_API_KEY` | Google Gemini API key (stored for future API support) |

## External AI Provider Support

| Provider | Usage API | What's Tracked |
|---|---|---|
| **OpenAI** | ✅ `/v1/dashboard/billing/usage` | Spend (USD) + per-model breakdown |
| **Anthropic** | ⚠️ No public API for individual keys | Key stored; view at console.anthropic.com |
| **DeepSeek** | ✅ `/user/balance` | Credit balance remaining |
| **Perplexity** | ⚠️ No public API available | Key stored for future support |
| **Google Gemini** | ⚠️ No public API available | Key stored for future support |

Set a `*_MONTHLY_LIMIT` env var (or configure in the desktop app Settings) to enable the gauge bar for cost/balance-based providers.

## Monthly Quotas by Plan

| Plan | Monthly Premium Requests |
|---|---|
| Free | 50 |
| Pro / Individual | 300 |
| Business | 300 per seat |
| Enterprise | 1,000 per seat |

## Task Cost Estimates

| Task Type | Approximate Cost | Description |
|---|---|---|
| Simple | ~1 request | Chat turn or inline suggestion with default model |
| Complex | ~15 requests | Copilot coding agent task or advanced model chat |

> **Note:** Actual costs vary by model. Some models (e.g., GPT-4.5) have higher multipliers.
> See [GitHub docs on Copilot requests](https://docs.github.com/en/copilot/concepts/billing/copilot-requests) for details.

## Model Multipliers

| Model | Multiplier |
|---|---|
| gpt-4o | 1x |
| gpt-4.1 | 1x |
| gpt-4.5 | 50x |
| gpt-5 | 1x |
| claude-3.5-sonnet | 1x |
| claude-3.7-sonnet | 1x |
| gemini-2.0-flash | 0.25x |
| gemini-2.5-pro | 1x |
| o1 | 10x |
| o3 | 10x |
| o3-mini | 1x |

## GitHub Actions

Run this tool automatically via the included workflow:

1. Go to **Actions** → **GitHub Gas Gauge** → **Run workflow**
2. Optionally specify an org name, plan type, quota override, or which section to show (`both`, `copilot-only`, `actions-only`)
3. Or add `COPILOT_TOKEN` to your repository secrets for a dedicated token

The workflow also runs daily at 9am UTC via schedule.

## Desktop App

The repository includes a cross-platform desktop app built with **Tauri + Rust** for the backend and **React + TypeScript** for the UI (`src-tauri/` + `src/`).

### Features
- System tray icon that changes color (green/yellow/red) based on usage level
- Live gas gauge UI with smooth animations for Copilot, Actions, and external providers
- Configurable polling interval and threshold alerts (75%, 90%, 100%)
- Provider API key management (OpenAI, Anthropic, DeepSeek, Perplexity, Gemini) with optional monthly limits
- Secure PAT and API key storage in local app data directory
- Dark mode UI

### Building
```bash
# Install dependencies
npm install

# Run in development mode
npm run tauri dev

# Build for production (requires Rust toolchain)
npm run tauri build
```

## Running Tests

```bash
python -m pytest test_gas_gauge.py -v
```

## Contributing

Contributions are welcome! Here are some guidelines:

1. **Fork** the repository and create a feature branch
2. **Write tests** for any new functionality (see `test_gas_gauge.py` for patterns)
3. **Run tests** before submitting: `python -m pytest test_gas_gauge.py -v`
4. **Keep it simple** – the Python CLI and desktop app are parallel tracks; changes to one shouldn't break the other
5. **Open a PR** with a clear description of what you changed and why

Please follow the existing code style (PEP 8 for Python, standard Rust/React conventions for the desktop app).

## Roadmap

- [x] Python CLI — Copilot premium request gas gauge
- [x] GitHub Actions workflow
- [x] Actions billing gauge
- [x] Multi-provider token gauges (OpenAI, Anthropic, DeepSeek, Perplexity, Gemini)
- [ ] Desktop app (Windows + macOS) — Tauri + Rust *(scaffold in place)*
- [ ] Anthropic / Perplexity / Gemini usage APIs (when publicly available)
- [ ] Prepaid balance tracking
- [ ] Email/SMS threshold alerts
- [ ] Historical usage charts

