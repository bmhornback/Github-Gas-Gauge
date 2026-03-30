interface OveragePanelProps {
  overageCount: number;
  unit: string;
  /** Cost per overage unit in USD (e.g. 0.008 per Actions minute) */
  costPerUnit: number;
}

export default function OveragePanel({ overageCount, unit, costPerUnit }: OveragePanelProps) {
  if (overageCount <= 0) return null;

  const estimatedCost = overageCount * costPerUnit;

  return (
    <div className="overage-panel">
      <h3>⚠️ Overage</h3>
      <p>
        <strong>{overageCount.toLocaleString()}</strong> {unit} beyond your included quota
      </p>
      {costPerUnit > 0 && (
        <p className="overage-cost">
          Estimated cost:{" "}
          <strong>${estimatedCost.toFixed(2)}</strong>
        </p>
      )}
    </div>
  );
}
