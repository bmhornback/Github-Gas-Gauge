import GasGauge from "./GasGauge";

export interface ProviderUsage {
  provider_id: string;
  name: string;
  available: boolean;
  billing_type: string;      // "cost" or "balance"
  cost_usd: number;          // cost-based: total spend this period
  balance_usd: number;       // balance-based: remaining credit
  currency: string;
  limit_usd?: number | null;
  percent_used: number;      // 0.0–1.0
  by_model: Record<string, number>;
  note?: string | null;
}

interface ProviderGaugesProps {
  providers: ProviderUsage[];
}

function ProviderCard({ p }: { p: ProviderUsage }) {
  if (!p.available) {
    return (
      <div className="provider-card provider-card--unavailable">
        <h3>{p.name}</h3>
        <p className="provider-note">{p.note ?? "Usage data not available."}</p>
      </div>
    );
  }

  const isBalance = p.billing_type === "balance";

  // For balance providers the gauge shows % consumed (1 - remaining/limit)
  // For cost providers the gauge shows % of monthly limit spent
  const gaugeUsed = isBalance
    ? p.limit_usd
      ? Math.max(p.limit_usd - p.balance_usd, 0)
      : 0
    : Math.round(p.cost_usd * 100);   // cents

  const gaugeTotal = isBalance
    ? p.limit_usd ?? 0
    : Math.round((p.limit_usd ?? 0) * 100);  // cents

  const hasLimit = (p.limit_usd ?? 0) > 0;

  const topModels = Object.entries(p.by_model)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
    .filter(([, v]) => v > 0);

  return (
    <div className="provider-card">
      <h3>{p.name}</h3>

      {hasLimit ? (
        <GasGauge used={gaugeUsed} total={gaugeTotal} label={isBalance ? p.currency : "USD cents"} />
      ) : (
        <div className="provider-no-gauge">
          <span className="provider-cost-value">
            {isBalance
              ? `${p.currency} ${p.balance_usd.toFixed(4)}`
              : `$${p.cost_usd.toFixed(4)}`}
          </span>
          <span className="provider-cost-label">
            {isBalance ? "balance remaining" : "spent this period"}
          </span>
          <p className="provider-note provider-note--hint">
            Set a monthly limit in Settings to enable the gauge.
          </p>
        </div>
      )}

      {isBalance && hasLimit && (
        <p className="provider-sub">
          {p.currency} {p.balance_usd.toFixed(4)} of {p.currency} {p.limit_usd!.toFixed(2)} remaining
        </p>
      )}

      {!isBalance && hasLimit && (
        <p className="provider-sub">
          ${p.cost_usd.toFixed(4)} of ${p.limit_usd!.toFixed(2)} monthly limit
        </p>
      )}

      {topModels.length > 0 && (
        <div className="provider-models">
          <h4>Usage by Model</h4>
          {topModels.map(([model, cost]) => (
            <div key={model} className="provider-model-row">
              <span className="provider-model-name">{model}</span>
              <span className="provider-model-cost">${cost.toFixed(4)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ProviderGauges({ providers }: ProviderGaugesProps) {
  if (!providers || providers.length === 0) return null;

  return (
    <section className="providers-section">
      <h2>External AI Providers</h2>
      <div className="providers-grid">
        {providers.map((p) => (
          <ProviderCard key={p.provider_id} p={p} />
        ))}
      </div>
    </section>
  );
}
