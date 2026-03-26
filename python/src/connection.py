"""
TCP connection to Unreal Editor's MCP Bridge plugin.

Protocol: 4-byte big-endian length prefix + UTF-8 JSON payload.
Default endpoint: 127.0.0.1:55558.

Adapted from UEEditorMCP/Python/ue_editor_mcp/connection.py.
Simplified: no heartbeat thread (library is used in short-lived scripts),
but keeps persistent connection, auto-reconnect, and context manager.
"""
from __future__ import annotations

import json
import socket
import logging
from typing import Any

from .errors import UEConnectionError

logger = logging.getLogger(__name__)

MAX_MESSAGE_SIZE = 100 * 1024 * 1024  # 100 MB


class Connection:
    """Persistent TCP connection to UE Editor plugin."""

    def __init__(self, host: str = "127.0.0.1", port: int = 55558,
                 timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket: socket.socket | None = None

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        if self._socket is not None:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            self._socket = sock
            logger.info(f"Connected to UE at {self.host}:{self.port}")
        except (socket.error, socket.timeout, ConnectionRefusedError) as e:
            raise UEConnectionError(
                f"Cannot connect to Unreal Editor at {self.host}:{self.port}. "
                f"Is the editor running with UEEditorMCP plugin enabled? Error: {e}"
            ) from e

    def disconnect(self) -> None:
        if self._socket is None:
            return
        try:
            self._send_raw({"type": "close"})
        except Exception:
            pass
        try:
            self._socket.close()
        except Exception:
            pass
        self._socket = None
        logger.info("Disconnected from UE")

    def send_command(self, command_type: str,
                     params: dict[str, Any] | None = None) -> dict:
        """
        Send a command and return the response data dict.

        Raises UEConnectionError on connection failure.
        Returns the raw response dict (always has 'success' key).
        """
        self._ensure_connected()

        command: dict[str, Any] = {"type": command_type}
        if params:
            command["params"] = params

        try:
            self._send_raw(command)
            response = self._receive_raw()
        except (socket.error, BrokenPipeError, ConnectionResetError) as e:
            self._socket = None
            raise UEConnectionError(f"Connection lost during '{command_type}': {e}") from e

        if response is None:
            self._socket = None
            raise UEConnectionError(
                f"No response from UE for '{command_type}'. Connection may have dropped."
            )

        return self._normalize_response(response)

    def _ensure_connected(self) -> None:
        if self._socket is None:
            self.connect()

    def _normalize_response(self, response: dict) -> dict:
        """Normalize both response formats into {success, ...data} or {success, error}."""
        # Format 1: {"success": true/false, ...}
        if "success" in response:
            return response

        # Format 2 (legacy): {"status": "success", "result": {...}}
        if "status" in response:
            if response["status"] == "success":
                result = response.get("result", {})
                return {"success": True, **result}
            else:
                return {
                    "success": False,
                    "error": response.get("error", "Unknown error"),
                    "error_type": response.get("error_type", "unknown"),
                }

        # Unknown format
        return {"success": False, "error": f"Unknown response format: {json.dumps(response)[:200]}"}

    def _send_raw(self, data: dict) -> None:
        if self._socket is None:
            raise UEConnectionError("Not connected")
        message = json.dumps(data).encode("utf-8")
        length = len(message)
        self._socket.sendall(length.to_bytes(4, byteorder="big"))
        self._socket.sendall(message)

    def _receive_raw(self) -> dict | None:
        if self._socket is None:
            return None
        try:
            length_bytes = self._recv_exact(4)
            if not length_bytes:
                return None
            length = int.from_bytes(length_bytes, byteorder="big")
            if length <= 0 or length > MAX_MESSAGE_SIZE:
                logger.error(f"Invalid message length: {length}")
                return None
            message_bytes = self._recv_exact(length)
            if not message_bytes:
                return None
            return json.loads(message_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse response: {e}")
            return None

    def _recv_exact(self, num_bytes: int) -> bytes | None:
        if self._socket is None:
            return None
        data = bytearray()
        while len(data) < num_bytes:
            try:
                chunk = self._socket.recv(num_bytes - len(data))
                if not chunk:
                    return None
                data.extend(chunk)
            except (socket.timeout, socket.error):
                return None
        return bytes(data)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
