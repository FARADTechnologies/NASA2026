import { useLocation } from "./lib/router";
import { Home } from "./pages/Home";
import { Viewer } from "./pages/Viewer";
import { TopBar } from "./components/TopBar";

export default function App() {
  const { path, search } = useLocation();
  if (path.startsWith("/view")) return <Viewer key={viewKey(search)} search={search} />;
  if (path.startsWith("/discover")) return <Placeholder title="Discover" text="Auto-detected movers and candidates across all fields — coming in the next build." />;
  if (path.startsWith("/about")) return <Placeholder title="About SkyLapse" text="Method, validation and data credits — coming in the next build." />;
  return <Home />;
}

function viewKey(search: string) {
  const q = new URLSearchParams(search);
  return `${q.get("field") ?? ""}|${q.get("ra") ?? ""}|${q.get("dec") ?? ""}`;
}

function Placeholder({ title, text }: { title: string; text: string }) {
  return <div className="page"><TopBar /><div className="empty-state"><h2>{title}</h2><p>{text}</p></div></div>;
}
