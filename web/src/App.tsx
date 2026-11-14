import { useLocation } from "./lib/router";
import { Home } from "./pages/Home";
import { Viewer } from "./pages/Viewer";
import { TopBar } from "./components/TopBar";
import { Discover } from "./pages/Discover";
import { About } from "./pages/About";

export default function App() {
  const { path, search } = useLocation();
  if (path.startsWith("/view")) return <Viewer key={viewKey(search)} search={search} />;
  if (path.startsWith("/discover")) return <Discover />;
  if (path.startsWith("/about")) return <About />;
  if (path === "/" || path === "/index.html") return <Home />;
  return <Placeholder title="Page not found" text="This page does not exist. Go back to the home page to pick a target." />;
}

function viewKey(search: string) {
  const q = new URLSearchParams(search);
  return `${q.get("field") ?? ""}|${q.get("ra") ?? ""}|${q.get("dec") ?? ""}`;
}

function Placeholder({ title, text }: { title: string; text: string }) {
  return <div className="page"><TopBar /><div className="empty-state"><h2>{title}</h2><p>{text}</p></div></div>;
}
