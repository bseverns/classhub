"""Connectivity utilities for Tailnet-aware healthchecks."""

from __future__ import annotations

import logging
import subprocess
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


def is_tailnet_peer_reachable(base_url: str) -> bool:
    """
    Check if the target host in base_url is a reachable Tailnet peer.
    Uses 'tailscale status' under the hood.
    """
    host = (urlsplit(base_url).hostname or "").strip().lower()
    if not host or host in {"localhost", "127.0.0.1", "ollama"}:
        return True

    try:
        # Check if tailscale command exists
        # We use --json for machine-parsable output
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("tailscale_status_command_failed")
            return False

        import json

        data = json.loads(result.stdout)
        peers = data.get("Peer", {})

        # Check if the host matches any peer IP or DNS name
        for peer_id, peer_data in peers.items():
            if host in peer_data.get("TailscaleIPs", []):
                return peer_data.get("Active", False)
            if host == peer_data.get("DNSName", "").rstrip("."):
                return peer_data.get("Active", False)

        logger.info(f"host_{host}_not_found_in_tailnet_peers")
        return False

    except Exception as exc:
        logger.error(f"tailnet_connectivity_check_failed: {exc}")
        return False


def get_tailnet_diagnostics(base_url: str) -> dict[str, object]:
    """
    Return more detailed diagnostics for a tailnet path.
    """
    host = (urlsplit(base_url).hostname or "").strip().lower()
    reachable = is_tailnet_peer_reachable(base_url)
    
    return {
        "host": host,
        "tailnet_reachable": reachable,
        "mode": "distributed_mesh" if not reachable else "connected",
    }
