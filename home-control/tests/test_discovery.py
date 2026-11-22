from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from home_control.discovery import DEFAULT_PROBE_PORTS, DEEP_PROBE_PORTS, discover
from home_control.models import Device


def _roku() -> Device:
    return Device(
        id="roku-10-0-0-5",
        name="Living Room",
        kind="tv",
        manufacturer="roku",
        model="8060",
        address="10.0.0.5",
        port=8060,
        protocol="roku",
        capabilities=["mute"],
    )


class DiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_scan_probes_tv_ports(self) -> None:
        with (
            patch("home_control.discovery._mdns", new_callable=AsyncMock, return_value=[]),
            patch("home_control.discovery._ssdp", return_value=[]),
            patch("home_control.discovery._port_sweep", new_callable=AsyncMock, return_value=[]) as sweep,
            patch("home_control.discovery._enrich_roku", new_callable=AsyncMock),
        ):
            await discover(timeout=0.05, deep=False)
        sweep.assert_awaited()
        ports = sweep.await_args.kwargs.get("ports") or (
            sweep.await_args.args[0] if sweep.await_args.args else None
        )
        self.assertIsNotNone(ports)
        self.assertIn(8060, ports)
        self.assertIn(8001, ports)
        self.assertIn(8008, ports)
        self.assertEqual(list(ports), list(DEFAULT_PROBE_PORTS))

    async def test_deep_scan_adds_switch_and_media_ports(self) -> None:
        with (
            patch("home_control.discovery._mdns", new_callable=AsyncMock, return_value=[]),
            patch("home_control.discovery._ssdp", return_value=[]),
            patch("home_control.discovery._port_sweep", new_callable=AsyncMock, return_value=[]) as sweep,
            patch("home_control.discovery._enrich_roku", new_callable=AsyncMock),
        ):
            await discover(timeout=0.05, deep=True)
        ports = sweep.await_args.kwargs.get("ports") or sweep.await_args.args[0]
        self.assertIn(9999, ports)
        self.assertIn(8123, ports)
        self.assertTrue(set(DEFAULT_PROBE_PORTS).issubset(set(ports)))
        self.assertEqual(set(ports), set(DEEP_PROBE_PORTS))

    async def test_mdns_crash_still_returns_port_hits(self) -> None:
        with (
            patch("home_control.discovery._mdns", new_callable=AsyncMock, side_effect=RuntimeError("mdns down")),
            patch("home_control.discovery._ssdp", return_value=[]),
            patch("home_control.discovery._port_sweep", new_callable=AsyncMock, return_value=[_roku()]),
            patch("home_control.discovery._enrich_roku", new_callable=AsyncMock),
        ):
            found = await discover(timeout=0.05, deep=False)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].protocol, "roku")


if __name__ == "__main__":
    unittest.main()
