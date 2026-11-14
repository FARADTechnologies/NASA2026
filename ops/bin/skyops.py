#!/usr/bin/env python3
"""skyops — autonomous issue-driven agent ops for SkyLapse (GitHub Issues = task bus).

Standard library only. Needs the GitHub CLI (`gh`) logged in for issue commands.

Every task issue starts with a header block that machines read:

    ```skylapse
    agent: frontend
    priority: P0
    start: after #12 #14          (now | after #N #M | at 2026-11-14T13:30+04:00)
    autonomy: auto                (auto | human  → human = needs the label "approved" first)
    milestone: M2
    ```

Agent commands (the AI runs these):
  brief                          recovery brief (role, journal, state, commits, my queue)
  next [--wait SEC] [--json]     best eligible task for me (waits up to SEC, polling); prints NO_TASK if none
  claim N                        mark task N in-progress (comment + label)
  submit N (--file F|--text T) [--pr URL]   report; task → status:review (questions are answered and closed)
  block N --reason T             mark blocked with a reason
  ask --to AGENT --title T (--file F|--text T)   question/request to another agent
  escalate --title T --body-file F                escalation to the captain
Orchestrator commands:
  setup-labels · task --agent A --title T --body-file F [--prio P0] [--start now|"after #3 #4"|"at ISO"] [--autonomy auto|human]
  accept N [--merge-pr]          accept a reviewed task (merge its PR if given) and close it
  changes N (--file F|--text T)  request changes → status:changes-requested
Human commands:
  inbox [--agent A] · show N [--copy] · approve N · auto on|off · pause · resume · status · watch [--agent A]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
AGENTS = ["orchestrator", "pipeline", "science", "frontend", "pitch"]
LABELS = {
    **{f"agent:{a}": "1d76db" for a in AGENTS}, "agent:captain": "000000",
    "type:task": "0e8a16", "type:question": "fbca04", "type:bug": "d93f0b", "type:report": "c5def5",
    "type:escalation": "b60205", "type:checkpoint": "5319e7",
    "prio:P0": "b60205", "prio:P1": "d93f0b", "prio:P2": "fbca04",
    "status:in-progress": "0052cc", "status:review": "5319e7", "status:changes-requested": "e99695",
    "status:blocked": "000000", "needs-human": "f9d0c4", "approved": "0e8a16",
}
BAKU = dt.timezone(dt.timedelta(hours=4))
HEADER_RE = re.compile(r"```skylapse\s*\n(.*?)```", re.S)
TITLE_RE = re.compile(r"^\[(\w+)\]\[(P\d)\]\[(auto|human)\]", re.I)


# ----------------------------------------------------------------------------- basics
_GH = None


def find_gh():
    """gh on PATH, else $SKYLAPSE_GH, else the usual install folders (Windows apps started before the install have an old PATH)."""
    global _GH
    if _GH:
        return _GH
    import glob
    home = Path.home()
    cands = [shutil.which("gh"), os.environ.get("SKYLAPSE_GH"),
             r"C:\Program Files\GitHub CLI\gh.exe",
             str(Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")) / "Microsoft/WinGet/Links/gh.exe"),
             *sorted(glob.glob(str(home / "tools/gh/*/bin/gh.exe")), reverse=True),
             "/opt/homebrew/bin/gh", "/usr/local/bin/gh", "/usr/bin/gh"]
    for c in cands:
        if c and Path(c).exists():
            _GH = c
            return c
    return None


def run(cmd, timeout=20, stdin=None):
    if cmd and cmd[0] == "gh" and find_gh():
        cmd = [find_gh()] + list(cmd[1:])
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", input=stdin)
        return p.returncode, (p.stdout or "") + (p.stderr if p.returncode else "")
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout: {' '.join(cmd)}"


def have_gh():
    return find_gh() is not None or bool(os.environ.get("SKYOPS_FAKE_ISSUES"))


def need_gh():
    if not have_gh():
        sys.exit("gh (GitHub CLI) not found on PATH, in $SKYLAPSE_GH, or in the usual install folders. "
                 "If it was just installed, restart the Claude app; else install it and run `gh auth login`.")


def me():
    f = ROOT / ".skylapse-role"
    if f.exists():
        raw = f.read_bytes()
        # tolerate Windows PowerShell `echo x > file` (UTF-16 + BOM) and UTF-8 BOM
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            txt = raw.decode("utf-16", "ignore")
        else:
            txt = raw.decode("utf-8-sig", "ignore")
        r = txt.replace("\x00", "").strip().lower()
        return r if r in AGENTS else None
    return None


def team():
    try:
        return json.loads((ROOT / "ops" / "team.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def gh_user_for(agent):
    t = team()
    u = t.get("captain") if agent == "captain" else (t.get("roles") or {}).get(agent)
    return u if u and not u.startswith("<") else None


def now():
    return dt.datetime.now(BAKU)


def stamp():
    return now().strftime("%a %H:%M")


def flag(name):
    return ROOT / name


def auto_on():
    return flag(".skylapse-auto").exists() and not flag(".skylapse-pause").exists()


# ----------------------------------------------------------------------------- issues
def fetch_issues(label=None, state="open", limit=60):
    fake = os.environ.get("SKYOPS_FAKE_ISSUES")
    if fake:  # offline testing
        items = json.loads(Path(fake).read_text(encoding="utf-8"))
        items = [i for i in items if i.get("state", "OPEN").lower() == state or state == "all"]
        return [i for i in items if not label or label in [l["name"] for l in i.get("labels", [])]]
    cmd = ["gh", "issue", "list", "--state", state, "--limit", str(limit),
           "--json", "number,title,labels,body,state,createdAt,updatedAt"]
    if label:
        cmd += ["--label", label]
    code, out = run(cmd, timeout=25)
    if code != 0:
        raise RuntimeError(out.strip())
    return json.loads(out)


_state_cache: dict[int, str] = {}


def live_state(n):
    """Uncached issue state straight from GitHub (OPEN/CLOSED); 'OPEN' if it cannot be read."""
    code, out = run(["gh", "issue", "view", str(n), "--json", "state"], timeout=15)
    try:
        return json.loads(out).get("state", "OPEN").upper() if code == 0 else "OPEN"
    except Exception:
        return "OPEN"


def issue_state(n):
    if n in _state_cache:
        return _state_cache[n]
    fake = os.environ.get("SKYOPS_FAKE_ISSUES")
    if fake:
        for i in json.loads(Path(fake).read_text(encoding="utf-8")):
            if i["number"] == n:
                _state_cache[n] = i.get("state", "OPEN").upper()
                return _state_cache[n]
        return "MISSING"
    code, out = run(["gh", "issue", "view", str(n), "--json", "state"], timeout=15)
    st = json.loads(out).get("state", "MISSING") if code == 0 else "MISSING"
    _state_cache[n] = st
    return st


def labels_of(it):
    return [l["name"] for l in it.get("labels", [])]


def parse_header(it):
    h = {"agent": None, "priority": None, "start": "now", "autonomy": "auto", "milestone": ""}
    m = HEADER_RE.search(it.get("body") or "")
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                h[k.strip().lower()] = v.strip()
    t = TITLE_RE.match(it.get("title", ""))
    labs = labels_of(it)
    if not h["agent"]:
        h["agent"] = (t.group(1).lower() if t else None) or next((l[6:] for l in labs if l.startswith("agent:")), None)
    if not h["priority"]:
        h["priority"] = (t.group(2).upper() if t else None) or next((l[5:] for l in labs if l.startswith("prio:")), "P2")
    if "needs-human" in labs or (t and t.group(3).lower() == "human"):
        h["autonomy"] = "human"
    return h


def eligibility(it, agent):
    """Return (eligible: bool, reason: str)."""
    labs = labels_of(it)
    h = parse_header(it)
    if h["agent"] != agent and f"agent:{agent}" not in labs:
        return False, "not mine"
    if "status:review" in labs:
        return False, "waiting for orchestrator review"
    if "status:blocked" in labs:
        return False, "blocked"
    if "type:escalation" in labs and agent != "orchestrator":
        return False, "escalation (humans)"
    if h["autonomy"] == "human" and "approved" not in labs:
        return False, "needs a human to add the label 'approved'"
    start = (h["start"] or "now").strip()
    if start.lower().startswith("after"):
        deps = [int(x) for x in re.findall(r"#(\d+)", start)]
        open_deps = [d for d in deps if issue_state(d) != "CLOSED"]
        if open_deps:
            return False, "waiting for " + ", ".join(f"#{d}" for d in open_deps)
    elif start.lower().startswith("at"):
        try:
            when = dt.datetime.fromisoformat(start[2:].strip())
            if when.tzinfo is None:
                when = when.replace(tzinfo=BAKU)
            if now() < when:
                return False, "scheduled for " + when.astimezone(BAKU).strftime("%a %H:%M")
        except ValueError:
            return False, f"bad start time '{start}'"
    return True, "ready"


def rank(it):
    labs = labels_of(it)
    h = parse_header(it)
    order = 9
    if "status:in-progress" in labs:
        order = 0
    elif "status:changes-requested" in labs:
        order = 1
    elif "type:bug" in labs:
        order = 2
    elif "type:question" in labs:
        order = 3
    return (order, {"P0": 0, "P1": 1, "P2": 2}.get(h["priority"], 3), it["number"])


def my_queue(agent):
    items = fetch_issues(f"agent:{agent}")
    out = []
    for it in items:
        ok, why = eligibility(it, agent)
        out.append((it, ok, why))
    out.sort(key=lambda x: rank(x[0]))
    return out


def review_queue():
    return sorted(fetch_issues("status:review"), key=lambda it: it["number"])


def fmt(it, why=None):
    h = parse_header(it)
    title = it["title"]
    prefix = "" if TITLE_RE.match(title) else f"[{h['agent']}][{h['priority']}][{h['autonomy']}] "
    s = f"#{it['number']} {prefix}{title}"
    return s + (f"   — {why}" if why else "")


# ----------------------------------------------------------------------------- brief
def read_head(path, n):
    if not path.exists():
        return f"(missing: {path.relative_to(ROOT)})"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[:n]) + (f"\n… (+{len(lines) - n} lines)" if len(lines) > n else "")


def read_tail(path, n):
    if not path.exists():
        return f"(missing: {path.relative_to(ROOT)})"
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])


def build_brief(source="manual"):
    a = me()
    parts = [f"===== SKYLAPSE RECOVERY BRIEF (trigger: {source}, {stamp()} Baku) =====",
             f"You are agent: {a or 'UNKNOWN — ask the human which agent you are and write it to .skylapse-role'}",
             f"AUTONOMOUS MODE: {'ON' if auto_on() else 'OFF'}"
             + ("  (paused)" if flag('.skylapse-pause').exists() else ""),
             "CLAUDE.md is authoritative. Continue from 'Next step' in your journal; keep the journal current."]
    if a:
        parts += ["", f"----- YOUR JOURNAL ops/memory/sessions/{a}.md -----",
                  read_head(ROOT / "ops" / "memory" / "sessions" / f"{a}.md", 140)]
    parts += ["", "----- PROJECT STATE (ops/memory/PROJECT_STATE.md) -----",
              read_head(ROOT / "ops" / "memory" / "PROJECT_STATE.md", 70),
              "", "----- RECENT KNOW-HOW -----", read_tail(ROOT / "ops" / "memory" / "KNOWHOW.md", 25)]
    code, log = run(["git", "log", "--oneline", "-12", "--all", "--decorate"], timeout=8)
    parts += ["", "----- RECENT COMMITS -----", log.strip() if code == 0 else "(git unavailable)"]
    code, st = run(["git", "status", "--short", "--branch"], timeout=8)
    if code == 0:
        lines = st.strip().splitlines()
        parts += ["", "----- GIT STATUS -----", "\n".join(lines[:25]) + ("\n…" if len(lines) > 25 else "")]
    if a and have_gh():
        try:
            q = my_queue(a)
            parts += ["", "----- MY QUEUE -----"] + ([fmt(it, why) for it, ok, why in q] or ["(empty)"])
            if a == "orchestrator":
                parts += ["----- WAITING FOR MY REVIEW -----"] + ([fmt(i) for i in review_queue()] or ["(none)"])
        except Exception as e:
            parts += ["", f"(could not read GitHub issues: {e})"]
    if auto_on():
        parts += ["", "AUTONOMOUS MODE IS ON → if you are not in the middle of a task, run:",
                  "  python ops/bin/skyops.py next --wait 540     (use a Bash timeout of 600000 ms)"]
    parts += ["===== END OF BRIEF ====="]
    return "\n".join(parts)


# ----------------------------------------------------------------------------- commands
def cmd_next(a):
    need_gh()
    agent = a.agent or me()
    if not agent:
        sys.exit("Unknown agent: create .skylapse-role or pass --agent")
    deadline = time.time() + max(0, min(a.wait, 560))
    while True:
        if flag(".skylapse-pause").exists():
            print("PAUSED — a human paused this agent (.skylapse-pause exists). Stop and wait for the human.")
            return
        _state_cache.clear()
        try:
            q = my_queue(agent)
            reviews = review_queue() if agent == "orchestrator" else []
        except Exception as e:
            print(f"ERROR reading issues: {e}")
            return
        ready = [it for it, ok, why in q if ok]
        if agent == "orchestrator" and reviews:
            it = reviews[0]
            print(f"ACTION: REVIEW #{it['number']} — {it['title']}\n"
                  f"Read the issue and its latest REPORT, check the PR/branch, run the acceptance test, then\n"
                  f"`skyops.py accept {it['number']} [--merge-pr URL]` or `skyops.py changes {it['number']} --text ...`.\n")
            print(it.get("body") or "")
            return
        if ready and not os.environ.get("SKYOPS_FAKE_ISSUES"):
            # guard against the accept race: re-check that the chosen issue is still OPEN right now
            ready = [it for it in ready if live_state(it["number"]) == "OPEN"]
        if ready:
            it = ready[0]
            action = "RESUME" if "status:in-progress" in labels_of(it) else "START"
            if a.json:
                print(json.dumps({"action": action, "number": it["number"], "title": it["title"],
                                  "header": parse_header(it), "body": it.get("body")}, ensure_ascii=False))
            else:
                print(f"ACTION: {action} TASK #{it['number']} — {it['title']}")
                print("Steps: claim it (if START) → do it → test → commit/push/PR → submit report → update journal → next.\n")
                print(it.get("body") or "")
                code, out = run(["gh", "issue", "view", str(it["number"]), "--json", "comments"], timeout=15) \
                    if not os.environ.get("SKYOPS_FAKE_ISSUES") else (1, "")
                if code != 0:
                    print(f"\n(could not load comments: {out.strip()[:200]} — run `skyops.py show {it['number']}`)")
                else:
                    comments = json.loads(out).get("comments", [])[-4:]
                    for c in comments:
                        print(f"\n--- comment by {c.get('author', {}).get('login', '?')} ---\n{c.get('body', '')}")
            return
        if time.time() >= deadline:
            pending = [fmt(it, why) for it, ok, why in q][:8]
            print("NO_TASK" + (f" (waited {a.wait}s)" if a.wait else ""))
            print("Pending:\n  " + ("\n  ".join(pending) if pending else "(queue empty)"))
            print("If autonomous mode is on, run `next --wait 540` again (Bash timeout 600000 ms).")
            return
        time.sleep(max(1.0, min(45.0, deadline - time.time())))


def comment(n, text):
    if os.environ.get("SKYOPS_FAKE_ISSUES"):
        print(f"[fake] comment on #{n}:\n{text}")
        return 0
    code, out = run(["gh", "issue", "comment", str(n), "--body-file", "-"], timeout=30, stdin=text)
    if code != 0:
        print(f"WARNING: comment on #{n} failed: {out.strip()}", file=sys.stderr)
    return code


def edit_labels(n, add=(), remove=()):
    if os.environ.get("SKYOPS_FAKE_ISSUES"):
        print(f"[fake] labels #{n}: +{list(add)} -{list(remove)}")
        return
    cmd = ["gh", "issue", "edit", str(n)]
    for l in add:
        cmd += ["--add-label", l]
    for l in remove:
        cmd += ["--remove-label", l]
    code, out = run(cmd, timeout=30)
    if code != 0:
        print(out)


def body_from(a):
    if getattr(a, "file", None):
        return Path(a.file).read_text(encoding="utf-8")
    return getattr(a, "text", "") or ""


def cmd_claim(a):
    need_gh()
    agent = me() or "?"
    comment(a.number, f"🤖 **CLAIMED** by agent `{agent}` on `{socket.gethostname()}` at {stamp()} (Baku).")
    edit_labels(a.number, add=["status:in-progress"], remove=["status:changes-requested"])
    print(f"claimed #{a.number}")


def cmd_submit(a):
    need_gh()
    agent = me() or "?"
    text = f"🤖 **REPORT** from agent `{agent}` at {stamp()} (Baku)\n\n{body_from(a)}"
    if a.pr:
        text += f"\n\nPR: {a.pr}"
    comment(a.number, text)
    labs = []
    if not os.environ.get("SKYOPS_FAKE_ISSUES"):
        code, out = run(["gh", "issue", "view", str(a.number), "--json", "labels"], timeout=15)
        labs = [l["name"] for l in json.loads(out).get("labels", [])] if code == 0 else []
    if "type:question" in labs:
        edit_labels(a.number, remove=["status:in-progress"])
        run(["gh", "issue", "close", str(a.number)], timeout=20)
        print(f"answered and closed question #{a.number}")
    else:
        edit_labels(a.number, add=["status:review"], remove=["status:in-progress", "status:changes-requested"])
        print(f"#{a.number} → status:review (the orchestrator will accept or request changes)")


def cmd_block(a):
    need_gh()
    comment(a.number, f"⛔ **BLOCKED** ({me()} at {stamp()}): {a.reason}")
    edit_labels(a.number, add=["status:blocked"], remove=["status:in-progress"])


def create_issue(title, body, labels, assignee=None):
    if os.environ.get("SKYOPS_FAKE_ISSUES"):
        print(f"[fake] create issue '{title}' labels={labels} assignee={assignee}\n{body}")
        return
    cmd = ["gh", "issue", "create", "--title", title, "--body-file", "-", "--label", ",".join(labels)]
    if assignee:
        cmd += ["--assignee", assignee]
    code, out = run(cmd, timeout=40, stdin=body)
    print(out.strip())
    if code != 0:
        sys.exit(f"gh issue create FAILED (exit {code}) — the issue was NOT created. Fix the cause (labels? auth? assignee?) and retry.")


def header_block(agent, prio, start, autonomy, milestone=""):
    return (f"```skylapse\nagent: {agent}\npriority: {prio}\nstart: {start}\nautonomy: {autonomy}\n"
            f"milestone: {milestone}\n```\n\n")


def cmd_task(a):
    need_gh()
    body = Path(a.body_file).read_text(encoding="utf-8")
    if not HEADER_RE.search(body):
        body = header_block(a.agent, a.prio, a.start, a.autonomy, a.milestone) + body
    title = a.title if TITLE_RE.match(a.title) else f"[{a.agent}][{a.prio}][{a.autonomy}] {a.title}"
    labels = [f"agent:{a.agent}", f"type:{a.type}", f"prio:{a.prio}"] + (["needs-human"] if a.autonomy == "human" else [])
    create_issue(title, body, labels, gh_user_for(a.agent))


def cmd_ask(a):
    need_gh()
    body = header_block(a.to, "P1", "now", "auto") + f"Question/request from agent `{me()}`:\n\n" + body_from(a) + \
        "\n\nAnswer with `skyops.py submit <n> --text ...` (questions are closed automatically)."
    create_issue(f"[{a.to}][P1][auto] Q from {me()}: {a.title}", body, [f"agent:{a.to}", "type:question", "prio:P1"],
                 gh_user_for(a.to))


def cmd_escalate(a):
    need_gh()
    title = a.title if a.title.startswith("ESC:") else f"ESC: {a.title}"
    body = Path(a.body_file).read_text(encoding="utf-8")
    create_issue(title, body, ["type:escalation", "prio:P0", "agent:captain"], gh_user_for("captain"))
    print("Now ask your human to send the captain one WhatsApp line: 'ESC #<n>: <one sentence>'.")


def cmd_accept(a):
    need_gh()
    if a.merge_pr:
        code, out = run(["gh", "pr", "merge", a.merge_pr, "--squash", "--delete-branch=false"], timeout=60)
        print(out.strip() or "PR merged")
        if code != 0:
            sys.exit("merge failed — fix conflicts or ask the owner; issue not closed")
    comment(a.number, f"✅ **ACCEPTED** by orchestrator at {stamp()}." + (f" Merged {a.merge_pr}." if a.merge_pr else ""))
    code, out = (0, "") if os.environ.get("SKYOPS_FAKE_ISSUES") else run(["gh", "issue", "close", str(a.number)], timeout=20)
    if code != 0:
        sys.exit(f"could not close #{a.number}: {out.strip()}")
    edit_labels(a.number, remove=["status:review"])  # only after closing, so no worker can see it as open+unlabelled
    print(f"#{a.number} closed (dependents unlock)")


def cmd_changes(a):
    need_gh()
    comment(a.number, f"🔁 **CHANGES REQUESTED** by orchestrator at {stamp()}:\n\n{body_from(a)}")
    edit_labels(a.number, add=["status:changes-requested"], remove=["status:review"])


def cmd_approve(a):
    need_gh()
    comment(a.number, f"👍 Approved by a human at {stamp()}.")
    edit_labels(a.number, add=["approved"])


def cmd_setup_labels(_):
    need_gh()
    for name, color in LABELS.items():
        code, out = run(["gh", "label", "create", name, "--color", color, "--force"])
        print(("ok   " if code == 0 else "FAIL ") + name + ("" if code == 0 else f"  {out.strip()}"))


def cmd_inbox(a):
    need_gh()
    agent = a.agent or me()
    if not agent:
        sys.exit("Unknown agent: create .skylapse-role or pass --agent")
    q = my_queue(agent)
    print("\n".join(fmt(it, why) for it, ok, why in q) or f"No open issues for agent:{agent}.")


def cmd_show(a):
    need_gh()
    code, out = run(["gh", "issue", "view", str(a.number), "--json", "number,title,body,comments"], timeout=15)
    if code != 0:
        sys.exit(out)
    d = json.loads(out)
    text = f"# #{d['number']} {d['title']}\n\n{d['body']}\n"
    for c in d.get("comments", [])[-5:]:
        text += f"\n--- {c.get('author', {}).get('login', '?')} ---\n{c.get('body', '')}\n"
    print(text)
    if a.copy:
        for cmd in (["pbcopy"], ["clip"], ["xclip", "-selection", "clipboard"], ["wl-copy"]):
            if shutil.which(cmd[0]):
                subprocess.run(cmd, input=text, text=True, encoding="utf-8")
                print("(copied)")
                break


def cmd_auto(a):
    f = flag(".skylapse-auto")
    if a.state == "on":
        f.write_text(stamp(), encoding="utf-8")
        flag(".skylapse-pause").unlink(missing_ok=True)
        print("AUTONOMOUS MODE ON. Now run: python ops/bin/skyops.py next --wait 540  (Bash timeout 600000 ms)")
    else:
        f.unlink(missing_ok=True)
        print("AUTONOMOUS MODE OFF (the agent will stop after its current turn).")


def cmd_pause(_):
    flag(".skylapse-pause").write_text(stamp(), encoding="utf-8")
    print("PAUSED. The agent finishes its current step and stops. Resume with: skyops.py resume")


def cmd_resume(_):
    flag(".skylapse-pause").unlink(missing_ok=True)
    print("RESUMED. Tell the agent: 'continue' (it will run next --wait).")


def cmd_status(_):
    print(f"agent={me()}  auto={'ON' if flag('.skylapse-auto').exists() else 'OFF'}  "
          f"paused={'YES' if flag('.skylapse-pause').exists() else 'no'}  time={stamp()} Baku")


def cmd_watch(a):
    need_gh()
    agent = a.agent or me()
    seen = set()
    first = True
    print(f"Watching agent:{agent} every 60 s (Ctrl+C to stop)…")
    while True:
        try:
            for it, ok, why in my_queue(agent):
                if it["number"] not in seen:
                    seen.add(it["number"])
                    if not first:
                        print("\a" + stamp() + "  NEW  " + fmt(it, why), flush=True)
        except Exception as e:
            print("error:", e)
        first = False
        time.sleep(60)


def main():
    p = argparse.ArgumentParser(description="SkyLapse autonomous ops")
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("brief"); s.add_parser("whoami"); s.add_parser("setup-labels")
    s.add_parser("pause"); s.add_parser("resume"); s.add_parser("status")
    x = s.add_parser("next"); x.add_argument("--wait", type=int, default=0); x.add_argument("--json", action="store_true")
    x.add_argument("--agent")
    x = s.add_parser("claim"); x.add_argument("number", type=int)
    x = s.add_parser("submit"); x.add_argument("number", type=int); x.add_argument("--pr")
    g = x.add_mutually_exclusive_group(required=True); g.add_argument("--file"); g.add_argument("--text")
    x = s.add_parser("block"); x.add_argument("number", type=int); x.add_argument("--reason", required=True)
    x = s.add_parser("ask"); x.add_argument("--to", required=True, choices=AGENTS); x.add_argument("--title", required=True)
    g = x.add_mutually_exclusive_group(required=True); g.add_argument("--file"); g.add_argument("--text")
    x = s.add_parser("escalate"); x.add_argument("--title", required=True); x.add_argument("--body-file", required=True)
    x = s.add_parser("task"); x.add_argument("--agent", required=True, choices=AGENTS)
    x.add_argument("--title", required=True); x.add_argument("--body-file", required=True)
    x.add_argument("--prio", default="P1", choices=["P0", "P1", "P2"]); x.add_argument("--start", default="now")
    x.add_argument("--autonomy", default="auto", choices=["auto", "human"]); x.add_argument("--milestone", default="")
    x.add_argument("--type", default="task", choices=["task", "bug", "checkpoint"])
    x = s.add_parser("accept"); x.add_argument("number", type=int); x.add_argument("--merge-pr")
    x = s.add_parser("changes"); x.add_argument("number", type=int)
    g = x.add_mutually_exclusive_group(required=True); g.add_argument("--file"); g.add_argument("--text")
    x = s.add_parser("approve"); x.add_argument("number", type=int)
    x = s.add_parser("inbox"); x.add_argument("--agent")
    x = s.add_parser("show"); x.add_argument("number", type=int); x.add_argument("--copy", action="store_true")
    x = s.add_parser("auto"); x.add_argument("state", choices=["on", "off"])
    x = s.add_parser("watch"); x.add_argument("--agent")
    a = p.parse_args()
    if a.cmd == "brief":
        print(build_brief("manual"))
    elif a.cmd == "whoami":
        print(me() or "unknown")
    else:
        {"setup-labels": cmd_setup_labels, "next": cmd_next, "claim": cmd_claim, "submit": cmd_submit,
         "block": cmd_block, "ask": cmd_ask, "escalate": cmd_escalate, "task": cmd_task, "accept": cmd_accept,
         "changes": cmd_changes, "approve": cmd_approve, "inbox": cmd_inbox, "show": cmd_show, "auto": cmd_auto,
         "pause": cmd_pause, "resume": cmd_resume, "status": cmd_status, "watch": cmd_watch}[a.cmd](a)


if __name__ == "__main__":
    main()
