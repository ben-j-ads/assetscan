"""Local web app: `assetscan serve`. Stdlib only, bound to localhost, nothing leaves your machine."""
from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .io import read_csv_text
from .scan import CHECKS, Asset, analyze
from .io import tri

WEB = Path(__file__).parent / "web"
MAX_BODY = 1_000_000
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}


def _num(v, name, cast=int, default=0):
    if v in (None, ""):
        return default
    try:
        f = float(v)
        return cast(f) if cast is float or f == int(f) else (_ for _ in ()).throw(ValueError())
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be a whole number" if cast is int else f"'{name}' must be a number") from None


def handle_scan(body: dict) -> dict:
    if body.get("csv"):
        assets = read_csv_text(body["csv"])
    else:
        assets = []
        for row in body.get("assets") or []:
            name = str(row.get("name", "")).strip()
            rivals = {}
            if row.get("rival_detail"):
                rivals = {str(k): _num(v, f"{name} {k}") for k, v in row["rival_detail"].items() if _num(v, k) > 0}
            elif _num(row.get("rivals"), f"{name} rivals") > 0:
                rivals = {"Rivals": _num(row.get("rivals"), f"{name} rivals")}
            assets.append(Asset(name, _num(row.get("n"), f"{name} respondents"), _num(row.get("brand"), f"{name} brand"),
                                rivals, bool(row.get("prompted")), str(row.get("segment", "")).strip(),
                                {k: tri(v) for k, v in (row.get("checks") or {}).items() if k in CHECKS},
                                _num(row.get("used"), f"{name} touchpoints used"), _num(row.get("total"), f"{name} touchpoints total")))
    return analyze(assets, _num(body.get("fame_cut"), "fame cut", float, 30) / 100,
                   _num(body.get("uniq_cut"), "uniqueness cut", float, 50) / 100,
                   _num(body.get("w_fame"), "fame weight", float, 50) / 100)


API = {"/api/scan": handle_scan}


class Handler(BaseHTTPRequestHandler):
    server_version = "assetscan"

    def log_message(self, *args):
        pass

    def _host_ok(self) -> bool:
        host = self.headers.get("Host") or ""
        name = host.split("]")[0] + "]" if host.startswith("[") else host.rsplit(":", 1)[0]
        return name in LOCAL_HOSTS

    def _send(self, code, body: bytes, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        if not self._host_ok():
            return self._json(403, {"error": "forbidden host"})
        path = self.path.split("?", 1)[0]
        target = (WEB / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
        if WEB.resolve() not in target.parents or not target.is_file():
            return self._json(404, {"error": "not found"})
        ctype = "font/ttf" if target.suffix == ".ttf" else (mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)

    def do_POST(self):
        if not self._host_ok():
            return self._json(403, {"error": "forbidden host"})
        fn = API.get(self.path.split("?", 1)[0])
        if fn is None:
            return self._json(404, {"error": "not found"})
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._json(415, {"error": "send application/json"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._json(413, {"error": "request too large"})
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("expected a JSON object")
            self._json(200, fn(body))
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            self._json(400, {"error": str(e) or "bad request"})


def make_server(port: int = 8766) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(port: int = 8766, open_browser: bool = True) -> None:
    httpd = make_server(port)
    url = f"http://localhost:{httpd.server_address[1]}/"
    print(f"assetscan is running at {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        httpd.server_close()
