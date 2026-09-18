"""Local read-only web preview for ApplyPilot."""

from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import json

from job_automation.agent.journal import AgentJournal
from job_automation.db import JobRepository
from job_automation.discovery.ashby import search_ashby_board
from job_automation.models import Job


def create_server(db_path: str | Path, port: int = 8765) -> ThreadingHTTPServer:
    """Bind a local preview server; no application submission routes exist."""
    database = Path(db_path)

    class PreviewHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlsplit(self.path)
            if parsed.path == "/health":
                self._send(json.dumps({"status": "ok", "service": "ApplyPilot"}).encode(), "application/json")
                return
            if parsed.path not in {"/", "/search"}:
                self.send_error(404)
                return

            params = parse_qs(parsed.query)
            query = params.get("query", [""])[0].strip()[:120]
            board = params.get("board", ["super.com"])[0].strip()[:100]
            location = params.get("location", [""])[0].strip()[:100]
            jobs: list[Job] = []
            search_error = ""
            if parsed.path == "/search":
                if not query or not board:
                    search_error = "Enter a job title and an Ashby board name."
                else:
                    try:
                        jobs = search_ashby_board(board, query, location)[:20]
                    except Exception as exc:
                        search_error = f"Job search failed: {exc}"

            with AgentJournal(database) as journal:
                attempts = journal.latest(20)
            with JobRepository(database) as repo:
                applications = repo.list()[:10]
            page = render_dashboard(attempts, applications, jobs, query, board, location, search_error)
            self._send(page.encode("utf-8"), "text/html; charset=utf-8")

        def _send(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", port), PreviewHandler)


def render_dashboard(
    attempts: list[dict[str, object]],
    applications: list[object],
    jobs: list[Job],
    query: str = "",
    board: str = "super.com",
    location: str = "",
    search_error: str = "",
) -> str:
    """Render a local dashboard without exposing saved profile or answers."""
    def safe(value: object) -> str:
        return escape(str(value or ""), quote=True)

    attempt_cards = "".join(
        '<article class="row"><span class="dot"></span><div>'
        f'<strong>{safe(item["job_title"])}</strong><small>{safe(item["company"])} · {safe(item["run_id"])[:8]}</small>'
        f'</div><span class="badge">{safe(item["stage"]).replace("_", " ")}</span></article>'
        for item in attempts
    ) or '<p class="empty">No agent runs yet. Run a search or use the CLI to prepare an application.</p>'

    application_cards = "".join(
        '<article class="row"><span class="dot green"></span><div>'
        f'<strong>{safe(app.role)}</strong><small>{safe(app.company)} · {safe(app.date_applied)}</small>'
        f'</div><span class="badge">{safe(app.status.value)}</span></article>'
        for app in applications
    ) or '<p class="empty">No tracked applications recorded.</p>'

    job_cards = "".join(
        '<article class="job"><div><span class="eyebrow">{}</span><h3>{}</h3><p>{}</p></div>'
        '<a href="{}" target="_blank" rel="noopener noreferrer">Open application ↗</a></article>'.format(
            safe(job.company), safe(job.title), safe(job.location or "Location not listed"), safe(job.url)
        ) for job in jobs
    )
    if query and not search_error and not jobs:
        job_cards = '<p class="empty">No matching jobs found on this board.</p>'
    if search_error:
        job_cards = f'<p class="error">{safe(search_error)}</p>'

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ApplyPilot · Agent Console</title>
<style>
:root{{--ink:#e9eef8;--muted:#9cabbe;--line:#27354b;--panel:#172238;--panel2:#1c2a43;--accent:#77e2b6}}
*{{box-sizing:border-box}}body{{margin:0;background:#0c1525;color:var(--ink);font:15px/1.5 Segoe UI,Arial,sans-serif}}
main{{max-width:1100px;margin:auto;padding:40px 24px 70px}}header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:52px}}
.brand{{font-weight:800;font-size:22px;letter-spacing:-.04em}}.brand span{{color:var(--accent)}}.live{{border:1px solid #315d50;color:var(--accent);padding:5px 11px;border-radius:50px;font-size:12px}}
.eyebrow{{color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}}h1{{font-size:clamp(34px,5vw,58px);line-height:1.05;letter-spacing:-.06em;margin:14px 0}}h2{{font-size:20px;margin:0 0 18px}}h3{{margin:4px 0;font-size:18px}}
.hero p{{max-width:650px;color:var(--muted);font-size:18px}}.grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:20px;margin-top:34px}}.panel{{background:var(--panel);border:1px solid var(--line);border-radius:20px;padding:25px}}
.search{{display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:10px;margin-top:22px}}label{{display:block;color:var(--muted);font-size:12px;margin-bottom:6px}}input{{width:100%;padding:12px;background:#0d1728;color:var(--ink);border:1px solid #34455e;border-radius:9px;font:inherit}}button{{align-self:end;background:var(--accent);border:0;border-radius:9px;padding:13px 18px;color:#092b23;font-weight:800;cursor:pointer}}
.row{{display:flex;align-items:center;gap:12px;padding:14px 0;border-top:1px solid var(--line)}}.row>div{{flex:1;min-width:0}}.row strong{{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}small{{display:block;color:var(--muted)}}.dot{{width:9px;height:9px;flex:none;border-radius:50%;background:#f7ba68}}.dot.green{{background:var(--accent)}}.badge{{font-size:11px;color:#c9d8eb;border:1px solid #43536d;border-radius:20px;padding:4px 8px;white-space:nowrap;text-transform:capitalize}}
.results{{margin-top:22px}}.job{{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:18px 0;border-top:1px solid var(--line)}}.job p{{margin:0;color:var(--muted)}}a{{color:var(--accent);white-space:nowrap}}.empty{{color:var(--muted)}}.error{{color:#ffbdac}}footer{{margin-top:32px;color:var(--muted);font-size:13px}}@media(max-width:800px){{.grid,.search{{display:block}}.panel{{margin-top:16px}}.search>div,button{{margin-top:10px}}.job{{align-items:start;flex-direction:column}}}}
</style></head><body><main>
<header><div class="brand">Apply<span>Pilot</span></div><div class="live">● Local preview</div></header>
<section class="hero"><span class="eyebrow">Browser agent console</span><h1>Your job search,<br>visible and reviewable.</h1><p>Search current jobs on an Ashby board and see the application agent's recorded progress. Browser filling runs from the CLI and stops for review.</p></section>
<section class="panel"><span class="eyebrow">Find jobs</span><h2>Search a public board</h2>
<form class="search" action="/search" method="get"><div><label for="query">Role</label><input id="query" name="query" value="{safe(query)}" placeholder="Full Stack Developer" required></div><div><label for="board">Ashby board</label><input id="board" name="board" value="{safe(board)}" required></div><div><label for="location">Location</label><input id="location" name="location" value="{safe(location)}" placeholder="Remote"></div><button type="submit">Search</button></form>
<div class="results">{job_cards}</div></section>
<section class="grid"><div class="panel"><span class="eyebrow">Recent activity</span><h2>Agent attempts</h2>{attempt_cards}</div><div class="panel"><span class="eyebrow">Tracker</span><h2>Recorded applications</h2>{application_cards}</div></section>
<footer>Local read-only dashboard · Search opens external application pages in a new tab · No application is submitted here</footer>
</main></body></html>'''
