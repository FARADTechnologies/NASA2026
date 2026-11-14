import { navigate } from "../lib/router";
import { SearchBox } from "./SearchBox";

export function TopBar({ title, isMock }: { title?: string; isMock?: boolean }) {
  const go = (to: string) => (e: React.MouseEvent) => { e.preventDefault(); navigate(to); };
  return (
    <header className="topbar">
      <a href="/" className="logo" onClick={go("/")}>
        <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden><circle cx="10" cy="20" r="3" fill="#f4a259" opacity=".5" /><circle cx="16" cy="16" r="3" fill="#f4a259" opacity=".75" /><circle cx="22" cy="12" r="3.4" fill="#4cc9f0" /></svg>
        <span>SkyLapse</span>
      </a>
      {title && <span className="tb-title">{title}{isMock && <span className="badge b-mock">mock</span>}</span>}
      <div className="tb-search"><SearchBox compact /></div>
      <nav>
        <a href="/discover" onClick={go("/discover")}>Discover</a>
        <a href="/about" onClick={go("/about")}>About</a>
      </nav>
    </header>
  );
}
