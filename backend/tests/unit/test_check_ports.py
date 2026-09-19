"""
Unit tests for backend/check_ports.py pre-flight port verification.
Compatible with both pytest and python -m unittest.
"""

import errno
import os
import socket
import unittest
from check_ports import (
    DEFAULT_TARGETS,
    PortTarget,
    check_ports,
    probe_socket_bind,
    resolve_port,
)


class TestCheckPorts(unittest.TestCase):
    """Unit tests covering port resolution, socket probing, and collision handling."""

    def test_resolve_port_defaults(self):
        """Verify that default ports are returned when environment variables are unset."""
        for target in DEFAULT_TARGETS:
            self.assertEqual(resolve_port(target), target.default_port)

    def test_resolve_port_env_override(self):
        """Verify that environment variable overrides default port values."""
        target = PortTarget(
            name="Custom Service",
            default_port=9000,
            env_var_name="CUSTOM_PORT",
            description="Testing override",
        )
        os.environ["CUSTOM_PORT"] = "9999"
        try:
            self.assertEqual(resolve_port(target), 9999)
        finally:
            os.environ.pop("CUSTOM_PORT", None)

    def test_probe_socket_bind_available_port(self):
        """Verify that an unused high ephemeral port probe returns available."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", 0))
            _, free_port = s.getsockname()

        is_available, err_code, msg = probe_socket_bind("0.0.0.0", free_port)
        self.assertTrue(is_available)
        self.assertIsNone(err_code)
        self.assertIn("free and available", msg)

    def test_probe_socket_bind_detects_eaddrinuse(self):
        """Verify that an actively bound listening socket triggers EADDRINUSE detection."""
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("0.0.0.0", 0))
        listener.listen(1)
        _, bound_port = listener.getsockname()

        try:
            is_available, err_code, msg = probe_socket_bind("0.0.0.0", bound_port)
            self.assertFalse(is_available)
            self.assertEqual(err_code, errno.EADDRINUSE)
            self.assertIn("EADDRINUSE", msg)
        finally:
            listener.close()

    def test_check_ports_collision_aborts_all_clear(self):
        """Verify check_ports returns all_clear=False when a target port is occupied."""
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("0.0.0.0", 0))
        listener.listen(1)
        _, busy_port = listener.getsockname()

        try:
            mock_targets = [
                PortTarget("Busy Service", busy_port, "BUSY_PORT", "Collision test"),
            ]
            all_clear, results = check_ports(host="0.0.0.0", targets=mock_targets)
            self.assertFalse(all_clear)
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].is_available)
            self.assertEqual(results[0].errno_code, errno.EADDRINUSE)
        finally:
            listener.close()


if __name__ == "__main__":
    unittest.main()
