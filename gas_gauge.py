#!/usr/bin/env python3
"""
GitHub Gas Gauge - Track your GitHub Copilot premium request usage.

Shows current token consumption and estimates how many simple or complex
tasks remain for the billing period.
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

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

# ── External AI provider definitions ─────────────────────────────────────────
# Supported: API call made automatically when API key env var is set.
# Unsupported: No public usage API — shows helpful message with console link.
PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "env_var": "OPENAI_API_KEY",
        "limit_env_var": "OPENAI_MONTHLY_LIMIT",
        "billing_type": "cost",
        "supported": True,
    },
    "anthropic": {
        "name": "Anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "limit_env_var": "ANTHROPIC_MONTHLY_LIMIT",
        "billing_type": "cost",
        "supported": False,
        "note": (
            "No public usage API for individual keys. "
            "View at https://console.anthropic.com/settings/usage"
        ),
    },
    "deepseek": {
        "name": "DeepSeek",
        "env_var": "DEEPSEEK_API_KEY",
        "limit_env_var": "DEEPSEEK_MONTHLY_LIMIT",
        "billing_type": "balance",
        "supported": True,
    },
    "perplexity": {
        "name": "Perplexity",
        "env_var": "PERPLEXITY_API_KEY",
        "limit_env_var": "PERPLEXITY_MONTHLY_LIMIT",
        "billing_type": "cost",
        "supported": False,
        "note": (
            "No public usage API available. "
            "View at https://www.perplexity.ai/settings/api"
        ),
    },
    "gemini": {
        "name": "Google Gemini",
        "env_var": "GEMINI_API_KEY",
        "limit_env_var": "GEMINI_MONTHLY_LIMIT",
        "billing_type": "cost",
        "supported": False,
        "note": (
            "No public usage API available. "
            "View at https://aistudio.google.com/"
        ),
    },
}

ALL_PROVIDER_IDS = list(PROVIDERS.keys())

# ── Session Analytics ──────────────────────────────────────────────────────────
# Reads local Copilot session files to report token consumption per model,
# project, and session.  All processing is local-only — nothing is uploaded
# or transmitted.
#
# Session data location: ~/.copilot/session-state/<session-id>/
#   events.jsonl      – JSONL stream of session events
#   workspace.yaml    – optional; contains the working directory (cwd)
#
# Only output tokens are available in the session logs (Copilot does not record
# input tokens in the local session state).

SESSION_CACHE_VERSION = 1


def _default_cache_path():
    """Return the path to the session analytics cache file."""
    cache_dir = Path.home() / ".cache" / "github-gas-gauge"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "session-cache.json"


def _load_cache(cache_path):
    """Load the session cache from disk, or return an empty dict."""
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") == SESSION_CACHE_VERSION:
            return data.get("entries", {})
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return {}


def _save_cache(cache_path, entries):
    """Persist the session cache to disk."""
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"version": SESSION_CACHE_VERSION, "entries": entries}, f)
    except OSError:
        pass


def _file_mtime(path):
    """Return the file's mtime as a float, or -1.0 on error."""
    try:
        return path.stat().st_mtime
    except OSError:
        return -1.0


def _parse_cwd_from_yaml(yaml_text):
    """Extract the cwd field from a minimal workspace.yaml string.

    Returns the cwd string, or None if not found.
    """
    match = re.search(r"^cwd:\s*(.+)$", yaml_text, re.MULTILINE)
    if not match:
        return None
    raw = match.group(1)
    raw = re.sub(r"\s*#.*$", "", raw)   # strip trailing comment
    raw = raw.strip().strip("'\"")
    return raw or None


def _parse_copilot_events_file(events_path):
    """Parse a Copilot events.jsonl file into a list of session call dicts.

    Each call dict contains:
      model, output_tokens, timestamp, tools (list of str), user_message (str)

    Only output tokens are logged by Copilot; input tokens are always 0.
    The 'tools' list contains raw tool names from toolRequests.
    """
    try:
        text = events_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    calls = []
    current_model = ""
    pending_user_message = ""
    seen_message_ids = set()

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type", "")
        data = event.get("data", {}) or {}

        if event_type == "session.model_change":
            new_model = data.get("newModel", "")
            if new_model:
                current_model = new_model
        elif event_type == "user.message":
            pending_user_message = data.get("content", "") or ""
        elif event_type == "assistant.message":
            if not current_model:
                pending_user_message = ""
                continue
            message_id = data.get("messageId", "") or ""
            output_tokens = int(data.get("outputTokens", 0) or 0)
            if output_tokens <= 0:
                pending_user_message = ""
                continue
            if message_id:
                if message_id in seen_message_ids:
                    pending_user_message = ""
                    continue
                seen_message_ids.add(message_id)

            tool_requests = data.get("toolRequests") or []
            tools = []
            for req in tool_requests:
                if isinstance(req, dict):
                    name = req.get("name", "")
                    if name:
                        tools.append(name)

            calls.append({
                "model": current_model,
                "output_tokens": output_tokens,
                "timestamp": event.get("timestamp", "") or "",
                "tools": tools,
                "user_message": pending_user_message,
            })
            pending_user_message = ""

    return calls


def discover_copilot_sessions(session_state_dir=None):
    """Discover Copilot session directories.

    Returns a list of dicts:
      {session_id, project, events_path (Path), mtime (float)}
    """
    if session_state_dir is None:
        session_state_dir = Path.home() / ".copilot" / "session-state"

    sessions = []
    if not session_state_dir.is_dir():
        return sessions

    try:
        entries = sorted(session_state_dir.iterdir())
    except PermissionError:
        return sessions

    for entry in entries:
        if not entry.is_dir():
            continue
        events_path = entry / "events.jsonl"
        if not events_path.is_file():
            continue

        session_id = entry.name
        project = session_id  # default

        workspace_yaml = entry / "workspace.yaml"
        if workspace_yaml.is_file():
            try:
                yaml_text = workspace_yaml.read_text(encoding="utf-8", errors="replace")
                cwd = _parse_cwd_from_yaml(yaml_text)
                if cwd:
                    project = Path(cwd).name
            except OSError:
                pass

        sessions.append({
            "session_id": session_id,
            "project": project,
            "events_path": events_path,
            "mtime": _file_mtime(events_path),
        })

    return sessions


def parse_session_period(period_str):
    """Parse a session period string into (start_date, end_date).

    Returns (None, None) for 'all' (no filter).

    Supported values:
      today               – current calendar day
      week                – last 7 calendar days (inclusive of today)
      month               – current calendar month
      all                 – all time (returns None, None)
      YYYY-MM-DD:YYYY-MM-DD – explicit date range

    Raises ValueError for unrecognised or invalid inputs.
    """
    today = date.today()
    p = period_str.lower().strip()
    if p == "today":
        return today, today
    if p == "week":
        return today - timedelta(days=6), today
    if p == "month":
        return date(today.year, today.month, 1), today
    if p == "all":
        return None, None
    # Custom range YYYY-MM-DD:YYYY-MM-DD
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2}):(\d{4}-\d{2}-\d{2})", period_str.strip())
    if match:
        try:
            start = date.fromisoformat(match.group(1))
            end = date.fromisoformat(match.group(2))
        except ValueError as exc:
            raise ValueError(f"Invalid date in range '{period_str}': {exc}") from exc
        if end < start:
            raise ValueError(
                f"End date {end.isoformat()} is before start date {start.isoformat()}"
            )
        return start, end
    raise ValueError(
        f"Invalid session period '{period_str}'. "
        "Use: today, week, month, all, or YYYY-MM-DD:YYYY-MM-DD"
    )


def _call_date(call):
    """Extract the date from a session call dict's timestamp field.

    Returns a date object, or None if the timestamp is missing or unparseable.
    """
    ts = call.get("timestamp", "") or ""
    if not ts:
        return None
    # Handle ISO 8601 with optional Z or +00:00 suffix
    try:
        ts_clean = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_clean).date()
    except ValueError:
        pass
    # Fall back to bare YYYY-MM-DD prefix
    try:
        return date.fromisoformat(ts[:10])
    except (ValueError, IndexError):
        return None


def _filter_calls_by_period(calls, start_date, end_date):
    """Return only those calls whose timestamp falls within [start_date, end_date].

    If both start_date and end_date are None, returns all calls unchanged.
    Calls with no parseable timestamp are excluded when a filter is active.
    """
    if start_date is None and end_date is None:
        return list(calls)
    filtered = []
    for call in calls:
        d = _call_date(call)
        if d is None:
            continue
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue
        filtered.append(call)
    return filtered


def aggregate_session_analytics(sessions_with_calls):
    """Aggregate per-session call lists into a summary analytics dict.

    sessions_with_calls: list of dicts with keys:
      session_id, project, calls (list of call dicts)

    Returns a dict with:
      total_output_tokens, by_model, by_project, top_sessions, daily_trend
    """
    total_output_tokens = 0
    by_model = {}
    by_project = {}
    session_totals = []
    daily = {}  # ISO date string -> token count

    for session in sessions_with_calls:
        session_id = session["session_id"]
        project = session["project"]
        calls = session.get("calls", [])

        session_tokens = 0
        session_model = ""
        first_ts = ""

        for call in calls:
            tokens = call.get("output_tokens", 0) or 0
            model = call.get("model", "") or "unknown"
            ts = call.get("timestamp", "") or ""

            total_output_tokens += tokens
            session_tokens += tokens
            by_model[model] = by_model.get(model, 0) + tokens
            by_project[project] = by_project.get(project, 0) + tokens

            if not session_model:
                session_model = model
            if not first_ts and ts:
                first_ts = ts

            d = _call_date(call)
            if d is not None:
                ds = d.isoformat()
                daily[ds] = daily.get(ds, 0) + tokens

        if session_tokens > 0:
            session_totals.append({
                "session_id": session_id,
                "project": project,
                "output_tokens": session_tokens,
                "model": session_model or "unknown",
                "first_ts": first_ts,
            })

    # Top sessions sorted by token count descending
    top_sessions = sorted(session_totals, key=lambda x: -x["output_tokens"])[:10]

    # Daily trend sorted chronologically
    daily_trend = [
        {"date": ds, "output_tokens": tok}
        for ds, tok in sorted(daily.items())
    ]

    return {
        "total_output_tokens": total_output_tokens,
        "by_model": by_model,
        "by_project": by_project,
        "top_sessions": top_sessions,
        "daily_trend": daily_trend,
    }


def run_session_analytics(session_state_dir=None, period_str="week", cache_path=None):
    """Run the full session analytics pipeline.

    Discovers sessions under session_state_dir (default: ~/.copilot/session-state),
    applies file-level mtime caching, filters calls by period_str, and aggregates.

    Returns a result dict. Always returns a dict (never raises).
    Check result["available"] to detect errors.
    """
    if cache_path is None:
        cache_path = _default_cache_path()

    try:
        start_date, end_date = parse_session_period(period_str)
    except ValueError as exc:
        return {"available": False, "error": str(exc)}

    cache = _load_cache(cache_path)
    sessions = discover_copilot_sessions(
        Path(session_state_dir) if session_state_dir else None
    )
    session_dir_str = str(
        Path(session_state_dir) if session_state_dir
        else Path.home() / ".copilot" / "session-state"
    )

    if not sessions:
        return {
            "available": False,
            "session_dir": session_dir_str,
            "error": (
                f"No Copilot sessions found at {session_dir_str}. "
                "GitHub Copilot must have been used in agent/chat mode to "
                "generate local session files."
            ),
        }

    sessions_with_calls = []
    cache_updated = False

    for session_info in sessions:
        events_path = session_info["events_path"]
        mtime = session_info["mtime"]
        cache_key = str(events_path)

        cached = cache.get(cache_key)
        if cached and cached.get("mtime") == mtime:
            all_calls = cached["calls"]
        else:
            all_calls = _parse_copilot_events_file(events_path)
            cache[cache_key] = {"mtime": mtime, "calls": all_calls}
            cache_updated = True

        filtered_calls = _filter_calls_by_period(all_calls, start_date, end_date)
        if filtered_calls:
            sessions_with_calls.append({
                "session_id": session_info["session_id"],
                "project": session_info["project"],
                "calls": filtered_calls,
            })

    if cache_updated:
        _save_cache(cache_path, cache)

    analytics = aggregate_session_analytics(sessions_with_calls)
    analytics["available"] = True
    analytics["session_dir"] = session_dir_str
    analytics["period"] = period_str
    analytics["session_count"] = len(sessions)
    analytics["active_session_count"] = len(sessions_with_calls)

    if start_date and end_date:
        analytics["period_range"] = f"{start_date.isoformat()} to {end_date.isoformat()}"
    elif start_date:
        analytics["period_range"] = f"from {start_date.isoformat()}"
    elif end_date:
        analytics["period_range"] = f"through {end_date.isoformat()}"
    else:
        analytics["period_range"] = "all time"

    return analytics


def print_session_analytics(analytics, no_color=False):
    """Print the Copilot session analytics report to stdout."""
    header = f"{'=' * 60}"
    print(header)
    print("  📈 Copilot Session Analytics")
    print(header)

    if not analytics.get("available", False):
        error = analytics.get("error", "Session data not available.")
        session_dir = analytics.get("session_dir", "~/.copilot/session-state")
        print(f"  ⚠️  {error}")
        print()
        print(f"  Session state directory: {session_dir}")
        print("  ℹ️  Session analytics reads local Copilot session files.")
        print("      No data is uploaded or shared externally.")
        print(header)
        return

    period_range = analytics.get("period_range", analytics.get("period", ""))
    session_dir = analytics.get("session_dir", "")
    total_sessions = analytics.get("session_count", 0)
    active_sessions = analytics.get("active_session_count", 0)
    total_tokens = analytics.get("total_output_tokens", 0)

    print(f"  Period:             {period_range}")
    print(f"  Session directory:  {session_dir}")
    print()
    print(f"  Sessions found (total):   {total_sessions:>8,}")
    print(f"  Sessions in period:       {active_sessions:>8,}")
    print(f"  Output tokens (period):   {total_tokens:>8,}")
    print()

    by_model = analytics.get("by_model", {})
    if by_model:
        print("  Output Tokens by Model:")
        for model, tokens in sorted(by_model.items(), key=lambda x: -x[1]):
            if tokens > 0:
                pct = tokens / total_tokens * 100 if total_tokens > 0 else 0.0
                print(f"    {model:<35} {tokens:>8,}  ({pct:.1f}%)")
        print()

    by_project = analytics.get("by_project", {})
    if by_project:
        print("  Output Tokens by Project:")
        for project, tokens in sorted(by_project.items(), key=lambda x: -x[1])[:10]:
            if tokens > 0:
                pct = tokens / total_tokens * 100 if total_tokens > 0 else 0.0
                print(f"    {project:<35} {tokens:>8,}  ({pct:.1f}%)")
        print()

    top_sessions = analytics.get("top_sessions", [])
    if top_sessions:
        print("  Top Sessions by Output Tokens:")
        print(f"    {'Project':<25}  {'Model':<20}  {'Tokens':>8}  Date")
        print(f"    {'-' * 70}")
        for session in top_sessions[:5]:
            project = (session.get("project", "") or "")[:25]
            model = (session.get("model", "") or "")[:20]
            tokens = session.get("output_tokens", 0)
            ts = (session.get("first_ts", "") or "")[:10]
            print(f"    {project:<25}  {model:<20}  {tokens:>8,}  {ts}")
        print()

    daily_trend = analytics.get("daily_trend", [])
    if daily_trend:
        recent = daily_trend[-7:]
        max_val = max((d["output_tokens"] for d in recent), default=1) or 1
        bar_width = 20
        print("  Daily Token Usage (most recent 7 days):")
        for day in recent:
            date_str = day["date"]
            tokens = day["output_tokens"]
            filled = int(tokens / max_val * bar_width)
            empty = bar_width - filled
            if no_color:
                bar = f"{'█' * filled}{'░' * empty}"
            else:
                ratio = tokens / max_val
                if ratio >= 0.9:
                    color = "\033[91m"
                elif ratio >= 0.6:
                    color = "\033[93m"
                else:
                    color = "\033[92m"
                reset = "\033[0m"
                bar = f"{color}{'█' * filled}{reset}{'░' * empty}"
            print(f"    {date_str}  [{bar}]  {tokens:>8,}")
        print()

    print("  ℹ️  Only output tokens are available in Copilot session files.")
    print("      Input tokens are not logged; actual API costs are higher.")
    print("      Data is read locally — nothing is uploaded or shared.")
    print(header)


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


def get_user_actions_billing(token: str) -> dict:
    """Get Actions billing usage for the authenticated user."""
    resp = requests.get(
        f"{GITHUB_API_BASE}/user/settings/billing/actions",
        headers=get_headers(token),
        timeout=30,
    )
    if resp.status_code in (403, 404):
        return None
    resp.raise_for_status()
    return resp.json()


def get_org_actions_billing(token: str, org: str) -> dict:
    """Get Actions billing usage for an organization."""
    resp = requests.get(
        f"{GITHUB_API_BASE}/orgs/{org}/settings/billing/actions",
        headers=get_headers(token),
        timeout=30,
    )
    if resp.status_code in (403, 404):
        return None
    resp.raise_for_status()
    return resp.json()


def parse_actions_usage(data: dict) -> dict:
    """Parse Actions billing API response into a normalized dict."""
    if not data:
        return {
            "minutes_used": 0,
            "included_minutes": 0,
            "minutes_used_breakdown": {},
            "total_paid_minutes_used": 0,
        }
    return {
        "minutes_used": int(data.get("total_minutes_used", 0) or 0),
        "included_minutes": int(data.get("included_minutes", 0) or 0),
        "minutes_used_breakdown": data.get("minutes_used_breakdown", {}) or {},
        "total_paid_minutes_used": int(data.get("total_paid_minutes_used", 0) or 0),
    }


def print_actions_gauge(
    minutes_used: int,
    included_minutes: int,
    total_paid_minutes_used: int,
    minutes_used_breakdown: dict = None,
    login: str = "unknown",
    org: str = None,
    no_color: bool = False,
):
    """Print the Actions billing gas gauge report."""
    remaining = max(included_minutes - minutes_used, 0)
    pct_used = (minutes_used / included_minutes * 100) if included_minutes > 0 else 0.0

    # Per-minute overage pricing for Ubuntu (most common runner)
    ubuntu_per_minute = 0.008
    estimated_cost = total_paid_minutes_used * ubuntu_per_minute

    header = f"{'=' * 60}"
    print(header)
    print("  ⚙️  GitHub Actions Usage")
    print(header)

    scope = f"Org: {org}" if org else f"User: {login}"
    print(f"  {scope}")
    print()

    gauge_bar = draw_gauge(minutes_used, included_minutes, no_color=no_color)
    print(f"  Usage   {gauge_bar}  {pct_used:.1f}%")
    print()
    print(f"  Minutes Used (this month):   {minutes_used:>8,}")
    print(f"  Included Minutes:            {included_minutes:>8,}")
    print(f"  Minutes Remaining:           {remaining:>8,}")
    print()

    if minutes_used_breakdown:
        print("  Minutes by Runner OS:")
        for os_name, mins in sorted(minutes_used_breakdown.items(), key=lambda x: -x[1]):
            if mins and mins > 0:
                print(f"    {os_name:<20} {mins:>8,} minutes")
        print()

    print(f"  Paid Minutes Used (overage): {total_paid_minutes_used:>8,}")
    print(f"  Estimated Overage Cost:      ${estimated_cost:>7.2f}")
    print(header)


def get_openai_usage(api_key: str, year: int = None, month: int = None) -> dict:
    """Fetch OpenAI billing usage for the given month via /v1/dashboard/billing/usage.

    Returns the raw JSON dict, or None on authentication / not-found errors.
    ``total_usage`` in the response is in USD cents (divide by 100 for USD).
    """
    import calendar as _cal
    today = date.today()
    period_year = year or today.year
    period_month = month or today.month

    start_date = f"{period_year}-{period_month:02d}-01"
    last_day = _cal.monthrange(period_year, period_month)[1]
    end_date = f"{period_year}-{period_month:02d}-{last_day:02d}"

    resp = requests.get(
        "https://api.openai.com/v1/dashboard/billing/usage",
        headers={"Authorization": f"Bearer {api_key}"},
        params={"start_date": start_date, "end_date": end_date},
        timeout=30,
    )
    if resp.status_code in (401, 403, 404):
        return None
    resp.raise_for_status()
    return resp.json()


def parse_openai_usage(data: dict) -> dict:
    """Parse an OpenAI billing/usage API response.

    ``total_usage`` is in USD cents; this function converts to USD.
    """
    if not data:
        return {"cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0,
                "total_tokens": 0, "by_model": {}}

    total_usage_cents = data.get("total_usage", 0) or 0
    cost_usd = total_usage_cents / 100.0

    by_model = {}
    for day in data.get("daily_costs", []):
        for item in day.get("line_items", []):
            name = item.get("name", "unknown")
            cost_cents = item.get("cost", 0) or 0
            by_model[name] = by_model.get(name, 0.0) + cost_cents / 100.0

    return {
        "cost_usd": cost_usd,
        "input_tokens": 0,    # billing endpoint doesn't expose token counts
        "output_tokens": 0,
        "total_tokens": 0,
        "by_model": by_model,
    }


def get_deepseek_balance(api_key: str) -> dict:
    """Fetch DeepSeek account credit balance via /user/balance.

    Returns the raw JSON dict, or None on authentication / not-found errors.
    """
    resp = requests.get(
        "https://api.deepseek.com/user/balance",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        timeout=30,
    )
    if resp.status_code in (401, 403, 404):
        return None
    resp.raise_for_status()
    return resp.json()


def parse_deepseek_balance(data: dict) -> dict:
    """Parse a DeepSeek /user/balance response into a normalised dict."""
    if not data:
        return {"balance": 0.0, "currency": "USD", "is_available": False}

    balance_infos = data.get("balance_infos", [])
    total_balance = 0.0
    currency = "USD"
    for info in balance_infos:
        currency = info.get("currency", "USD")
        try:
            total_balance = float(info.get("total_balance", 0) or 0)
        except (ValueError, TypeError):
            total_balance = 0.0
        break  # use first balance entry

    return {
        "balance": total_balance,
        "currency": currency,
        "is_available": data.get("is_available", True),
    }


def fetch_provider_usage(provider_id: str, year: int = None, month: int = None) -> dict:
    """Fetch and normalise usage for a single external AI provider.

    The API key is read from the provider's ``env_var``.  An optional monthly
    spending limit is read from ``limit_env_var``.

    Always returns a dict — never raises.  Callers should check ``available``.
    """
    config = PROVIDERS.get(provider_id)
    if not config:
        return {"available": False, "error": f"Unknown provider: {provider_id}",
                "provider_id": provider_id, "name": provider_id}

    api_key = os.environ.get(config["env_var"], "")

    if not config.get("supported", False):
        return {
            "provider_id": provider_id,
            "name": config["name"],
            "available": False,
            "api_key_set": bool(api_key),
            "note": config.get("note", "No public API available."),
        }

    if not api_key:
        return {
            "provider_id": provider_id,
            "name": config["name"],
            "available": False,
            "api_key_set": False,
            "note": f"Set {config['env_var']} environment variable to enable.",
        }

    # Read optional user-defined monthly limit from env var
    limit_usd = None
    limit_raw = os.environ.get(config.get("limit_env_var", ""), "")
    if limit_raw:
        try:
            limit_usd = float(limit_raw)
        except ValueError:
            pass

    try:
        if provider_id == "openai":
            raw = get_openai_usage(api_key, year, month)
            if raw is None:
                return {
                    "provider_id": provider_id,
                    "name": config["name"],
                    "available": False,
                    "api_key_set": True,
                    "note": (
                        "Could not fetch usage. Ensure your API key has "
                        "billing read access."
                    ),
                }
            parsed = parse_openai_usage(raw)
            return {
                "provider_id": provider_id,
                "name": config["name"],
                "available": True,
                "billing_type": "cost",
                "cost": parsed["cost_usd"],
                "input_tokens": parsed["input_tokens"],
                "output_tokens": parsed["output_tokens"],
                "total_tokens": parsed["total_tokens"],
                "by_model": parsed["by_model"],
                "limit": limit_usd,
            }

        if provider_id == "deepseek":
            raw = get_deepseek_balance(api_key)
            if raw is None:
                return {
                    "provider_id": provider_id,
                    "name": config["name"],
                    "available": False,
                    "api_key_set": True,
                    "note": "Could not fetch balance. Check your DeepSeek API key.",
                }
            parsed = parse_deepseek_balance(raw)
            return {
                "provider_id": provider_id,
                "name": config["name"],
                "available": True,
                "billing_type": "balance",
                "balance": parsed["balance"],
                "currency": parsed["currency"],
                "is_available": parsed["is_available"],
                "limit": limit_usd,
            }

    except requests.exceptions.RequestException as exc:
        return {
            "provider_id": provider_id,
            "name": config["name"],
            "available": False,
            "api_key_set": True,
            "note": f"API error: {exc}",
        }

    return {
        "provider_id": provider_id,
        "name": config["name"],
        "available": False,
        "note": "Provider not yet implemented.",
    }


def print_provider_gauge(usage: dict, no_color: bool = False):
    """Print a gas gauge section for an external AI provider."""
    name = usage.get("name", usage.get("provider_id", "Unknown Provider"))
    provider_id = usage.get("provider_id", "")
    header = f"{'=' * 60}"

    print(header)
    print(f"  🤖 {name} Usage")
    print(header)

    if not usage.get("available", False):
        note = usage.get("note", "Usage data not available.")
        print(f"  ⚠️  {note}")
        # Show env var hint only for unsupported providers (supported providers'
        # "missing key" note already mentions the variable name)
        if not usage.get("api_key_set", True):
            cfg = PROVIDERS.get(provider_id, {})
            if cfg.get("supported", False):
                # note already says "Set X_API_KEY to enable" — no duplicate needed
                pass
            else:
                env_var = cfg.get("env_var", "API_KEY")
                print(f"     Set {env_var} to enable future API support.")
        print(header)
        return

    billing_type = usage.get("billing_type", "cost")

    if billing_type == "balance":
        # Credit / balance-based providers (e.g. DeepSeek)
        balance = usage.get("balance", 0.0)
        currency = usage.get("currency", "USD")
        limit = usage.get("limit")

        if not usage.get("is_available", True):
            print("  ⚠️  Account not active or balance unavailable.")
            print(header)
            return

        print(f"  Account Balance:  {currency} {balance:.4f}")
        print()

        if limit and limit > 0:
            pct_spent = min((limit - balance) / limit, 1.0)
            gauge = draw_gauge(int(pct_spent * 1000), 1000, no_color=no_color)
            pct_remaining = max(1.0 - pct_spent, 0.0)
            print(f"  Balance   {gauge}  {pct_remaining * 100:.1f}% remaining")
            print(f"            {currency} {balance:.4f} of {currency} {limit:.2f} remaining")
        else:
            limit_env_var = PROVIDERS.get(provider_id, {}).get("limit_env_var", "LIMIT")
            print(f"  (Set {limit_env_var} to enable gauge)")

    else:
        # Cost / spend-based providers (e.g. OpenAI)
        cost = usage.get("cost", 0.0)
        limit = usage.get("limit")
        by_model = usage.get("by_model", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        if limit and limit > 0:
            pct = min(cost / limit, 1.0)
            gauge = draw_gauge(int(cost * 100), int(limit * 100), no_color=no_color)
            print(f"  Spending  {gauge}  {pct * 100:.1f}%")
            print(f"            ${cost:.4f} of ${limit:.2f} monthly limit")
        else:
            limit_env_var = PROVIDERS.get(provider_id, {}).get("limit_env_var", "LIMIT")
            print(f"  Cost This Period: ${cost:.4f}")
            print(f"  (Set {limit_env_var} to enable spending gauge)")

        print()

        if total_tokens > 0:
            print(f"  Total Tokens:   {total_tokens:>12,}")
            if input_tokens > 0:
                print(f"    Input:        {input_tokens:>12,}")
            if output_tokens > 0:
                print(f"    Output:       {output_tokens:>12,}")
            print()

        if by_model and any(v > 0 for v in by_model.values()):
            print("  Usage by Model:")
            for model, val in sorted(by_model.items(), key=lambda x: -x[1]):
                if val > 0:
                    print(f"    {model:<35} ${val:.4f}")
            print()

    print(header)


def main():
    parser = argparse.ArgumentParser(
        description="GitHub Gas Gauge – View your Copilot premium request consumption and AI provider token usage.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check your personal GitHub usage (reads GITHUB_TOKEN from environment)
  python gas_gauge.py

  # Check an organization's usage
  python gas_gauge.py --org my-org

  # Show only Actions billing
  python gas_gauge.py --actions-only

  # Show only Copilot section
  python gas_gauge.py --copilot-only

  # Show OpenAI + DeepSeek provider gauges alongside GitHub sections
  python gas_gauge.py --providers openai,deepseek

  # Show all external providers, skip GitHub sections
  python gas_gauge.py --providers-only

  # Show all providers with a specific provider only
  python gas_gauge.py --providers-only --providers openai

  # Specify a different month
  python gas_gauge.py --year 2025 --month 6

  # Override quota (if you have a custom plan)
  python gas_gauge.py --quota 500

  # Disable color output (for CI/logs)
  python gas_gauge.py --no-color

  # Show local Copilot session analytics (reads ~/.copilot/session-state/)
  python gas_gauge.py --session-analytics

  # Session analytics for today only
  python gas_gauge.py --session-analytics --session-period today

  # Export session analytics as JSON
  python gas_gauge.py --session-json

Environment variables:
  GITHUB_TOKEN          GitHub personal access token (required for GitHub sections)
  COPILOT_PLAN          Copilot plan: free, pro, business, enterprise (default: pro)
  COPILOT_QUOTA         Monthly premium request quota override
  OPENAI_API_KEY        OpenAI API key (enables OpenAI usage gauge)
  OPENAI_MONTHLY_LIMIT  Monthly spending limit in USD (enables OpenAI gauge bar)
  DEEPSEEK_API_KEY      DeepSeek API key (enables DeepSeek balance gauge)
  DEEPSEEK_MONTHLY_LIMIT  Credit limit in USD (enables DeepSeek gauge bar)
  ANTHROPIC_API_KEY     Anthropic API key (set for future API support)
  PERPLEXITY_API_KEY    Perplexity API key (set for future API support)
  GEMINI_API_KEY        Google Gemini API key (set for future API support)
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
        help="Output raw JSON usage data (Copilot only)",
    )
    parser.add_argument(
        "--actions-only",
        action="store_true",
        help="Show only Actions billing, skip Copilot section",
    )
    parser.add_argument(
        "--copilot-only",
        action="store_true",
        help="Show only Copilot section, skip Actions billing",
    )
    parser.add_argument(
        "--providers",
        default=None,
        metavar="PROVIDER[,...]",
        help=(
            "Comma-separated external AI providers to show, or 'all'. "
            "Options: " + ", ".join(ALL_PROVIDER_IDS)
        ),
    )
    parser.add_argument(
        "--providers-only",
        action="store_true",
        help=(
            "Show only external provider gauges — skip GitHub Copilot and Actions sections. "
            "Implies --providers all when --providers is not specified."
        ),
    )
    parser.add_argument(
        "--session-analytics",
        action="store_true",
        help=(
            "Show Copilot session analytics by reading local session files from "
            "~/.copilot/session-state/. No data is uploaded or transmitted."
        ),
    )
    parser.add_argument(
        "--session-period",
        default="week",
        metavar="PERIOD",
        help=(
            "Time period for session analytics: today, week (default), month, all, "
            "or YYYY-MM-DD:YYYY-MM-DD. Requires --session-analytics or --session-json."
        ),
    )
    parser.add_argument(
        "--session-dir",
        default=None,
        metavar="DIR",
        help="Override the Copilot session-state directory (default: ~/.copilot/session-state).",
    )
    parser.add_argument(
        "--session-json",
        action="store_true",
        help=(
            "Output session analytics as JSON to stdout and exit. "
            "Skips all other output sections."
        ),
    )

    args = parser.parse_args()

    if args.actions_only and args.copilot_only:
        print("Error: --actions-only and --copilot-only are mutually exclusive.")
        sys.exit(1)

    # Resolve which external providers to show
    if args.providers_only and not args.providers:
        # Default: show all providers (those with API keys configured)
        providers_to_show = ALL_PROVIDER_IDS
    elif args.providers:
        if args.providers.lower() == "all":
            providers_to_show = ALL_PROVIDER_IDS
        else:
            providers_to_show = [p.strip().lower() for p in args.providers.split(",")]
            invalid = [p for p in providers_to_show if p not in PROVIDERS]
            if invalid:
                print(f"Error: Unknown provider(s): {', '.join(invalid)}")
                print(f"       Valid providers: {', '.join(ALL_PROVIDER_IDS)}")
                sys.exit(1)
    else:
        providers_to_show = []

    show_copilot = not args.actions_only and not args.providers_only
    show_actions = not args.copilot_only and not args.providers_only

    # --session-json outputs only session analytics JSON and exits immediately.
    # Skip all GitHub API sections in that case.
    if args.session_json:
        show_copilot = False
        show_actions = False
        providers_to_show = []

    # GitHub sections need a token; skip gracefully when --providers-only
    if (show_copilot or show_actions) and not args.token:
        print("Error: GitHub token required. Set GITHUB_TOKEN env var or use --token.")
        print("       Create a token at: https://github.com/settings/tokens")
        print("       Required scopes: read:org (for org usage) or copilot (for user usage)")
        print("       Use --providers-only or --session-json to skip GitHub sections.")
        sys.exit(1)

    login = "unknown"
    if show_copilot or show_actions:
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

        # Fetch and display Copilot usage
        if show_copilot:
            usage_data = None
            if args.org:
                try:
                    usage_data = get_org_billing_usage(args.token, args.org, args.year, args.month)
                    if usage_data is None:
                        print(f"Warning: Could not retrieve org Copilot usage for '{args.org}'.")
                        print("         Ensure you have admin/billing manager access.")
                except requests.exceptions.HTTPError as e:
                    print(f"Error fetching org Copilot usage: {e}")
            else:
                try:
                    usage_data = get_user_billing_usage(args.token, args.year, args.month)
                except requests.exceptions.HTTPError as e:
                    print(f"Error fetching user Copilot usage: {e}")

            if args.json:
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

        # Fetch and display Actions usage
        if show_actions:
            actions_data = None
            if args.org:
                try:
                    actions_data = get_org_actions_billing(args.token, args.org)
                    if actions_data is None:
                        print(f"Warning: Could not retrieve org Actions billing for '{args.org}'.")
                        print("         Ensure you have admin/billing manager access.")
                except requests.exceptions.HTTPError as e:
                    print(f"Error fetching org Actions billing: {e}")
            else:
                try:
                    actions_data = get_user_actions_billing(args.token)
                except requests.exceptions.HTTPError as e:
                    print(f"Error fetching Actions billing: {e}")

            if actions_data is not None:
                parsed_actions = parse_actions_usage(actions_data)
                print_actions_gauge(
                    minutes_used=parsed_actions["minutes_used"],
                    included_minutes=parsed_actions["included_minutes"],
                    total_paid_minutes_used=parsed_actions["total_paid_minutes_used"],
                    minutes_used_breakdown=parsed_actions["minutes_used_breakdown"],
                    login=login,
                    org=args.org,
                    no_color=args.no_color,
                )
            elif not args.org:
                print("Note: Actions billing data not available for this account.")

    # Fetch and display external provider gauges
    for provider_id in providers_to_show:
        usage = fetch_provider_usage(provider_id, args.year, args.month)
        print_provider_gauge(usage, no_color=args.no_color)

    # Session analytics (--session-json exits early with JSON; --session-analytics
    # appends the text section to whatever else was already printed)
    if args.session_analytics or args.session_json:
        analytics = run_session_analytics(
            session_state_dir=args.session_dir,
            period_str=args.session_period,
        )
        if args.session_json:
            print(json.dumps(analytics, indent=2, default=str))
            return
        print_session_analytics(analytics, no_color=args.no_color)


if __name__ == "__main__":
    main()
