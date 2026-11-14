// Small dependency-free SVG scatter chart (error bars, hollow points, optional line, shaded bands, legend).
interface Pt { x: number; y: number; err?: number; hollow?: boolean }
export interface Series { name: string; color: string; points: Pt[]; faint?: boolean; connect?: boolean; noLegend?: boolean }
export interface Band { x0: number; x1: number; label: string; color?: string }

export function ScatterChart({ series, line, xLabel, yLabel, invertY, hollowLabel, bands, xRange }: {
  series: Series[];
  line?: { name: string; color: string; xs: number[]; ys: number[] };
  xLabel: string; yLabel: string; invertY?: boolean; hollowLabel?: string; bands?: Band[]; xRange?: [number, number];
}) {
  const W = 320, H = 190, L = 44, R = 10, T = 14, B = 34;
  const all = series.flatMap((s) => s.points);
  const main = series.filter((s) => !s.faint).flatMap((s) => s.points);
  const forY = main.length ? main : all;
  const xs = [...all.map((p) => p.x), ...(line?.xs ?? [])];
  const ys = [...forY.flatMap((p) => [p.y - (p.err ?? 0), p.y + (p.err ?? 0)]), ...(line?.ys ?? [])].filter(Number.isFinite);
  if (!xs.length || !ys.length) return null;
  let [x0, x1] = xRange ?? [Math.min(...xs), Math.max(...xs)]; let [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const px = xRange ? 0 : (x1 - x0) * 0.05 || 0.5, py = (y1 - y0) * 0.1 || 0.5;
  x0 -= px; x1 += px; y0 -= py; y1 += py;
  const sx = (x: number) => L + ((x - x0) / (x1 - x0)) * (W - L - R);
  const syRaw = (y: number) => (invertY ? T + ((y - y0) / (y1 - y0)) * (H - T - B) : H - B - ((y - y0) / (y1 - y0)) * (H - T - B));
  const sy = (y: number) => Math.min(H - B, Math.max(T, syRaw(y))); // faint points outside the main range are clamped
  const ticks = (a: number, b: number, n = 4) => Array.from({ length: n + 1 }, (_, i) => a + ((b - a) * i) / n);
  const fmt = (v: number) => (Math.abs(v) >= 100 ? v.toFixed(0) : Math.abs(v) >= 10 ? v.toFixed(1) : v.toFixed(2));
  const anyHollow = all.some((p) => p.hollow);
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${yLabel} vs ${xLabel}`}>
        {bands?.filter((b) => b.x1 > x0 && b.x0 < x1).map((b) => (
          <g key={b.label}>
            <rect x={sx(Math.max(b.x0, x0))} y={T} width={Math.max(1, sx(Math.min(b.x1, x1)) - sx(Math.max(b.x0, x0)))} height={H - T - B} fill={b.color ?? "rgba(255,209,102,0.10)"} />
            <text x={(sx(Math.max(b.x0, x0)) + sx(Math.min(b.x1, x1))) / 2} y={T - 3} textAnchor="middle" className="band-label">{b.label}</text>
          </g>
        ))}
        {ticks(y0, y1).map((t, i) => (
          <g key={"y" + i}><line x1={L} x2={W - R} y1={syRaw(t)} y2={syRaw(t)} className="grid" /><text x={L - 5} y={syRaw(t) + 3} textAnchor="end" className="tick">{fmt(t)}</text></g>
        ))}
        {ticks(x0, x1).map((t, i) => <text key={"x" + i} x={sx(t)} y={H - B + 14} textAnchor="middle" className="tick">{fmt(t)}</text>)}
        <text x={(L + W - R) / 2} y={H - 4} textAnchor="middle" className="axis-label">{xLabel}</text>
        <text x={11} y={(T + H - B) / 2} textAnchor="middle" className="axis-label" transform={`rotate(-90 11 ${(T + H - B) / 2})`}>{yLabel}</text>
        {line && line.xs.length > 1 && (
          <polyline fill="none" stroke={line.color} strokeWidth={1.5} strokeDasharray="5 3" points={line.xs.map((x, i) => `${sx(x)},${sy(line.ys[i])}`).join(" ")} />
        )}
        {series.map((s) => (
          <g key={s.name} opacity={s.faint ? 0.35 : 1}>
            {s.connect && s.points.length > 1 && (
              <polyline fill="none" stroke={s.color} strokeWidth={1.8} points={[...s.points].sort((a, b) => a.x - b.x).map((p) => `${sx(p.x)},${sy(p.y)}`).join(" ")} />
            )}
            {s.points.map((p, i) => (
              <g key={i}>
                {p.err && !s.faint ? <line x1={sx(p.x)} x2={sx(p.x)} y1={sy(p.y - p.err)} y2={sy(p.y + p.err)} stroke={s.color} strokeOpacity={0.6} /> : null}
                <circle cx={sx(p.x)} cy={sy(p.y)} r={s.faint ? 2 : 3.4} fill={p.hollow ? "var(--bg)" : s.color} stroke={s.color} strokeWidth={s.faint ? 0.8 : 1.5} />
              </g>
            ))}
          </g>
        ))}
      </svg>
      <div className="legend">
        {series.filter((s) => s.points.length && !s.noLegend).map((s) => <span key={s.name} style={{ opacity: s.faint ? 0.6 : 1 }}><i style={{ background: s.color }} />{s.name}</span>)}
        {line && <span><i className="ln" style={{ borderColor: line.color }} />{line.name}</span>}
        {anyHollow && <span><i className="hollow" />{hollowLabel ?? "flagged"}</span>}
      </div>
    </div>
  );
}
