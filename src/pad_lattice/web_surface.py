"""Authenticated browser implementation of the Pad-Lattice surface contract."""

from __future__ import annotations

import hmac
import http
import ipaddress
import mimetypes
import queue
import secrets
import threading
import time
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path, PurePosixPath
from typing import Any, Callable
from urllib.parse import unquote, urlsplit

import segno
from websockets.datastructures import Headers, MultipleValuesError
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response
from websockets.sync.server import Server, ServerConnection, serve

from pad_lattice.devices.base import (
    ActionPressed,
    SessionSelected,
    SurfaceEvent,
    SurfaceView,
)
from pad_lattice.visual_protocol import IDENTITY_ACCENTS, VISUAL_PROTOCOL_VERSION
from pad_lattice.web_protocol import (
    ActionCommand,
    AuthenticateCommand,
    CreatePairingCommand,
    RevokeRemoteCommand,
    SelectSessionCommand,
    WebProtocolError,
    decode_web_message,
    encode_web_message,
    parse_web_command,
    surface_message,
    web_error,
    web_message,
)

PAIRING_TTL = 5 * 60
AUTHENTICATION_TIMEOUT = 10.0
FAILED_ATTEMPT_WINDOW = 60.0
FAILED_ATTEMPT_LIMIT = 5
GLOBAL_PAIRING_ATTEMPT_LIMIT = 20
MAX_PENDING_SURFACE_EVENTS = 256
MAX_BROWSER_CLIENTS = 16
MAX_REMOTE_CLIENTS = 8
COMMAND_RATE_WINDOW = 1.0
COMMAND_RATE_LIMIT = 20


@dataclass(frozen=True)
class PairingCredential:
    pin: str
    secret: str
    pairing_url: str
    qr_data_uri: str
    expires_at: float
    attempts: int = 0


@dataclass
class BrowserClient:
    connection: ServerConnection
    admin: bool
    remote: bool
    send_lock: threading.Lock = field(default_factory=threading.Lock)
    command_times: list[float] = field(default_factory=list)

    def send(self, message: dict[str, Any]) -> None:
        with self.send_lock:
            self.connection.send(encode_web_message(message))

    def allow_command(self, now: float) -> bool:
        self.command_times = [
            timestamp
            for timestamp in self.command_times
            if now - timestamp < COMMAND_RATE_WINDOW
        ]
        if len(self.command_times) >= COMMAND_RATE_LIMIT:
            return False
        self.command_times.append(now)
        return True


class BrowserSurfaceServer:
    """Serve static UI assets and authenticated surface messages."""

    def __init__(
        self,
        event_sink: Callable[[SurfaceEvent], None],
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        asset_root: Path | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.event_sink = event_sink
        self.host = host
        self.port = port
        self.asset_root = asset_root
        self.clock = clock
        self._server: Server | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self._clients: dict[int, BrowserClient] = {}
        self._clients_lock = threading.RLock()
        self._pending_clients = 0
        self._pending_remote_clients = 0
        self._auth_lock = threading.RLock()
        self._latest_surface: dict[str, Any] | None = None
        self._pairing: PairingCredential | None = None
        self._session_tokens: set[str] = set()
        self._failed_attempts: dict[str, list[float]] = {}
        self._advertised_base_url: str | None = None
        self._advertised_hostname: str | None = None
        self._closed = False

    @property
    def actual_port(self) -> int:
        if self._server is None:
            return self.port
        return int(self._server.socket.getsockname()[1])

    @property
    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.actual_port}"

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._serve,
            name="pad-lattice-web",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5.0):
            raise OSError("timed out while starting browser surface")
        if self._startup_error is not None:
            raise OSError(
                f"could not start browser surface: {self._startup_error}"
            ) from self._startup_error

    def broadcast_surface(self, message: dict[str, Any]) -> None:
        self._latest_surface = message
        self._broadcast(message)

    def configure_lan(self, advertised_base_url: str) -> None:
        parsed = urlsplit(advertised_base_url)
        try:
            advertised_port = parsed.port
        except ValueError as exc:
            raise ValueError("advertised LAN URL must be an HTTP origin") from exc
        if (
            parsed.scheme != "http"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or (advertised_port or 80) != self.actual_port
        ):
            raise ValueError("advertised LAN URL must be an HTTP origin")
        hostname = parsed.hostname.lower()
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            if not address.is_private or address.is_loopback or address.is_unspecified:
                raise ValueError("advertised LAN address must be a private address")
        with self._auth_lock:
            self._advertised_base_url = advertised_base_url.rstrip("/")
            self._advertised_hostname = hostname

    def create_pairing(self) -> dict[str, Any]:
        with self._auth_lock:
            if self._advertised_base_url is None:
                raise WebProtocolError("LAN access is not enabled", code="lan_disabled")
            now = self.clock()
            secret = secrets.token_urlsafe(24)
            pin = f"{secrets.randbelow(1_000_000):06d}"
            pairing_url = f"{self._advertised_base_url}/#pair={secret}"
            qr = segno.make(pairing_url, error="m")
            credential = PairingCredential(
                pin=pin,
                secret=secret,
                pairing_url=pairing_url,
                qr_data_uri=str(qr.svg_data_uri(scale=5, border=2)),
                expires_at=now + PAIRING_TTL,
            )
            self._pairing = credential
        return web_message(
            "pairing",
            pin=credential.pin,
            pairing_url=credential.pairing_url,
            qr_data_uri=credential.qr_data_uri,
            expires_in=PAIRING_TTL,
        )

    def revoke_remote(self) -> None:
        with self._auth_lock:
            self._session_tokens.clear()
            self._pairing = None
        with self._clients_lock:
            clients = tuple(self._clients.values())
        for client in clients:
            if client.remote:
                try:
                    client.connection.close(1008, "authorization revoked")
                except OSError:
                    pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.revoke_remote()
        with self._clients_lock:
            clients = tuple(self._clients.values())
        for client in clients:
            try:
                client.connection.close(1001, "server shutting down")
            except OSError:
                pass
        if self._server is not None:
            self._server.shutdown()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=5.0)
        self._thread = None
        self._server = None

    def _serve(self) -> None:
        try:
            self._server = serve(
                self._handle_connection,
                self.host,
                self.port,
                process_request=self._process_request,
                server_header=None,
                compression=None,
                close_timeout=1,
                max_size=16 * 1024,
                max_queue=8,
            )
        except BaseException as exc:
            self._startup_error = exc
            self._ready.set()
            return
        self._ready.set()
        try:
            self._server.serve_forever()
        finally:
            self._server = None

    def _process_request(
        self,
        connection: ServerConnection,
        request: Request,
    ) -> Response | None:
        if not self._valid_host(request):
            return self._response(
                http.HTTPStatus.BAD_REQUEST,
                b"Invalid Host\n",
                "text/plain",
            )
        path = urlsplit(request.path).path
        if path == "/ws":
            if not self._same_origin(request):
                return self._response(
                    http.HTTPStatus.FORBIDDEN,
                    b"WebSocket origin rejected\n",
                    "text/plain",
                )
            return None
        if path == "/config.json":
            return self._response(
                http.HTTPStatus.OK,
                b'{"mode":"live","protocol":1}',
                "application/json",
            )
        return self._static_response(path)

    def _handle_connection(self, connection: ServerConnection) -> None:
        peer = _peer_host(connection.remote_address)
        loopback = _is_loopback(peer)
        client: BrowserClient | None = None
        reserved = False
        try:
            if not self._reserve_client(remote=not loopback):
                raise WebProtocolError(
                    "browser connection limit reached",
                    code="connection_limit",
                )
            reserved = True
            raw = connection.recv(timeout=AUTHENTICATION_TIMEOUT)
            command = parse_web_command(decode_web_message(raw))
            if not isinstance(command, AuthenticateCommand):
                raise WebProtocolError(
                    "authenticate before sending commands",
                    code="authentication_required",
                )
            authenticated, issued_token = self._authenticate(
                peer,
                command.credential,
                loopback=loopback,
            )
            if not authenticated:
                raise WebProtocolError(
                    "invalid or expired credential",
                    code="forbidden",
                )

            client = BrowserClient(connection, admin=loopback, remote=not loopback)
            with self._clients_lock:
                self._release_client_reservation(client.remote)
                reserved = False
                self._clients[id(connection)] = client
            client.send(
                web_message(
                    "authenticated",
                    admin=client.admin,
                    session_token=issued_token,
                    lan_enabled=self._advertised_base_url is not None,
                )
            )
            with self._auth_lock:
                pairing = self._pairing if client.admin else None
                remaining = (
                    round(pairing.expires_at - self.clock())
                    if pairing is not None
                    else 0
                )
            if pairing is not None:
                if remaining > 0:
                    client.send(
                        web_message(
                            "pairing",
                            pin=pairing.pin,
                            pairing_url=pairing.pairing_url,
                            qr_data_uri=pairing.qr_data_uri,
                            expires_in=remaining,
                        )
                    )
            if self._latest_surface is not None:
                client.send(self._latest_surface)

            while True:
                raw = connection.recv()
                try:
                    if not client.allow_command(self.clock()):
                        client.send(
                            web_error(
                                WebProtocolError(
                                    "browser command rate exceeded",
                                    code="rate_limited",
                                )
                            )
                        )
                        connection.close(1008, "command rate exceeded")
                        return
                    command = parse_web_command(decode_web_message(raw))
                    self._handle_command(client, command)
                except WebProtocolError as exc:
                    client.send(web_error(exc))
        except TimeoutError:
            self._send_unregistered(
                connection,
                web_error(
                    WebProtocolError(
                        "authentication timed out",
                        code="authentication_timeout",
                    )
                ),
            )
        except WebProtocolError as exc:
            self._send_unregistered(connection, web_error(exc))
        except ConnectionClosed:
            pass
        finally:
            with self._clients_lock:
                if reserved:
                    self._release_client_reservation(not loopback)
                self._clients.pop(id(connection), None)

    def _reserve_client(self, *, remote: bool) -> bool:
        with self._clients_lock:
            total = len(self._clients) + self._pending_clients
            remote_total = (
                sum(client.remote for client in self._clients.values())
                + self._pending_remote_clients
            )
            if total >= MAX_BROWSER_CLIENTS or (
                remote and remote_total >= MAX_REMOTE_CLIENTS
            ):
                return False
            self._pending_clients += 1
            if remote:
                self._pending_remote_clients += 1
            return True

    def _release_client_reservation(self, remote: bool) -> None:
        self._pending_clients -= 1
        if remote:
            self._pending_remote_clients -= 1

    def _handle_command(self, client: BrowserClient, command: object) -> None:
        if isinstance(command, AuthenticateCommand):
            raise WebProtocolError("client is already authenticated")
        if isinstance(command, ActionCommand):
            self.event_sink(ActionPressed(command.action))
            return
        if isinstance(command, SelectSessionCommand):
            self.event_sink(SessionSelected(command.slot))
            return
        if isinstance(command, CreatePairingCommand):
            self._require_admin(client)
            client.send(self.create_pairing())
            return
        if isinstance(command, RevokeRemoteCommand):
            self._require_admin(client)
            self.revoke_remote()
            client.send(web_message("remote_revoked"))
            return
        raise AssertionError(f"unhandled web command: {command!r}")

    def _authenticate(
        self,
        peer: str,
        credential: str | None,
        *,
        loopback: bool,
    ) -> tuple[bool, str | None]:
        with self._auth_lock:
            if loopback and credential is None:
                return True, None
            if credential is None or self._rate_limited(peer):
                return False, None
            if any(
                hmac.compare_digest(credential, token)
                for token in self._session_tokens
            ):
                return True, None

            pairing = self._pairing
            now = self.clock()
            if pairing is not None and now < pairing.expires_at and (
                hmac.compare_digest(credential, pairing.pin)
                or hmac.compare_digest(credential, pairing.secret)
            ):
                token = secrets.token_urlsafe(32)
                self._session_tokens.add(token)
                self._pairing = None
                self._failed_attempts.pop(peer, None)
                return True, token

            self._record_failed_attempt(peer)
            if pairing is not None:
                attempts = pairing.attempts + 1
                if attempts >= GLOBAL_PAIRING_ATTEMPT_LIMIT:
                    self._pairing = None
                else:
                    self._pairing = PairingCredential(
                        pin=pairing.pin,
                        secret=pairing.secret,
                        pairing_url=pairing.pairing_url,
                        qr_data_uri=pairing.qr_data_uri,
                        expires_at=pairing.expires_at,
                        attempts=attempts,
                    )
            return False, None

    def _rate_limited(self, peer: str) -> bool:
        with self._auth_lock:
            now = self.clock()
            attempts = [
                attempt
                for attempt in self._failed_attempts.get(peer, ())
                if now - attempt < FAILED_ATTEMPT_WINDOW
            ]
            self._failed_attempts[peer] = attempts
            return len(attempts) >= FAILED_ATTEMPT_LIMIT

    def _record_failed_attempt(self, peer: str) -> None:
        with self._auth_lock:
            self._failed_attempts.setdefault(peer, []).append(self.clock())

    def _broadcast(self, message: dict[str, Any]) -> None:
        with self._clients_lock:
            clients = tuple(self._clients.values())
        for client in clients:
            try:
                client.send(message)
            except (ConnectionClosed, OSError):
                with self._clients_lock:
                    self._clients.pop(id(client.connection), None)

    def _send_unregistered(
        self,
        connection: ServerConnection,
        message: dict[str, Any],
    ) -> None:
        try:
            connection.send(encode_web_message(message))
        except (ConnectionClosed, OSError):
            pass

    def _require_admin(self, client: BrowserClient) -> None:
        if not client.admin:
            raise WebProtocolError(
                "local administrator required",
                code="admin_required",
            )

    def _valid_host(self, request: Request) -> bool:
        try:
            host_header = request.headers.get("Host")
        except MultipleValuesError:
            return False
        if not host_header:
            return False
        return self._host_is_allowed(host_header)

    def _host_is_allowed(self, authority: str) -> bool:
        try:
            parsed = urlsplit(f"//{authority}")
            hostname = (parsed.hostname or "").lower()
            port = parsed.port
        except ValueError:
            return False
        expected_port = self.actual_port
        if port is None:
            port = 80
        if port != expected_port:
            return False
        if hostname in {"localhost", "127.0.0.1"}:
            return True
        if self.host == "127.0.0.1":
            return False
        with self._auth_lock:
            return hostname == self._advertised_hostname

    def _same_origin(self, request: Request) -> bool:
        try:
            origin = request.headers.get("Origin")
            host = request.headers.get("Host")
        except MultipleValuesError:
            return False
        if origin is None or host is None:
            return False
        parsed = urlsplit(origin)
        return parsed.scheme == "http" and parsed.netloc == host

    def _static_response(self, requested_path: str) -> Response:
        decoded = unquote(requested_path)
        relative = PurePosixPath(decoded.lstrip("/") or "index.html")
        if any(part in {"", ".", ".."} for part in relative.parts):
            return self._response(
                http.HTTPStatus.NOT_FOUND,
                b"Not found\n",
                "text/plain",
            )
        try:
            if self.asset_root is not None:
                asset = self.asset_root.joinpath(*relative.parts)
                body = asset.read_bytes()
            else:
                asset = resources.files("pad_lattice").joinpath(
                    "web_dist", "play", *relative.parts
                )
                body = asset.read_bytes()
        except (FileNotFoundError, IsADirectoryError):
            return self._response(
                http.HTTPStatus.NOT_FOUND,
                b"Not found\n",
                "text/plain",
            )
        content_type = (
            mimetypes.guess_type(str(relative))[0] or "application/octet-stream"
        )
        return self._response(http.HTTPStatus.OK, body, content_type)

    def _response(
        self,
        status: http.HTTPStatus,
        body: bytes,
        content_type: str,
    ) -> Response:
        headers = Headers()
        headers["Content-Type"] = f"{content_type}; charset=utf-8"
        headers["Content-Length"] = str(len(body))
        headers["Cache-Control"] = "no-store"
        headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "style-src 'self'; script-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'"
        )
        headers["Referrer-Policy"] = "no-referrer"
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        return Response(status.value, status.phrase, headers, body)


class WebSurface:
    """Surface adapter backed by authenticated browser clients."""

    surface_kind = "web"
    profile_id = "virtual/browser"
    input_name = "Browser controls"
    output_name = "Browser display"
    selector_capacity = 8
    accent_names = IDENTITY_ACCENTS
    visual_protocol = VISUAL_PROTOCOL_VERSION

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8765,
        asset_root: Path | None = None,
    ) -> None:
        self._events: queue.Queue[SurfaceEvent] = queue.Queue(
            maxsize=MAX_PENDING_SURFACE_EVENTS
        )
        self.server = BrowserSurfaceServer(
            self._enqueue_event,
            host=host,
            port=port,
            asset_root=asset_root,
        )

    @property
    def local_url(self) -> str:
        return self.server.local_url

    def initialize(self) -> None:
        self.server.start()
        self.input_name = f"Browser controls ({self.server.actual_port})"
        self.output_name = f"Browser display ({self.server.actual_port})"

    def configure_lan(self, advertised_base_url: str) -> None:
        self.server.configure_lan(advertised_base_url)

    def create_pairing(self) -> dict[str, Any]:
        return self.server.create_pairing()

    def render(self, view: SurfaceView) -> None:
        self.server.broadcast_surface(surface_message(view, self.selector_capacity))

    def poll_events(self) -> list[SurfaceEvent]:
        events: list[SurfaceEvent] = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                return events

    def _enqueue_event(self, event: SurfaceEvent) -> None:
        try:
            self._events.put_nowait(event)
        except queue.Full:
            pass

    def close(self) -> None:
        self.server.close()


def _peer_host(remote_address: object) -> str:
    if isinstance(remote_address, tuple) and remote_address:
        return str(remote_address[0])
    return ""


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
