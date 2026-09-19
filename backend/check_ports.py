#!/usr/bin/env python3
"""
VoluMeal-Align Port Pre-flight Check & Isolation Guard.

Reference:
- Requirement Specification.md Section 3.3 (원격 자원 격리 원칙)
- Requirement Specification.md Section 10.3 (하드웨어 예외 처리 가이드라인)
- Requirement Specification.md Section 16 (Agent Instruction Configuration)

Ownership:
- 백엔드/인프라 담당 [고용민] (Developer 1, UID: 1001)

Purpose:
- Verifies that target services (Backend: 8001, PostgreSQL: 5432, Redis: 6379)
  can safely bind to host 0.0.0.0 without encountering EADDRINUSE collisions.
- Prevents port collisions between Developer 1 (8001/3001) and Developer 2 (8002/3002),
  as well as clashes with existing host daemons.
- Aborts immediately with exit code 1 if any target port is already occupied.
"""

from __future__ import annotations

import argparse
import errno
import os
from pathlib import Path
import socket
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple


def load_dotenv_defaults() -> None:
    """
    Loads environment variables from .env and .env.shared into os.environ
    if not already defined, ensuring pre-flight checks honor workspace configuration.
    """
    workspace_root = Path(__file__).resolve().parents[1]
    for env_name in (".env", ".env.shared", "backend/.env.goyongmin"):
        candidate = workspace_root / env_name
        if candidate.is_file():
            try:
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = val
            except OSError:
                continue


class PortTarget(NamedTuple):
    """Specification of a network service port to validate."""
    name: str
    default_port: int
    env_var_name: str
    description: str


# Default targets based on Requirement Specification Sections 1.4, 3.3, 10.3
DEFAULT_TARGETS: Tuple[PortTarget, ...] = (
    PortTarget(
        name="Backend API (FastAPI)",
        default_port=8001,
        env_var_name="PORT",
        description="Goyongmin isolated backend server",
    ),
    PortTarget(
        name="PostgreSQL Database",
        default_port=5432,
        env_var_name="POSTGRES_PORT",
        description="Shared transactional relational database",
    ),
    PortTarget(
        name="Redis Broker / Cache",
        default_port=6379,
        env_var_name="REDIS_PORT",
        description="Shared Celery task broker and distributed cache",
    ),
)


class PortCheckResult(NamedTuple):
    """Result of an individual socket bind probe."""
    target: PortTarget
    port: int
    is_available: bool
    errno_code: Optional[int]
    error_message: str


def resolve_port(target: PortTarget) -> int:
    """
    Resolves the port number for a given target, prioritizing environment variables
    before falling back to the specification default.
    """
    raw_val = os.getenv(target.env_var_name)
    if raw_val is not None and raw_val.strip().isdigit():
        return int(raw_val.strip())
    return target.default_port


def probe_socket_bind(host: str, port: int) -> Tuple[bool, Optional[int], str]:
    """
    Attempts to bind a TCP streaming socket to (host, port).

    Returns:
        (is_available, errno_code, message)
        - If available: (True, None, "Available for binding")
        - If occupied/error: (False, errno, description string)
    """
    probe_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Explicitly do NOT set SO_REUSEADDR or SO_REUSEPORT to strictly detect
        # active listeners and established bindings on 0.0.0.0.
        probe_socket.bind((host, port))
        return True, None, "Port is free and available for binding."
    except OSError as exc:
        err_code = exc.errno
        if err_code == errno.EADDRINUSE:
            error_desc = f"EADDRINUSE (Errno {err_code}): Address already in use on {host}:{port}"
        elif err_code == errno.EACCES:
            error_desc = f"EACCES (Errno {err_code}): Permission denied when binding to {host}:{port}"
        else:
            err_name = errno.errorcode.get(err_code, f"UNKNOWN_{err_code}")
            error_desc = f"{err_name} (Errno {err_code}): {exc.strerror or 'Failed to bind socket'}"
        return False, err_code, error_desc
    finally:
        probe_socket.close()


def check_ports(
    host: str = "0.0.0.0",
    targets: Optional[List[PortTarget]] = None,
    backend_only: bool = False,
) -> Tuple[bool, List[PortCheckResult]]:
    """
    Evaluates port occupancy across all specified service targets.

    Returns:
        (all_clear, results)
        - all_clear: True if every probed port is free; False if any conflict exists.
        - results: List of PortCheckResult instances detailing probe outcomes.
    """
    if targets is None:
        target_list = list(DEFAULT_TARGETS)
    else:
        target_list = list(targets)

    if backend_only:
        target_list = [t for t in target_list if t.name.startswith("Backend API")]

    results: List[PortCheckResult] = []
    all_clear = True

    for target in target_list:
        port = resolve_port(target)
        is_available, err_code, msg = probe_socket_bind(host, port)
        result = PortCheckResult(
            target=target,
            port=port,
            is_available=is_available,
            errno_code=err_code,
            error_message=msg,
        )
        results.append(result)
        if not is_available:
            all_clear = False

    return all_clear, results


def format_report(host: str, results: List[PortCheckResult]) -> str:
    """Formats human-readable diagnostic output for terminal display."""
    lines: List[str] = [
        "=" * 78,
        " VoluMeal-Align Port Isolation Pre-flight Check",
        f" Host Binding Target: {host} (Localhost binding strictly prohibited)",
        " Reference: Sections 3.3, 10.3, 16 [Owner: 고용민]",
        "=" * 78,
    ]

    conflicts: List[PortCheckResult] = []

    for res in results:
        status_tag = "[OK: FREE]    " if res.is_available else "[FAIL: IN USE]"
        lines.append(
            f" {status_tag} {res.target.name:<26} Port: {res.port:<5} -> {res.error_message}"
        )
        if not res.is_available:
            conflicts.append(res)

    lines.append("-" * 78)

    if not conflicts:
        lines.extend([
            " [SUCCESS] All verified ports are available and ready for binding.",
            " Safe to proceed with FastAPI and Docker container startup.",
            "=" * 78,
        ])
    else:
        lines.extend([
            f" [CRITICAL ERROR] Detected {len(conflicts)} port collision(s) on host {host}:",
        ])
        for conf in conflicts:
            lines.append(
                f"   * Port {conf.port} ({conf.target.name}): {conf.error_message}"
            )
        lines.extend([
            "",
            " Troubleshooting & Resolution Steps:",
            "   1. Identify occupying PID:",
            f"      ss -tulpn | grep -E '{'|'.join(str(c.port) for c in conflicts)}'",
            "      or: lsof -i -P -n | grep LISTEN",
            "   2. If a lingering Docker container or orphaned process is running, stop it:",
            "      docker compose down   # or: kill -15 <PID>",
            "   3. Verify that environment variables (.env) do not collide with another developer's port.",
            "   4. Rerun pre-flight check: python backend/check_ports.py",
            "=" * 78,
        ])

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments for port verification."""
    parser = argparse.ArgumentParser(
        description="VoluMeal-Align Pre-flight Port Occupancy Verification Guard"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host IP to test socket binding (default: 0.0.0.0 as required by remote spec)",
    )
    parser.add_argument(
        "--backend-port",
        type=int,
        default=None,
        help="Override Backend API port (default: 8001 or $PORT)",
    )
    parser.add_argument(
        "--postgres-port",
        type=int,
        default=None,
        help="Override PostgreSQL port (default: 5432 or $POSTGRES_PORT)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=None,
        help="Override Redis port (default: 6379 or $REDIS_PORT)",
    )
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Check only the backend port (useful when Postgres/Redis are already running in Docker)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress banner and report output, communicating result solely via exit code",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for CLI execution."""
    load_dotenv_defaults()
    args = parse_args()

    targets: List[PortTarget] = []
    backend_port = args.backend_port or resolve_port(DEFAULT_TARGETS[0])
    postgres_port = args.postgres_port or resolve_port(DEFAULT_TARGETS[1])
    redis_port = args.redis_port or resolve_port(DEFAULT_TARGETS[2])

    targets.append(
        PortTarget(
            name=DEFAULT_TARGETS[0].name,
            default_port=backend_port,
            env_var_name=DEFAULT_TARGETS[0].env_var_name,
            description=DEFAULT_TARGETS[0].description,
        )
    )

    if not args.backend_only:
        targets.append(
            PortTarget(
                name=DEFAULT_TARGETS[1].name,
                default_port=postgres_port,
                env_var_name=DEFAULT_TARGETS[1].env_var_name,
                description=DEFAULT_TARGETS[1].description,
            )
        )
        targets.append(
            PortTarget(
                name=DEFAULT_TARGETS[2].name,
                default_port=redis_port,
                env_var_name=DEFAULT_TARGETS[2].env_var_name,
                description=DEFAULT_TARGETS[2].description,
            )
        )

    all_clear, results = check_ports(
        host=args.host,
        targets=targets,
        backend_only=args.backend_only,
    )

    if not args.quiet:
        report = format_report(args.host, results)
        if all_clear:
            sys.stdout.write(report + "\n")
        else:
            sys.stderr.write(report + "\n")

    if not all_clear:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
