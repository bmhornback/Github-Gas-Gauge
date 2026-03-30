import { BillingData } from "../App";

interface BalancePanelProps {
  billing: BillingData | null;
}

function BalancePanel({ billing }: BalancePanelProps) {
  if (!billing) {
    return (
      <section className="panel balance-panel">
        <h2 className="panel-title">📊 Usage Summary</h2>
        <div className="panel-body">
          <p className="muted">No billing data available yet.</p>
        </div>
      </section>
    );
  }

  const { total_minutes_used, included_minutes, minutes_used_breakdown } = billing;
  const remaining = Math.max(included_minutes - total_minutes_used, 0);
  const pct = included_minutes > 0 ? (total_minutes_used / included_minutes) * 100 : 0;

  return (
    <section className="panel balance-panel">
      <h2 className="panel-title">📊 Usage Summary</h2>
      <div className="panel-body">
        <div className="stat-row">
          <span className="stat-label">Included Minutes</span>
          <span className="stat-value">{included_minutes.toFixed(0)}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Used</span>
          <span className="stat-value">{total_minutes_used.toFixed(0)}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Remaining</span>
          <span className={`stat-value ${remaining === 0 ? "overage" : ""}`}>
            {remaining.toFixed(0)}
          </span>
        </div>

        {/* Progress bar */}
        <div className="progress-bar-bg" title={`${pct.toFixed(1)}% used`}>
          <div
            className="progress-bar-fill"
            style={{
              width: `${Math.min(pct, 100)}%`,
              backgroundColor:
                pct >= 90 ? "#ef4444" : pct >= 75 ? "#f59e0b" : "#22c55e",
            }}
          />
        </div>

        {/* Breakdown by OS */}
        <div className="breakdown-grid">
          <div className="breakdown-item">
            <span className="breakdown-os">🐧 Ubuntu</span>
            <span>{minutes_used_breakdown.ubuntu.toFixed(0)} min</span>
          </div>
          <div className="breakdown-item">
            <span className="breakdown-os">🍎 macOS</span>
            <span>{minutes_used_breakdown.macos.toFixed(0)} min</span>
          </div>
          <div className="breakdown-item">
            <span className="breakdown-os">🪟 Windows</span>
            <span>{minutes_used_breakdown.windows.toFixed(0)} min</span>
          </div>
        </div>
      </div>
    </section>
  );
}

export default BalancePanel;
