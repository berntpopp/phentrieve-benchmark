import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx


@dataclass(frozen=True)
class SyntheticHttpResponse:
    body: bytes
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    interrupt_after: int | None = None
    delay_before_body: float = 0.0
    chunk_size: int = 7


class _SyntheticServer(ThreadingHTTPServer):
    response: SyntheticHttpResponse


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        response = self.server.response  # type: ignore[attr-defined]
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        if (
            "Content-Length" not in response.headers
            and response.interrupt_after is None
        ):
            self.send_header("Connection", "close")
        self.end_headers()
        if response.delay_before_body:
            time.sleep(response.delay_before_body)
        body = response.body
        if response.interrupt_after is not None:
            body = body[: response.interrupt_after]
        for offset in range(0, len(body), response.chunk_size):
            self.wfile.write(body[offset : offset + response.chunk_size])
            self.wfile.flush()
        if response.interrupt_after is not None:
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()

    def log_message(self, format: str, *args: object) -> None:
        del format, args


class LoopbackTransport(httpx.BaseTransport):
    def __init__(self, port: int) -> None:
        self._port = port
        self._transport = httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        rewritten_url = request.url.copy_with(
            scheme="http",
            host="127.0.0.1",
            port=self._port,
        )
        rewritten = httpx.Request(
            method=request.method,
            url=rewritten_url,
            headers=request.headers,
            stream=request.stream,
            extensions=request.extensions,
        )
        response = self._transport.handle_request(rewritten)
        return httpx.Response(
            status_code=response.status_code,
            headers=response.headers,
            stream=response.stream,
            extensions=response.extensions,
            request=request,
        )

    def close(self) -> None:
        self._transport.close()


@contextmanager
def synthetic_http_server(
    response: SyntheticHttpResponse,
) -> Iterator[httpx.BaseTransport]:
    server = _SyntheticServer(("127.0.0.1", 0), _Handler)
    server.response = response
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield LoopbackTransport(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
