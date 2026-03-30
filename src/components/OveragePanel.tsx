interface OveragePanelProps {
  paidMinutes: number;
  breakdown: {
    ubuntu: number;
    macos: number;
    windows: number;
  };
}

/** Estimated cost per paid minute by runner type (USD). */
const RATE_PER_MINUTE: Record<string, number> = {
  ubuntu: 0.008,
  macos: 0.08,
  windows: 0.016,
};

function OveragePanel({ paidMinutes, breakdown }: OveragePanelProps) {
  if (paidMinutes <= 0) return null;

  // Estimate cost from breakdown (overage portion only, simplified).
  const estimatedCost =
    breakdown.ubuntu * RATE_PER_MINUTE.ubuntu +
    breakdown.macos * RATE_PER_MINUTE.macos +
    breakdown.windows * RATE_PER_MINUTE.windows;

  return (
    <section className="panel overage-panel">
      <h2 className="panel-title">⚠️ Overage Usage</h2>
      <div className="panel-body">
        <div className="stat-row">
          <span className="stat-label">Paid Minutes Used</span>
          <span className="stat-value overage">{paidMinutes.toFixed(0)}</span>
        </div>
        <div className="stat-row">
          <span className="stat-label">Estimated Overage Cost</span>
          <span className="stat-value overage">${estimatedCost.toFixed(2)}</span>
        </div>
        <div className="breakdown-grid">
          <div className="breakdown-item">
            <span className="breakdown-os">🐧 Ubuntu</span>
            <span>{breakdown.ubuntu.toFixed(0)} min</span>
          </div>
          <div className="breakdown-item">
            <span className="breakdown-os">🍎 macOS</span>
            <span>{breakdown.macos.toFixed(0)} min</span>
          </div>
          <div className="breakdown-item">
            <span className="breakdown-os">🪟 Windows</span>
            <span>{breakdown.windows.toFixed(0)} min</span>
          </div>
        </div>
        <a
          href="https://github.com/settings/billing"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary btn-small"
        >
          Manage Billing on GitHub ↗
        </a>
      </div>
    </section>
  );
}

export default OveragePanel;
