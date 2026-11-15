import { Moon, Sun } from "lucide-react";
import { navigate } from "../lib/router";
import { useTheme } from "../lib/theme";
import { SearchBox } from "./SearchBox";

export function TopBar({ title, isMock }: { title?: string; isMock?: boolean }) {
  const [theme, toggle] = useTheme();
  const go = (to: string) => (e: React.MouseEvent) => { e.preventDefault(); navigate(to); };
  const here = (p: string) => (location.pathname.startsWith(p) ? "on" : "");
  return (
    <header className="topbar">
      <a href="/" className="logo" onClick={go("/")} aria-label="SkyLapse home">
        <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
          <circle cx="8" cy="22" r="3" fill="var(--wise)" opacity=".45" /><circle cx="16" cy="16" r="3.2" fill="var(--wise)" opacity=".8" /><circle cx="24" cy="10" r="3.6" fill="var(--spherex)" />
        </svg>
        <span>SkyLapse</span>
      </a>
      {title && <span className="tb-title">{title}{isMock && <span className="badge b-mock">mock</span>}</span>}
      {/* Mount point for the "Ask SkyLapse" command bar (components/AskSkyLapse.tsx, built by the orchestrator):
          render <AskSkyLapse /> inside this element. Empty → takes no space. */}
      <div className="tb-ask" id="ask-skylapse-slot" data-slot="ask-skylapse" />
      <div className="tb-search"><SearchBox compact /></div>
      <nav>
        <a href="/discover" className={here("/discover")} onClick={go("/discover")}>Discover</a>
        <a href="/about" className={here("/about")} onClick={go("/about")}>About</a>
      </nav>
      <button className="icon-btn" onClick={toggle} title={theme === "light" ? "Switch to dark theme" : "Switch to light theme"} aria-label="Toggle theme">
        {theme === "light" ? <Moon size={17} strokeWidth={1.75} /> : <Sun size={17} strokeWidth={1.75} />}
      </button>
    </header>
  );
}
