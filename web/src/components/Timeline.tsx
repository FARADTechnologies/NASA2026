import type { Frame } from "../lib/bundle";
import { mjdToYear } from "../lib/bundle";

const Y0 = 2009.8, Y1 = 2026.9;
const COLORS: Record<string, string> = { WISE: "var(--wise)", SPHEREx: "var(--spherex)" };

export function Timeline(props: {
  frames: Frame[]; index: number; loaded: Set<string>; onSelect: (i: number) => void;
  range?: [number, number] | null; refId?: string;
}) {
  const { frames, index, loaded } = props;
  const pos = (y: number) => ((y - Y0) / (Y1 - Y0)) * 100;
  const years: number[] = [];
  for (let y = 2010; y <= 2026; y += 2) years.push(y);
  return (
    <div className="timeline" role="slider" aria-valuemin={0} aria-valuemax={frames.length - 1} aria-valuenow={index}>
      <div className="tl-track">
        <div className="tl-gap" style={{ left: pos(2011.15) + "%", width: pos(2013.9) - pos(2011.15) + "%" }}>
          <span>WISE hibernation</span>
        </div>
        {props.range && frames[props.range[0]] && frames[props.range[1]] && (
          <div className="tl-range" style={{
            left: pos(mjdToYear(frames[props.range[0]].mjd_mid)) + "%",
            width: Math.max(0.6, pos(mjdToYear(frames[props.range[1]].mjd_mid)) - pos(mjdToYear(frames[props.range[0]].mjd_mid))) + "%",
          }} />
        )}
        {frames.map((f, i) => {
          const y = mjdToYear(f.mjd_mid);
          const cur = i === index;
          return (
            <button
              key={f.id}
              className={"tl-tick" + (cur ? " cur" : "") + (loaded.has(f.id) ? "" : " pending") + (props.refId === f.id ? " ref" : "")}
              style={{ left: pos(y) + "%", background: COLORS[f.instrument] ?? "#888" }}
              title={`${f.date} · ${f.instrument} ${f.band}`}
              onClick={() => props.onSelect(i)}
            />
          );
        })}
      </div>
      <div className="tl-axis">
        {years.map((y) => <span key={y} style={{ left: pos(y) + "%" }}>{y}</span>)}
      </div>
      <div className="tl-legend">
        <span><i style={{ background: "var(--wise)" }} />WISE / NEOWISE</span>
        <span><i style={{ background: "var(--spherex)" }} />SPHEREx</span>
      </div>
    </div>
  );
}
