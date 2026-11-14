import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

// Dev-only fake live API (DATA_CONTRACT §7) for testing the live-mode UI without the backend.
// Enable with SKYLAPSE_FAKE_API=1 npm run dev. It replays the _mock field: queued → wise_ready → spherex_partial → done.
function fakeLiveApi(): Plugin {
  const src = path.resolve(__dirname, "public/bundle/_mock/mock_mover");
  let t0 = 0;
  const stage = () => {
    const s = (Date.now() - t0) / 1000;
    if (s < 3) return { state: "queued", progress: s / 15 };
    if (s < 8) return { state: "wise_ready", progress: s / 15 };
    if (s < 15) return { state: "spherex_partial", progress: s / 15 };
    return { state: "done", progress: 1 };
  };
  return {
    name: "skylapse-fake-live-api",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || "";
        if (req.method === "POST" && url.startsWith("/api/fields")) {
          t0 = Date.now();
          res.setHeader("content-type", "application/json");
          return res.end(JSON.stringify({ field_id: "live_mock", status_url: "/api/fields/live_mock/status" }));
        }
        if (url.startsWith("/api/fields/live_mock/status")) {
          res.setHeader("content-type", "application/json");
          return res.end(JSON.stringify({ ...stage(), manifest_url: "/api/fields/live_mock/manifest.json" }));
        }
        if (url.startsWith("/api/fields/live_mock/manifest.json")) {
          const m = JSON.parse(fs.readFileSync(path.join(src, "manifest.json"), "utf8"));
          const st = stage().state;
          const keep = (id: string) => id.startsWith("wise") || st === "done" || (st === "spherex_partial" && /_t00$/.test(id));
          m.field_id = "live_mock"; m.title = "Live field (fake API)";
          m.frames = m.frames.filter((f: { id: string }) => keep(f.id));
          m.sequences = m.sequences.map((s: { frames: string[] }) => ({ ...s, frames: s.frames.filter(keep) })).filter((s: { frames: string[] }) => s.frames.length);
          if (st !== "done") m.rgb_composites = [];
          res.setHeader("content-type", "application/json");
          return res.end(JSON.stringify(m));
        }
        const fm = /^\/api\/fields\/live_mock\/(.+)$/.exec(url.split("?")[0]);
        if (fm) {
          const f = path.join(src, fm[1]);
          if (f.startsWith(src) && fs.existsSync(f)) return res.end(fs.readFileSync(f));
          res.statusCode = 404; return res.end();
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), ...(process.env.SKYLAPSE_FAKE_API ? [fakeLiveApi()] : [])],
  server: { port: 5173 },
});
