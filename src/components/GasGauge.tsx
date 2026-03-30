interface GasGaugeProps {
  used: number;
  total: number;
  label: string;
}

const RADIUS = 80;
const STROKE = 14;
const CENTER = 100;
// Arc spans 180° (semicircle) from 180° to 0° (left to right)
const CIRCUMFERENCE = Math.PI * RADIUS; // half circumference for semicircle

function arcColor(pct: number): string {
  if (pct >= 0.9) return "#ef4444"; // red
  if (pct >= 0.75) return "#f59e0b"; // yellow
  return "#22c55e"; // green
}

export default function GasGauge({ used, total, label }: GasGaugeProps) {
  const pct = total > 0 ? Math.min(used / total, 1) : 0;
  const color = arcColor(pct);
  // Dash offset: full arc = 0 offset, empty = CIRCUMFERENCE offset
  const dashOffset = CIRCUMFERENCE * (1 - pct);

  return (
    <div className="gas-gauge">
      <svg
        viewBox="0 0 200 110"
        width="220"
        height="120"
        role="img"
        aria-label={`${Math.round(pct * 100)}% used`}
      >
        {/* Background track */}
        <path
          d={`M ${CENTER - RADIUS} ${CENTER} A ${RADIUS} ${RADIUS} 0 0 1 ${CENTER + RADIUS} ${CENTER}`}
          fill="none"
          stroke="#374151"
          strokeWidth={STROKE}
          strokeLinecap="round"
        />
        {/* Filled arc */}
        <path
          d={`M ${CENTER - RADIUS} ${CENTER} A ${RADIUS} ${RADIUS} 0 0 1 ${CENTER + RADIUS} ${CENTER}`}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 0.6s ease, stroke 0.4s ease" }}
        />
        {/* Percentage label */}
        <text x={CENTER} y={CENTER - 10} textAnchor="middle" className="gauge-pct" fill={color}>
          {Math.round(pct * 100)}%
        </text>
      </svg>
      <p className="gauge-label">
        {used.toLocaleString()} used of {total.toLocaleString()} {label}
      </p>
    </div>
  );
}
