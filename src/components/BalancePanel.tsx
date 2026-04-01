/**
 * Prepaid balance panel.
 * The GitHub Billing API does not expose prepaid credit balance in a standard
 * endpoint yet, so this panel shows a graceful "not available" state by default.
 * When the API becomes available, pass the balance (remaining) and limit props.
 */
interface BalancePanelProps {
  balance?: number;
  limit?: number;
}

export default function BalancePanel({ balance, limit }: BalancePanelProps) {
  if (balance === undefined || limit === undefined) {
    return (
      <div className="balance-panel balance-panel--unavailable">
        <h3>💳 Prepaid Balance</h3>
        <p className="unavailable-note">
          Prepaid credit balance is not currently available via the GitHub Billing API.
        </p>
      </div>
    );
  }

  // balance is the remaining amount; pct reflects how much is still available
  const pct = limit > 0 ? Math.min(balance / limit, 1) : 0;

  return (
    <div className="balance-panel">
      <h3>💳 Prepaid Balance</h3>
      <p>
        <strong>${balance.toFixed(2)}</strong> remaining of ${limit.toFixed(2)}
      </p>
      <div className="balance-bar-track">
        <div
          className="balance-bar-fill"
          style={{ width: `${pct * 100}%` }}
        />
      </div>
    </div>
  );
}
