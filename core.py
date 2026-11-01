import json
import os
import re
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

import music

APP_ID = "atsflow-v1"
DISCOVERY_PORT = 50505
ANNOUNCE_INTERVAL = 3
PEER_TIMEOUT = 12
CHUNK_SIZE = 1024 * 256

MEDIA_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/opus",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
}


class Discovery:
    def __init__(self, http_port):
        self.http_port = http_port
        self.id = uuid.uuid4().hex
        self.name = socket.gethostname()
        self.peers = {}
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        threading.Thread(target=self._announce_loop, daemon=True).start()
        threading.Thread(target=self._listen, daemon=True).start()

    def stop(self):
        self.running = False

    def _announce_loop(self):
        msg = json.dumps(
            {"app": APP_ID, "id": self.id, "name": self.name, "port": self.http_port}
        ).encode("utf-8")
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.settimeout(2)
                s.sendto(msg, ("<broadcast>", DISCOVERY_PORT))
                s.close()
            except OSError:
                pass
            time.sleep(ANNOUNCE_INTERVAL)

    def _listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", DISCOVERY_PORT))
        except OSError:
            return
        s.settimeout(1)
        while self.running:
            try:
                data, addr = s.recvfrom(4096)
                msg = json.loads(data.decode("utf-8"))
                if msg.get("app") != APP_ID or msg.get("id") == self.id:
                    continue
                with self.lock:
                    self.peers[msg["id"]] = {
                        "id": msg["id"],
                        "ip": addr[0],
                        "port": int(msg["port"]),
                        "name": msg.get("name", addr[0]),
                        "last_seen": time.time(),
                    }
            except (OSError, ValueError, KeyError):
                continue

    def get_peers(self):
        now = time.time()
        with self.lock:
            for pid in [
                pid
                for pid, p in self.peers.items()
                if now - p["last_seen"] > PEER_TIMEOUT
            ]:
                del self.peers[pid]
            return [dict(p) for p in self.peers.values()]


def list_files(shared_dir):
    root = os.path.realpath(shared_dir)
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            full = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            rel = os.path.relpath(full, root).replace("\\", "/")
            files.append({"path": rel, "size": size})
    files.sort(key=lambda f: f["path"].lower())
    return files


def resolve_file(shared_dir, rel):
    root = os.path.realpath(shared_dir)
    full = os.path.realpath(os.path.join(root, rel))
    if full != root and not full.startswith(root + os.sep):
        return None
    if not os.path.isfile(full):
        return None
    return full


class Handler(BaseHTTPRequestHandler):
    discovery = None
    shared_dir = None
    web_dir = None
    assets_dir = None
    server_version = "AtsFlow/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body, content_type, code=200):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        if route == "/api/info":
            self._send_json(
                {
                    "id": self.discovery.id,
                    "name": self.discovery.name,
                    "port": self.discovery.http_port,
                    "files": list_files(self.shared_dir),
                }
            )
        elif route == "/api/peers":
            self._send_json(self.discovery.get_peers())
        elif route == "/api/search":
            q = unquote(parse_qs(parsed.query).get("q", [""])[0]).strip()
            if not q:
                self._send_json({"error": "bos sorgu"}, 400)
                return
            try:
                self._send_json(music.search(q))
            except Exception as exc:
                self._send_json({"error": str(exc)}, 500)
        elif route == "/api/dlmusic":
            qs = parse_qs(parsed.query)
            url = unquote(qs.get("url", [""])[0])
            fmt = unquote(qs.get("fmt", [""])[0])
            if not url:
                self._send_json({"error": "bos url"}, 400)
                return
            try:
                self._send_json(music.start_download(url, fmt, self.shared_dir))
            except Exception as exc:
                self._send_json({"error": str(exc)}, 400)
        elif route == "/api/dljobs":
            self._send_json(music.get_jobs())
        elif route == "/api/resolve":
            qs = parse_qs(parsed.query)
            url = unquote(qs.get("url", [""])[0])
            kind = unquote(qs.get("kind", ["audio"])[0])
            if not url:
                self._send_json({"error": "bos url"}, 400)
                return
            try:
                self._send_json(music.resolve(url, kind))
            except Exception as exc:
                self._send_json({"error": str(exc)}, 500)
        elif route == "/download":
            self._download(parse_qs(parsed.query))
        elif route == "/play":
            self._play(parse_qs(parsed.query), self.headers.get("Range"))
        elif route == "/":
            try:
                with open(os.path.join(self.web_dir, "index.html"), "rb") as f:
                    self._send_bytes(f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send_bytes("index.html bulunamadi".encode(), "text/plain", 500)
        elif route.startswith("/assets/"):
            name = os.path.basename(unquote(route))
            ext = os.path.splitext(name)[1].lower()
            ctype = {
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".ico": "image/x-icon",
                ".json": "application/manifest+json",
            }.get(ext, "application/octet-stream")
            try:
                with open(os.path.join(self.assets_dir, name), "rb") as f:
                    self._send_bytes(f.read(), ctype)
            except OSError:
                self._send_json({"error": "not found"}, 404)
        else:
            self._send_json({"error": "not found"}, 404)

    def _download(self, qs):
        rel = unquote(qs.get("f", [""])[0])
        full = resolve_file(self.shared_dir, rel)
        if full is None:
            self._send_json({"error": "file not found"}, 404)
            return
        size = os.path.getsize(full)
        fname = os.path.basename(full)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.send_header(
            "Content-Disposition",
            "attachment; filename*=UTF-8''" + quote(fname),
        )
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            with open(full, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (OSError, ConnectionError):
            pass

    def _play(self, qs, range_header):
        rel = unquote(qs.get("f", [""])[0])
        full = resolve_file(self.shared_dir, rel)
        if full is None:
            self._send_json({"error": "file not found"}, 404)
            return
        size = os.path.getsize(full)
        ctype = MEDIA_TYPES.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        start, end = 0, size - 1
        status = 200
        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)", range_header.strip())
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    start = int(m.group(1))
                    if m.group(2):
                        end = int(m.group(2))
                else:
                    start = max(0, size - int(m.group(2)))
                end = min(end, size - 1)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                status = 206
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            with open(full, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (OSError, ConnectionError):
            pass


def make_server(shared_dir, web_dir, discovery, port=0, assets_dir=None):
    handler = type("BoundHandler", (Handler,), {})
    handler.discovery = discovery
    handler.shared_dir = shared_dir
    handler.web_dir = web_dir
    handler.assets_dir = assets_dir
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    return server
