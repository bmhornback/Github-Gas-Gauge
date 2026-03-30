import { useEffect, useRef } from "react";

interface GasGaugeProps {
  percentage: number;
  loading?: boolean;
}

/** Returns the color for a given usage percentage. */
function gaugeColor(pct: number): string {
  if (pct >= 90) return "#ef4444"; // red
  if (pct >= 75) return "#f59e0b"; // yellow/amber
  return "#22c55e"; // green
}

/** Returns a text label for the current zone. */
function zoneLabel(pct: number): string {
  if (pct >= 100) return "Over Limit";
  if (pct >= 90) return "Critical";
  if (pct >= 75) return "Warning";
  return "Normal";
}

/**
 * SVG arc-based semicircular gauge component.
 * The arc spans from the left (180°) to the right (0°) across the top half.
 */
function GasGauge({ percentage, loading = false }: GasGaugeProps) {
  const clampedPct = Math.min(Math.max(percentage, 0), 110);
  const prevPct = useRef(0);
  const animRef = useRef<number | null>(null);
  const arcRef = useRef<SVGPathElement | null>(null);
  const needleRef = useRef<SVGLineElement | null>(null);
  const pctTextRef = useRef<SVGTextElement | null>(null);

  const cx = 120;
  const cy = 120;
  const r = 90;

  /** Compute the (x, y) point on the arc for angle degrees (0 = right, 180 = left). */
  function polarToCartesian(angleDeg: number) {
    const rad = (angleDeg * Math.PI) / 180;
    return {
      x: cx + r * Math.cos(rad),
      y: cy + r * Math.sin(rad),
    };
  }

  /**
   * Build the SVG arc path for a given fill percentage.
   * The gauge runs from 180° (left) to 0° (right), so angle = 180 - (pct/100)*180.
   */
  function buildArcPath(fillPct: number): string {
    const startAngleDeg = 180;
    const endAngleDeg = 180 - (fillPct / 100) * 180;
    const start = polarToCartesian(startAngleDeg);
    const end = polarToCartesian(endAngleDeg);
    const largeArc = fillPct > 50 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  }

  useEffect(() => {
    const startPct = prevPct.current;
    const endPct = clampedPct;
    const duration = 600; // ms
    let startTime: number | null = null;

    function animate(timestamp: number) {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = startPct + (endPct - startPct) * eased;

      if (arcRef.current) {
        arcRef.current.setAttribute("d", buildArcPath(current));
        arcRef.current.setAttribute("stroke", gaugeColor(current));
      }

      // Needle angle: 180° at 0%, 0° at 100%
      if (needleRef.current) {
        const needleAngleDeg = 180 - (current / 100) * 180;
        const needleRad = (needleAngleDeg * Math.PI) / 180;
        const nx = cx + (r - 10) * Math.cos(needleRad);
        const ny = cy + (r - 10) * Math.sin(needleRad);
        needleRef.current.setAttribute("x2", String(nx));
        needleRef.current.setAttribute("y2", String(ny));
        needleRef.current.setAttribute("stroke", gaugeColor(current));
      }

      if (pctTextRef.current) {
        pctTextRef.current.textContent = `${Math.round(current)}%`;
      }

      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate);
      } else {
        prevPct.current = endPct;
      }
    }

    if (animRef.current) cancelAnimationFrame(animRef.current);
    animRef.current = requestAnimationFrame(animate);

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clampedPct]);

  // Track arc: background full semicircle
  const trackStart = polarToCartesian(180);
  const trackEnd = polarToCartesian(0);

  return (
    <div className="gas-gauge-wrapper">
      {loading && <div className="gauge-loading-overlay">Updating…</div>}
      <svg
        width="240"
        height="140"
        viewBox="0 0 240 140"
        className="gas-gauge-svg"
        aria-label={`Usage: ${Math.round(clampedPct)}%`}
      >
        {/* Background track */}
        <path
          d={`M ${trackStart.x} ${trackStart.y} A ${r} ${r} 0 0 1 ${trackEnd.x} ${trackEnd.y}`}
          fill="none"
          stroke="#374151"
          strokeWidth="16"
          strokeLinecap="round"
        />
        {/* Colored fill arc */}
        <path
          ref={arcRef}
          d={buildArcPath(0)}
          fill="none"
          stroke={gaugeColor(0)}
          strokeWidth="16"
          strokeLinecap="round"
        />
        {/* Needle */}
        <line
          ref={needleRef}
          x1={cx}
          y1={cy}
          x2={cx - (r - 10)}
          y2={cy}
          stroke={gaugeColor(0)}
          strokeWidth="3"
          strokeLinecap="round"
        />
        {/* Center dot */}
        <circle cx={cx} cy={cy} r="6" fill="#9ca3af" />
        {/* Percentage label */}
        <text
          ref={pctTextRef}
          x={cx}
          y={cy + 32}
          textAnchor="middle"
          fontSize="24"
          fontWeight="bold"
          fill="#f9fafb"
        >
          0%
        </text>
        {/* Zone label */}
        <text
          x={cx}
          y={cy + 52}
          textAnchor="middle"
          fontSize="11"
          fill="#9ca3af"
        >
          {zoneLabel(clampedPct)}
        </text>
        {/* Tick labels */}
        <text x="18" y="128" fontSize="10" fill="#6b7280">
          0%
        </text>
        <text x="108" y="24" fontSize="10" fill="#6b7280">
          50%
        </text>
        <text x="204" y="128" fontSize="10" fill="#6b7280">
          100%
        </text>
      </svg>
    </div>
  );
}

export default GasGauge;
