# GitHub Gas Gauge 🔋

A CLI tool and GitHub Action to view your GitHub Copilot premium request consumption and estimate how many simple or complex tasks you have remaining in the current billing period. Also reports GitHub Actions minutes usage alongside Copilot.

## Features

- **Visual gas gauge** showing used vs. remaining premium requests
- **Task estimates** – see how many simple (chat) or complex (coding agent) tasks remain
- **Per-model breakdown** of usage
- **Actions billing** – see your GitHub Actions minutes used, included, and overage cost
- **Personal or organization** usage reporting
- **GitHub Action** for automated daily reporting

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

### Options

```
usage: gas_gauge.py [-h] [--token TOKEN] [--org ORG] [--year YEAR]
                    [--month MONTH] [--quota QUOTA]
                    [--plan {free,pro,individual,business,enterprise}]
                    [--no-color] [--json]
                    [--show-actions] [--actions-only] [--copilot-only]

options:
  --token TOKEN       GitHub personal access token (default: $GITHUB_TOKEN)
  --org ORG           Organization name (for org-level usage)
  --year YEAR         Year to query (default: current year)
  --month MONTH       Month to query, 1-12 (default: current month)
  --quota QUOTA       Monthly premium request quota override
  --plan PLAN         Copilot plan: free, pro, business, enterprise (default: pro)
  --no-color          Disable color output
  --json              Output raw JSON usage data (Copilot only)
  --show-actions      Include Actions billing section (default: True)
  --actions-only      Show only Actions billing, skip Copilot section
  --copilot-only      Show only Copilot section, skip Actions billing
```

### Environment variables

| Variable | Description |
|---|---|
| `GITHUB_TOKEN` | GitHub personal access token (required) |
| `COPILOT_PLAN` | Your Copilot plan: `free`, `pro`, `business`, `enterprise` (default: `pro`) |
| `COPILOT_QUOTA` | Monthly premium request quota override |

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

A cross-platform desktop app (Windows + macOS) is planned using **Tauri + Rust** for the backend and **React + TypeScript** for the UI. See the [Roadmap](#roadmap) below.

The desktop app will feature:
- System tray icon that changes color (green/yellow/red) based on usage level
- Live gas gauge UI with smooth animations
- Configurable polling interval and threshold alerts (75%, 90%, 100%)
- Secure PAT storage in local app data directory
- Dark mode UI

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

- [ ] Desktop app (Windows + macOS) — Tauri + Rust
- [ ] Actions billing gauge
- [ ] Prepaid balance tracking
- [ ] Email/SMS threshold alerts
- [ ] Historical usage charts
