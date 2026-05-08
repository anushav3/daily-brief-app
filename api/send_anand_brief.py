import sys
import os
import io
import contextlib
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from anand_daily_brief_email import main


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        cron_secret = os.environ.get("CRON_SECRET", "")
        auth_header = self.headers.get("Authorization", "")
        if cron_secret and auth_header != f"Bearer {cron_secret}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                main()
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Anand's brief sent successfully")
        except SystemExit:
            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            output = buf.getvalue() or "No output captured"
            self.wfile.write(f"Error (captured output):\n{output}".encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            output = buf.getvalue()
            self.wfile.write(f"Error: {e}\nOutput:\n{output}".encode())

    def log_message(self, format, *args):
        pass
