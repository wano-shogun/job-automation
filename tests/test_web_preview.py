"""Smoke checks for the local dashboard that the preview button opens."""

from threading import Thread
from urllib.request import urlopen

from job_automation.web import create_server, render_dashboard


def test_preview_serves_health_and_dashboard(tmp_path):
    server = create_server(tmp_path / "preview.db", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/health", timeout=3) as response:
            assert response.status == 200
            assert b'"status": "ok"' in response.read()
        with urlopen(base + "/", timeout=3) as response:
            page = response.read().decode("utf-8")
            assert response.status == 200
            assert "ApplyPilot" in page
            assert "Agent attempts" in page
            assert "Recorded applications" in page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_preview_escapes_external_text():
    page = render_dashboard(
        attempts=[{
            "job_title": "<script>alert(1)</script>", "company": "Example",
            "run_id": "abc", "stage": "needs_review",
        }],
        applications=[], jobs=[], query='"><script>alert(2)</script>',
    )
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
