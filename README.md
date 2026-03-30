# GitHub Gas Gauge 🔋

A CLI tool and GitHub Action to view your GitHub Copilot premium request consumption and estimate how many simple or complex tasks you have remaining in the current billing period.

## Features

- **Visual gas gauge** showing used vs. remaining premium requests
- **Task estimates** – see how many simple (chat) or complex (coding agent) tasks remain
- **Per-model breakdown** of usage
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

### Options

```
usage: gas_gauge.py [-h] [--token TOKEN] [--org ORG] [--year YEAR]
                    [--month MONTH] [--quota QUOTA]
                    [--plan {free,pro,individual,business,enterprise}]
                    [--no-color] [--json]

options:
  --token TOKEN     GitHub personal access token (default: $GITHUB_TOKEN)
  --org ORG         Organization name (for org-level usage)
  --year YEAR       Year to query (default: current year)
  --month MONTH     Month to query, 1-12 (default: current month)
  --quota QUOTA     Monthly premium request quota override
  --plan PLAN       Copilot plan: free, pro, business, enterprise (default: pro)
  --no-color        Disable color output
  --json            Output raw JSON usage data
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

## GitHub Actions

Run this tool automatically via the included workflow:

1. Go to **Actions** → **GitHub Gas Gauge** → **Run workflow**
2. Optionally specify an org name, plan type, or quota override
3. Or add `COPILOT_TOKEN` to your repository secrets for a dedicated token

The workflow also runs daily at 9am UTC via schedule.

## Running Tests

```bash
python -m pytest test_gas_gauge.py -v
```
