"""Unit tests for connection.py — frame encoding/decoding and response normalization."""

import json
import struct
import pytest
from unittest.mock import MagicMock

from ue_bridge.connection import Connection, MAX_MESSAGE_SIZE
from ue_bridge.errors import UEConnectionError


class TestFrameEncoding:
    """Test the length-prefixed frame protocol."""

    def test_send_raw_encodes_correctly(self):
        """Verify 4-byte big-endian length prefix + UTF-8 JSON."""
        conn = Connection(auto_connect=False) if hasattr(Connection.__init__, 'auto_connect') else Connection.__new__(Connection)
        conn.host = "127.0.0.1"
        conn.port = 55558
        conn.timeout = 30.0

        mock_socket = MagicMock()
        conn._socket = mock_socket

        data = {"type": "ping"}
        conn._send_raw(data)

        # Check what was sent
        calls = mock_socket.sendall.call_args_list
        assert len(calls) == 2

        # First call: 4-byte length prefix
        length_bytes = calls[0][0][0]
        assert len(length_bytes) == 4

        # Second call: JSON payload
        payload = calls[1][0][0]
        expected_json = json.dumps(data).encode("utf-8")
        assert payload == expected_json

        # Length prefix matches payload length
        expected_length = struct.pack(">I", len(expected_json))
        assert length_bytes == expected_length

    def test_send_raw_raises_when_not_connected(self):
        conn = Connection.__new__(Connection)
        conn._socket = None
        with pytest.raises(UEConnectionError):
            conn._send_raw({"type": "ping"})


class TestResponseNormalization:
    """Test _normalize_response handles both formats."""

    def setup_method(self):
        self.conn = Connection.__new__(Connection)
        self.conn.host = "127.0.0.1"
        self.conn.port = 55558
        self.conn.timeout = 30.0
        self.conn._socket = None

    def test_format1_success(self):
        response = {"success": True, "node_id": "abc123", "name": "test"}
        result = self.conn._normalize_response(response)
        assert result["success"] is True
        assert result["node_id"] == "abc123"

    def test_format1_failure(self):
        response = {"success": False, "error": "not found", "error_type": "not_found"}
        result = self.conn._normalize_response(response)
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_format2_success(self):
        response = {"status": "success", "result": {"data": 42}}
        result = self.conn._normalize_response(response)
        assert result["success"] is True
        assert result["data"] == 42

    def test_format2_failure(self):
        response = {"status": "error", "error": "bad request"}
        result = self.conn._normalize_response(response)
        assert result["success"] is False
        assert "bad request" in result["error"]

    def test_unknown_format(self):
        response = {"foo": "bar"}
        result = self.conn._normalize_response(response)
        assert result["success"] is False
        assert "Unknown response format" in result["error"]


class TestRecvExact:
    """Test _recv_exact handles partial reads."""

    def setup_method(self):
        self.conn = Connection.__new__(Connection)
        self.conn.host = "127.0.0.1"
        self.conn.port = 55558
        self.conn.timeout = 30.0

    def test_receives_in_chunks(self):
        mock_socket = MagicMock()
        # Simulate data arriving in 3 chunks
        mock_socket.recv.side_effect = [b"hel", b"lo", b" "]
        self.conn._socket = mock_socket

        result = self.conn._recv_exact(6)
        assert result == b"hello "

    def test_returns_none_on_empty_recv(self):
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b""  # Connection closed
        self.conn._socket = mock_socket

        result = self.conn._recv_exact(4)
        assert result is None

    def test_returns_none_when_not_connected(self):
        self.conn._socket = None
        result = self.conn._recv_exact(4)
        assert result is None


class TestConnectionContract:
    def test_send_command_auto_connects(self):
        conn = Connection.__new__(Connection)
        conn.host = "127.0.0.1"
        conn.port = 55558
        conn.timeout = 30.0
        conn._socket = None

        conn.connect = MagicMock(side_effect=lambda: setattr(conn, "_socket", MagicMock()))
        conn._send_raw = MagicMock()
        conn._receive_raw = MagicMock(return_value={"success": True, "pong": True})

        result = conn.send_command("ping")

        conn.connect.assert_called_once()
        assert result == {"success": True, "pong": True}

    def test_receive_raw_rejects_too_large_messages(self):
        conn = Connection.__new__(Connection)
        conn.host = "127.0.0.1"
        conn.port = 55558
        conn.timeout = 30.0
        conn._socket = MagicMock()
        conn._recv_exact = MagicMock(return_value=(MAX_MESSAGE_SIZE + 1).to_bytes(4, byteorder="big"))

        result = conn._receive_raw()

        assert result is None
