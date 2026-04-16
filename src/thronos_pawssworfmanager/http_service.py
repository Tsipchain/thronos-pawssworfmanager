"""Minimal HTTP bootstrap for Railway runtime shell."""

from __future__ import annotations

import json
from wsgiref.simple_server import make_server

from .app import create_runtime_shell


shell = create_runtime_shell()


def wsgi_app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    request_body = {}

    content_length = environ.get("CONTENT_LENGTH", "")
    if method.upper() in {"POST", "PUT", "PATCH"}:
        try:
            length = int(content_length) if content_length else 0
        except ValueError:
            length = 0
        raw = environ.get("wsgi.input").read(length) if length > 0 else b""
        if raw:
            try:
                request_body = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                request_body = {}

    response = shell.handle(method, path, request_body)

    body = json.dumps(response.body, separators=(",", ":")).encode("utf-8")
    status_line = f"{response.status} {'OK' if response.status < 400 else 'ERROR'}"
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    start_response(status_line, headers)
    return [body]


def run() -> None:
    import os

    port = int(os.getenv("PORT", "8080"))
    with make_server("0.0.0.0", port, wsgi_app) as httpd:
        httpd.serve_forever()
