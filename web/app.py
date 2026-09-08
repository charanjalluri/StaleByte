"""
app.py
------
Standard library HTTP API server and static frontend host for StaleByte.
Connects directly to the services layer without re-implementing cache logic.
"""

from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Ensure stalebyte/ root is in sys.path when executed directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from services import ai_service, simulation_service

STATIC_DIR = Path(__file__).parent / "static"


def _safe_generate_summary(result_data: dict[str, Any]) -> str | None:
    """Safely obtain an automatic AI summary, never allowing an AI exception to break core responses."""
    try:
        return ai_service.generate_result_summary(result_data)
    except Exception:
        return None


class StaleByteRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for StaleByte Web & API."""

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/api/status":
                status_data = simulation_service.get_system_status()
                self._send_json(status_data)
                return

            if path == "/api/chat/status":
                health = ai_service.check_ai_health(timeout=2.0)
                self._send_json(health)
                return

            if path in ("/api/check", "/check"):
                result = simulation_service.run_check()
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/build", "/build"):
                result = simulation_service.run_build()
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/run/normal", "/run/normal"):
                result = simulation_service.run_normal_flow()
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/run/collision", "/run/collision"):
                result = simulation_service.run_collision_scenario()
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/run/skew", "/run/skew"):
                result = simulation_service.run_clock_skew_scenario()
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/", "/index.html", "/dashboard", "/dashboard.html", "/demo", "/demo.html"):
                self._serve_static_file(STATIC_DIR / "index.html")
                return

            if path.startswith("/static/"):
                rel_path = path.replace("/static/", "", 1)
                target = STATIC_DIR / rel_path
                self._serve_static_file(target)
                return

            # Direct root static lookup fallback (e.g. /styles.css, /app.js)
            direct_target = STATIC_DIR / path.lstrip("/")
            if direct_target.is_file():
                self._serve_static_file(direct_target)
                return

            self._send_error(HTTPStatus.NOT_FOUND, "Not Found")
        except Exception as exc:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Internal server error: {exc}")

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path

            # Read optional input payload safely
            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except (ValueError, TypeError):
                self._send_error(HTTPStatus.BAD_REQUEST, "Invalid Content-Length header.")
                return

            if content_length > 1_048_576:
                try:
                    remaining = content_length
                    while remaining > 0:
                        chunk = self.rfile.read(min(remaining, 65536))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                except Exception:
                    pass
                self._send_error(HTTPStatus.BAD_REQUEST, "File exceeds maximum allowable size of 1MB.")
                return

            body: Any = {}
            if content_length > 0:
                content_type = self.headers.get("Content-Type", "")
                raw_bytes = self.rfile.read(content_length)
                if "application/json" in content_type:
                    try:
                        body = json.loads(raw_bytes.decode("utf-8"))
                    except Exception:
                        self._send_error(HTTPStatus.BAD_REQUEST, "Malformed JSON in request body.")
                        return
                elif "multipart/form-data" in content_type:
                    body = self._parse_multipart(raw_bytes, content_type)
                elif "text/plain" in content_type:
                    try:
                        body = {"filename": "upload.src", "content": raw_bytes.decode("utf-8")}
                    except UnicodeDecodeError:
                        self._send_error(HTTPStatus.BAD_REQUEST, "Request body is not valid UTF-8 text.")
                        return
                else:
                    try:
                        body = json.loads(raw_bytes.decode("utf-8"))
                    except Exception:
                        body = {"content": raw_bytes.decode("utf-8", errors="ignore")}

            if not isinstance(body, dict):
                self._send_error(HTTPStatus.BAD_REQUEST, "Request body must be a JSON object.")
                return

            try:
                input_val = int(body.get("input_value", 10))
            except (ValueError, TypeError):
                self._send_error(HTTPStatus.BAD_REQUEST, "Invalid 'input_value': must be an integer.")
                return
            v1_src = body.get("v1_source")
            v2_src = body.get("v2_source")
            src_content = body.get("source_content")

            if path in ("/api/clean", "/api/cache/clean"):
                from cache import CacheStore
                store = CacheStore()
                store.invalidate()
                for p in store.cache_dir.glob("*.json"):
                    try:
                        p.unlink()
                    except OSError:
                        pass
                uploads_dir = store.cache_dir / "uploads"
                if uploads_dir.is_dir():
                    for p in uploads_dir.iterdir():
                        if p.name == ".gitkeep":
                            continue
                        try:
                            p.unlink()
                        except OSError:
                            pass
                self._send_json({"cleared": True, "message": "Cache successfully cleared."})
                return

            if path in ("/api/upload-check", "/upload-check"):
                filename = body.get("filename") or "upload.src"
                content = body.get("content")
                if content is None and "file_content" in body:
                    content = body["file_content"]
                if content is None:
                    self._send_error(HTTPStatus.BAD_REQUEST, "Missing file content in request.")
                    return
                result = simulation_service.check_uploaded_source(
                    filename=str(filename),
                    content=str(content),
                )
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/check", "/check"):
                target_file = body.get("path") or body.get("file") or body.get("filename")
                content = body.get("content") or body.get("file_content")
                result = simulation_service.run_check(
                    path_or_filename=str(target_file) if target_file else None,
                    content=str(content) if content is not None else None,
                )
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/build", "/build"):
                target_file = body.get("path") or body.get("file") or body.get("filename")
                content = body.get("content") or body.get("file_content")
                strategy = body.get("strategy", "robust")
                result = simulation_service.run_build(
                    path_or_filename=str(target_file) if target_file else None,
                    content=str(content) if content is not None else None,
                    input_value=input_val,
                    strategy=str(strategy),
                )
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/run/collision", "/run/collision"):
                result = simulation_service.run_collision_scenario(
                    input_value=input_val,
                    v1_content=v1_src,
                    v2_content=v2_src,
                )
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/run/normal", "/run/normal"):
                result = simulation_service.run_normal_flow(
                    input_value=input_val,
                    source_content=src_content or v1_src,
                )
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path in ("/api/run/skew", "/run/skew"):
                result = simulation_service.run_clock_skew_scenario(
                    input_value=input_val,
                    source_content=src_content or v1_src,
                )
                result["ai_summary"] = _safe_generate_summary(result)
                self._send_json(result)
                return

            if path == "/api/chat":
                messages = body.get("messages", [])
                if not isinstance(messages, list):
                    self._send_error(HTTPStatus.BAD_REQUEST, "'messages' must be a list of message objects.")
                    return
                stream_requested = bool(body.get("stream", True))

                if stream_requested:
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "close")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.close_connection = True

                    try:
                        for chunk in ai_service.stream_chat_completion(messages):
                            payload_str = json.dumps({"content": chunk})
                            self.wfile.write(f"data: {payload_str}\n\n".encode("utf-8"))
                            self.wfile.flush()
                        self.wfile.write(b"data: [DONE]\n\n")
                        self.wfile.flush()
                    except Exception:
                        err_str = json.dumps({"error": "Streaming interrupted."})
                        self.wfile.write(f"data: {err_str}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    return

                reply_text = ai_service.get_chat_response(messages)
                self._send_json({"reply": reply_text, "model": ai_service.MODEL_ID})
                return

            if path in ("/explain", "/api/explain"):
                explanation = ai_service.explain_diagnostic(body)
                self._send_json({
                    "explanation": explanation,
                    "model": ai_service.MODEL_ID,
                })
                return

            self._send_error(HTTPStatus.NOT_FOUND, "Not Found")
        except ValueError as val_err:
            self._send_error(HTTPStatus.BAD_REQUEST, str(val_err))
            return
        except Exception as exc:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Simulation error: {exc}")
            return

        self._send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _serve_static_file(self, file_path: Path) -> None:
        if not file_path.is_file() or not str(file_path.resolve()).startswith(str(STATIC_DIR.resolve())):
            self._send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"

        try:
            content = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as exc:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Error reading file: {exc}")

    def _send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        payload = json.dumps({"error": message, "status": status.value}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _parse_multipart(self, raw_bytes: bytes, content_type: str) -> dict[str, Any]:
        """Safely parse multipart/form-data payloads without external dependencies."""
        try:
            from email.parser import BytesParser
            raw_message = f"Content-Type: {content_type}\r\n\r\n".encode("latin-1") + raw_bytes
            msg = BytesParser().parsebytes(raw_message)
            res: dict[str, Any] = {}
            if msg.is_multipart():
                for part in msg.iter_parts():
                    fname = part.get_filename()
                    payload = part.get_payload(decode=True)
                    text_val = payload.decode("utf-8", errors="replace") if payload else ""
                    if fname:
                        res["filename"] = fname
                        res["content"] = text_val
                        break
                    field_name = part.get_param("name", header="content-disposition")
                    if field_name == "file":
                        res["filename"] = fname or "upload.src"
                        res["content"] = text_val
                        break
                    if field_name:
                        res[field_name] = text_val
            return res
        except Exception:
            return {}

    def log_message(self, format: str, *args: Any) -> None:
        # Override to keep test/console output clean
        pass


def create_server(host: str = "127.0.0.1", port: int = 8000) -> HTTPServer:
    """Create and return a configured HTTPServer instance."""
    return ThreadingHTTPServer((host, port), StaleByteRequestHandler)


def check_startup_ai_service() -> dict[str, Any]:
    """Perform a lightweight ping to the AI endpoint on server startup and log status."""
    ai_service.load_env_file()
    health = ai_service.check_ai_health(timeout=3.0)
    cfg_text = "KEY CONFIGURED" if health["configured"] else "NO KEY (Deterministic fallback active)"
    reach_text = "ENDPOINT REACHABLE" if health["reachable"] else f"ENDPOINT UNREACHABLE ({health.get('message', '')})"
    print(f"[AI Startup Check] Model: {health['model']} | {cfg_text} | {reach_text} | Endpoint: {health['endpoint']}")
    return health


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the web server synchronously."""
    server = create_server(host, port)
    print(f"StaleByte Web Dashboard running at http://{host}:{port}/")
    check_startup_ai_service()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down StaleByte Web Dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
