import sys
import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from daily_brief_email import fetch_brief_data

UPSTASH_URL   = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
DAILY_LIMIT   = 100


def _upstash(command: str) -> dict:
    """Call Upstash Redis REST API with a single command string e.g. 'INCR/mykey'."""
    req = urllib.request.Request(
        f"{UPSTASH_URL}/{command}",
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def check_rate_limit() -> tuple[bool, int]:
    """
    Increment today's counter. Returns (allowed, count).
    Falls back to allowing the request if Upstash is not configured.
    """
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return True, 0  # not configured — allow through

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key   = f"brief:count:{today}"

    try:
        result = _upstash(f"INCR/{key}")
        count  = int(result["result"])
        if count == 1:
            # First hit today — set TTL so key auto-expires at next midnight
            _upstash(f"EXPIRE/{key}/86400")
        return count <= DAILY_LIMIT, count
    except Exception:
        return True, 0  # fail open — don't block on Redis errors


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        allowed, count = check_rate_limit()

        if not allowed:
            self.send_response(429)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:sans-serif;padding:40px'>"
                b"<h2>Daily limit reached</h2>"
                b"<p>This page refreshes at most 100 times per day. Check back tomorrow.</p>"
                b"</body></html>"
            )
            return

        try:
            html = fetch_brief_data()
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())

    def log_message(self, format, *args):
        pass  # suppress default access logs
