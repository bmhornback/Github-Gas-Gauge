#!/usr/bin/env python3
"""
GitHub Gas Gauge - Track your GitHub Copilot premium request usage.

Shows current token consumption and estimates how many simple or complex
tasks remain for the billing period.
"""

import argparse
import os
import sys
from datetime import date, datetime

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"

# GitHub Copilot plan monthly premium request quotas (requests per user/month)
PLAN_QUOTAS = {
    "free": 50,
    "pro": 300,
    "individual": 300,
    "business": 300,
    "enterprise": 1000,
}

# Premium request multipliers per model (relative to 1 standard request)
# Source: https://docs.github.com/en/copilot/concepts/billing/copilot-requests
MODEL_MULTIPLIERS = {
    "gpt-4o": 1,
    "gpt-4.1": 1,
    "gpt-4.5": 50,
    "gpt-5": 1,
    "claude-3.5-sonnet": 1,
    "claude-3.7-sonnet": 1,
    "gemini-2.0-flash": 0.25,
    "gemini-2.5-pro": 1,
    "o1": 10,
    "o3": 10,
    "o3-mini": 1,
}

# Typical premium request costs by task complexity
TASK_COSTS = {
    "simple": {
        "description": "Simple chat turn or inline suggestion with default model",
        "requests": 1,
    },
    "complex": {
        "description": "Copilot coding agent task or advanced model interaction",
        "requests": 15,
    },
}

GAUGE_WIDTH = 40


def get_headers(token: str) -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def get_authenticated_user(token: str) -> dict:
    """Get the authenticated user's info."""
    resp = requests.get(f"{GITHUB_API_BASE}/user", headers=get_headers(token), timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_user_billing_usage(token: str, year: int = None, month: int = None) -> dict:
    """Get billing premium request usage for the authenticated user."""
    params = {}
    if year:
        params["year"] = year
    if month:
        params["month"] = month

    resp = requests.get(
        f"{GITHUB_API_BASE}/users/billing/premium_request/usage",
        headers=get_headers(token),
        params=params,
        timeout=30,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def get_org_billing_usage(token: str, org: str, year: int = None, month: int = None) -> dict:
    """Get billing premium request usage for an organization."""
    params = {}
    if year:
        params["year"] = year
    if month:
        params["month"] = month

    resp = requests.get(
        f"{GITHUB_API_BASE}/organizations/{org}/settings/billing/premium_request/usage",
        headers=get_headers(token),
        params=params,
        timeout=30,
    )
    if resp.status_code in (403, 404):
        return None
    resp.raise_for_status()
    return resp.json()


def parse_usage(usage_data: dict) -> dict:
    """Parse usage API response into total gross and net quantities."""
    if not usage_data or "usageItems" not in usage_data:
        return {"gross": 0, "net": 0, "by_model": {}, "by_product": {}}

    total_gross = 0
    total_net = 0
    by_model = {}
    by_product = {}

    for item in usage_data.get("usageItems", []):
        gross = item.get("grossQuantity", 0) or 0
        net = item.get("netQuantity", 0) or 0
        model = item.get("model", "unknown")
        product = item.get("product", "unknown")

        total_gross += gross
        total_net += net
        by_model[model] = by_model.get(model, 0) + gross
        by_product[product] = by_product.get(product, 0) + gross

    return {
        "gross": total_gross,
        "net": total_net,
        "by_model": by_model,
        "by_product": by_product,
    }


def draw_gauge(used: int, total: int, width: int = GAUGE_WIDTH, no_color: bool = False) -> str:
    """Draw an ASCII gas gauge bar."""
    if total <= 0:
        pct = 0.0
    else:
        pct = min(used / total, 1.0)

    filled = int(pct * width)
    empty = width - filled

    if no_color:
        bar = f"[{'█' * filled}{'░' * empty}]"
    else:
        if pct >= 0.9:
            color = "\033[91m"   # red
        elif pct >= 0.7:
            color = "\033[93m"   # yellow
        else:
            color = "\033[92m"   # green
        reset = "\033[0m"
        bar = f"[{color}{'█' * filled}{reset}{'░' * empty}]"

    return bar


def estimate_remaining_tasks(remaining: int) -> dict:
    """Estimate how many tasks of each type can still be completed."""
    estimates = {}
    for task_type, info in TASK_COSTS.items():
        cost = info["requests"]
        count = remaining // cost if cost > 0 else 0
        estimates[task_type] = {"count": count, "cost_each": cost, "description": info["description"]}
    return estimates


def format_time_period(year: int, month: int) -> str:
    try:
        return datetime(year, month, 1).strftime("%B %Y")
    except Exception:
        return f"{year}-{month:02d}"


def print_gas_gauge(
    used: int,
    quota: int,
    login: str,
    org: str = None,
    year: int = None,
    month: int = None,
    by_model: dict = None,
    by_product: dict = None,
    no_color: bool = False,
):
    """Print the full gas gauge report."""
    remaining = max(quota - used, 0)
    pct_used = (used / quota * 100) if quota > 0 else 0.0
    pct_remaining = 100.0 - pct_used

    today = date.today()
    period_year = year or today.year
    period_month = month or today.month
    period_str = format_time_period(period_year, period_month)

    header = f"{'=' * 60}"
    print(header)
    print("  🔋 GitHub Copilot Gas Gauge")
    print(header)

    scope = f"Org: {org}" if org else f"User: {login}"
    print(f"  {scope}  |  Period: {period_str}")
    print()

    gauge_bar = draw_gauge(used, quota, no_color=no_color)
    print(f"  Usage   {gauge_bar}  {pct_used:.1f}%")
    print()
    print(f"  Premium Requests Used:      {used:>8,}")
    print(f"  Premium Requests Remaining: {remaining:>8,}")
    print(f"  Monthly Quota:              {quota:>8,}")
    print()

    estimates = estimate_remaining_tasks(remaining)
    print("  Remaining Task Estimates:")
    for task_type, info in estimates.items():
        label = task_type.capitalize()
        count = info["count"]
        cost = info["cost_each"]
        print(f"    {label:<10} (~{cost} req each):  {count:>6,} tasks remaining")
        print(f"               {info['description']}")
    print()

    if by_model and any(v > 0 for v in by_model.values()):
        print("  Usage by Model:")
        for model, qty in sorted(by_model.items(), key=lambda x: -x[1]):
            if qty > 0:
                print(f"    {model:<35} {qty:>6,} requests")
        print()

    if by_product and any(v > 0 for v in by_product.values()):
        print("  Usage by Product:")
        for product, qty in sorted(by_product.items(), key=lambda x: -x[1]):
            if qty > 0:
                print(f"    {product:<35} {qty:>6,} requests")
        print()

    # Refill warning
    days_in_month = 28  # conservative
    try:
        import calendar
        days_in_month = calendar.monthrange(period_year, period_month)[1]
    except Exception:
        pass

    try:
        if period_year == today.year and period_month == today.month:
            days_left = (date(period_year, period_month, days_in_month) - today).days + 1
            print(f"  Days remaining in billing period: {days_left}")
            if days_left > 0 and remaining > 0:
                daily_budget = remaining // days_left
                print(f"  Daily budget to stay on track:    {daily_budget:,} requests/day")
    except Exception:
        pass

    print(header)


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Gas Gauge – View your Copilot premium request consumption.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check your personal usage (reads GITHUB_TOKEN from environment)
  python gas_gauge.py

  # Check an organization's usage
  python gas_gauge.py --org my-org

  # Specify a different month
  python gas_gauge.py --year 2025 --month 6

  # Override quota (if you have a custom plan)
  python gas_gauge.py --quota 500

  # Disable color output (for CI/logs)
  python gas_gauge.py --no-color

Environment variables:
  GITHUB_TOKEN   GitHub personal access token (required)
  COPILOT_PLAN   Your Copilot plan: free, pro, business, enterprise (default: pro)
  COPILOT_QUOTA  Monthly premium request quota override
""",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub personal access token (default: $GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--org",
        default=None,
        help="Organization name (for org-level usage; requires admin access)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Year to query (default: current year)",
    )
    parser.add_argument(
        "--month",
        type=int,
        default=None,
        help="Month to query, 1-12 (default: current month)",
    )
    parser.add_argument(
        "--quota",
        type=int,
        default=None,
        help="Monthly premium request quota override (default: determined by plan)",
    )
    parser.add_argument(
        "--plan",
        choices=list(PLAN_QUOTAS.keys()),
        default=os.environ.get("COPILOT_PLAN", "pro"),
        help="Your Copilot plan for quota calculation (default: pro)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON usage data",
    )

    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub token required. Set GITHUB_TOKEN env var or use --token.")
        print("       Create a token at: https://github.com/settings/tokens")
        print("       Required scopes: read:org (for org usage) or copilot (for user usage)")
        sys.exit(1)

    # Determine quota
    quota_env = os.environ.get("COPILOT_QUOTA")
    if args.quota:
        quota = args.quota
    elif quota_env:
        try:
            quota = int(quota_env)
        except ValueError:
            quota = PLAN_QUOTAS.get(args.plan, PLAN_QUOTAS["pro"])
    else:
        quota = PLAN_QUOTAS.get(args.plan, PLAN_QUOTAS["pro"])

    # Get authenticated user
    try:
        user = get_authenticated_user(args.token)
        login = user.get("login", "unknown")
    except requests.exceptions.HTTPError as e:
        print(f"Error: Authentication failed – {e}")
        print("       Check your token has the required permissions.")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to GitHub API. Check your network connection.")
        sys.exit(1)

    # Fetch usage data
    usage_data = None
    if args.org:
        try:
            usage_data = get_org_billing_usage(args.token, args.org, args.year, args.month)
            if usage_data is None:
                print(f"Warning: Could not retrieve org usage for '{args.org}'.")
                print("         Ensure you have admin/billing manager access.")
        except requests.exceptions.HTTPError as e:
            print(f"Error fetching org usage: {e}")
    else:
        try:
            usage_data = get_user_billing_usage(args.token, args.year, args.month)
        except requests.exceptions.HTTPError as e:
            print(f"Error fetching user usage: {e}")

    if args.json:
        import json
        print(json.dumps(usage_data, indent=2))
        return

    parsed = parse_usage(usage_data)

    print_gas_gauge(
        used=parsed["gross"],
        quota=quota,
        login=login,
        org=args.org,
        year=args.year,
        month=args.month,
        by_model=parsed["by_model"],
        by_product=parsed["by_product"],
        no_color=args.no_color,
    )


if __name__ == "__main__":
    main()
