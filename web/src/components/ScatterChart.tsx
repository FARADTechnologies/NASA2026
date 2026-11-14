// Small dependency-free SVG scatter chart (error bars, hollow points, optional line, legend).
interface Pt { x: number; y: number; err?: number; hollow?: boolean }
export function ScatterChart({ series, line, xLabel, yLabel, invertY, hollowLabel }: {
  series: { name: string; color: string; points: Pt[] }[];
  line?: { name: string; color: string; xs: number[]; ys: number[] };
  xLabel: string; yLabel: string; invertY?: boolean; hollowLabel?: string;
}) {
  const W = 320, H = 190, L = 44, R = 10, T = 10, B = 34;
  const all = series.flatMap((s) => s.points);
  const xs = [...all.map((p) => p.x), ...(line?.xs ?? [])];
  const ys = [...all.flatMap((p) => [p.y - (p.err ?? 0), p.y + (p.err ?? 0)]), ...(line?.ys ?? [])];
  if (!xs.length) return null;
  let [x0, x1] = [Math.min(...xs), Math.max(...xs)]; let [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const px = (x1 - x0) * 0.05 || 0.5, py = (y1 - y0) * 0.1 || 0.5;
  x0 -= px; x1 += px; y0 -= py; y1 += py;
  const sx = (x: number) => L + ((x - x0) / (x1 - x0)) * (W - L - R);
  const sy = (y: number) => (invertY ? T + ((y - y0) / (y1 - y0)) * (H - T - B) : H - B - ((y - y0) / (y1 - y0)) * (H - T - B));
  const ticks = (a: number, b: number, n = 4) => Array.from({ length: n + 1 }, (_, i) => a + ((b - a) * i) / n);
  const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2));
  const anyHollow = all.some((p) => p.hollow);
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${yLabel} vs ${xLabel}`}>
        {ticks(y0, y1).map((t, i) => (
          <g key={"y" + i}><line x1={L} x2={W - R} y1={sy(t)} y2={sy(t)} className="grid" /><text x={L - 5} y={sy(t) + 3} textAnchor="end" className="tick">{fmt(t)}</text></g>
        ))}
        {ticks(x0, x1).map((t, i) => <text key={"x" + i} x={sx(t)} y={H - B + 14} textAnchor="middle" className="tick">{fmt(t)}</text>)}
        <text x={(L + W - R) / 2} y={H - 4} textAnchor="middle" className="axis-label">{xLabel}</text>
        <text x={11} y={(T + H - B) / 2} textAnchor="middle" className="axis-label" transform={`rotate(-90 11 ${(T + H - B) / 2})`}>{yLabel}</text>
        {line && line.xs.length > 1 && (
          <polyline fill="none" stroke={line.color} strokeWidth={1.5} strokeDasharray="5 3" points={line.xs.map((x, i) => `${sx(x)},${sy(line.ys[i])}`).join(" ")} />
        )}
        {series.map((s) => s.points.map((p, i) => (
          <g key={s.name + i}>
            {p.err ? <line x1={sx(p.x)} x2={sx(p.x)} y1={sy(p.y - p.err)} y2={sy(p.y + p.err)} stroke={s.color} strokeOpacity={0.6} /> : null}
            <circle cx={sx(p.x)} cy={sy(p.y)} r={3.4} fill={p.hollow ? "var(--bg)" : s.color} stroke={s.color} strokeWidth={1.5} />
          </g>
        )))}
      </svg>
      <div className="legend">
        {series.filter((s) => s.points.length).map((s) => <span key={s.name}><i style={{ background: s.color }} />{s.name}</span>)}
        {line && <span><i className="ln" style={{ borderColor: line.color }} />{line.name}</span>}
        {anyHollow && <span><i className="hollow" />{hollowLabel ?? "flagged"}</span>}
      </div>
    </div>
  );
}
