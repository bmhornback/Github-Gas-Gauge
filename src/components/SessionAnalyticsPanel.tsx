import { invoke } from "@tauri-apps/api/core";
import { useState, useEffect, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SessionSummary {
  session_id: string;
  project: string;
  output_tokens: number;
  model: string;
  first_ts: string;
}

export interface DailyUsage {
  date: string;
  output_tokens: number;
}

export interface SessionAnalytics {
  available: boolean;
  session_dir: string;
  total_output_tokens: number;
  session_count: number;
  active_session_count: number;
  by_model: Record<string, number>;
  by_project: Record<string, number>;
  top_sessions: SessionSummary[];
  daily_trend: DailyUsage[];
}

// ─── Theme constants ──────────────────────────────────────────────────────────
// These mirror the CSS custom properties defined in app.css so that inline SVG
// styles stay consistent with the overall design system.
const COLOR_HIGH = "var(--accent-red, #ef4444)";
const COLOR_MID = "var(--accent-yellow, #f59e0b)";
const COLOR_LOW = "var(--accent-green, #22c55e)";
const COLOR_MODEL = "var(--accent-blue, #3b82f6)";
const COLOR_PROJECT = "#8b5cf6"; // violet — no CSS variable defined yet

function trendColor(pct: number): string {
  if (pct >= 0.9) return COLOR_HIGH;
  if (pct >= 0.5) return COLOR_MID;
  return COLOR_LOW;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

// ─── Trend Chart ──────────────────────────────────────────────────────────────

function TrendChart({ trend }: { trend: DailyUsage[] }) {
  const recent = trend.slice(-14);
  if (recent.length === 0) return null;

  const maxTokens = Math.max(...recent.map((d) => d.output_tokens), 1);
  const chartH = 72;
  const chartW = 300;
  const gap = 2;
  const barW = Math.max(Math.floor((chartW - gap * (recent.length - 1)) / recent.length), 4);

  return (
    <div className="trend-chart-wrapper">
      <svg
        width={chartW}
        height={chartH + 20}
        viewBox={`0 0 ${chartW} ${chartH + 20}`}
        aria-label="Daily token usage trend"
      >
        {recent.map((day, i) => {
          const pct = day.output_tokens / maxTokens;
          const barH = Math.max(Math.round(pct * chartH), 2);
          const x = i * (barW + gap);
          const y = chartH - barH;
          const color = trendColor(pct);
          return (
            <g key={day.date}>
              <rect x={x} y={y} width={barW} height={barH} fill={color} rx="2">
                <title>
                  {day.date}: {day.output_tokens.toLocaleString()} tokens
                </title>
              </rect>
              {(recent.length <= 7 || i % 2 === 0) && (
                <text
                  x={x + barW / 2}
                  y={chartH + 13}
                  textAnchor="middle"
                  fontSize="8"
                  fill="#64748b"
                >
                  {day.date.slice(5)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ─── Percentage Bar Row ───────────────────────────────────────────────────────

function PctRow({
  label,
  tokens,
  total,
  color,
}: {
  label: string;
  tokens: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (tokens / total) * 100 : 0;
  return (
    <div className="sa-model-row">
      <span className="sa-model-name" title={label}>
        {label}
      </span>
      <span className="sa-model-tokens">
        {formatTokens(tokens)} ({pct.toFixed(1)}%)
      </span>
      <div className="progress-bar-bg">
        <div
          className="progress-bar-fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function SessionAnalyticsPanel() {
  const [analytics, setAnalytics] = useState<SessionAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await invoke<SessionAnalytics>("get_session_analytics");
      setAnalytics(data);
    } catch (e) {
      setError(typeof e === "string" ? e : "Failed to load session analytics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  if (loading) {
    return (
      <section className="panel">
        <h2 className="panel-title">📈 Session Analytics</h2>
        <div className="panel-body">
          <p className="muted">Loading session data…</p>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel">
        <h2 className="panel-title">📈 Session Analytics</h2>
        <div className="panel-body">
          <p className="muted">⚠️ {error}</p>
        </div>
      </section>
    );
  }

  if (!analytics?.available) {
    return (
      <section className="panel">
        <h2 className="panel-title">📈 Session Analytics</h2>
        <div className="panel-body">
          <p className="muted">
            No Copilot session data found. Session analytics reads local files
            from{" "}
            <code className="sa-code">~/.copilot/session-state/</code>.
            GitHub Copilot agent or chat usage generates these files.
          </p>
          <p className="muted sa-hint">
            Session directory: {analytics?.session_dir ?? "~/.copilot/session-state"}
          </p>
          <p className="muted sa-hint">
            ℹ️ No data is uploaded or shared externally.
          </p>
          <button className="btn-primary btn-small" onClick={fetchAnalytics}>
            Retry
          </button>
        </div>
      </section>
    );
  }

  const topModels = Object.entries(analytics.by_model)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  const topProjects = Object.entries(analytics.by_project)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  return (
    <section className="panel">
      <h2 className="panel-title">📈 Session Analytics (Copilot)</h2>
      <div className="panel-body">

        {/* Summary stats */}
        <div className="stat-row">
          <span className="stat-label">Output Tokens (all sessions)</span>
          <span className="stat-value">
            {analytics.total_output_tokens.toLocaleString()}
          </span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Sessions on Disk</span>
          <span className="stat-value">{analytics.session_count}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Active Sessions</span>
          <span className="stat-value">{analytics.active_session_count}</span>
        </div>

        {/* Daily trend chart */}
        {analytics.daily_trend.length > 0 && (
          <div className="sa-section">
            <h3 className="sa-subheading">Daily Token Usage</h3>
            <TrendChart trend={analytics.daily_trend} />
          </div>
        )}

        {/* By model */}
        {topModels.length > 0 && (
          <div className="sa-section">
            <h3 className="sa-subheading">Output Tokens by Model</h3>
            {topModels.map(([model, tokens]) => (
              <PctRow
                key={model}
                label={model}
                tokens={tokens}
                total={analytics.total_output_tokens}
                color={COLOR_MODEL}
              />
            ))}
          </div>
        )}

        {/* By project */}
        {topProjects.length > 0 && (
          <div className="sa-section">
            <h3 className="sa-subheading">Output Tokens by Project</h3>
            {topProjects.map(([project, tokens]) => (
              <PctRow
                key={project}
                label={project}
                tokens={tokens}
                total={analytics.total_output_tokens}
                color={COLOR_PROJECT}
              />
            ))}
          </div>
        )}

        {/* Top sessions leaderboard */}
        {analytics.top_sessions.length > 0 && (
          <div className="sa-section">
            <h3 className="sa-subheading">Top Sessions by Output Tokens</h3>
            <div className="sa-leaderboard">
              {analytics.top_sessions.slice(0, 5).map((s, i) => (
                <div key={s.session_id} className="sa-session-row">
                  <span className="sa-rank">#{i + 1}</span>
                  <div className="sa-session-info">
                    <span className="sa-session-project">{s.project}</span>
                    <span className="sa-session-meta">
                      {s.model} · {s.first_ts.slice(0, 10)}
                    </span>
                  </div>
                  <span className="sa-session-tokens">
                    {s.output_tokens.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer note + refresh */}
        <div className="sa-footer">
          <p className="muted sa-hint">
            ℹ️ Only output tokens are available in Copilot session logs. Input
            tokens are not recorded. Data is read locally — nothing is shared.
          </p>
          <button className="btn-secondary btn-small" onClick={fetchAnalytics}>
            Refresh
          </button>
        </div>
      </div>
    </section>
  );
}
