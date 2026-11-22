from __future__ import annotations

import unittest

from home_control.net import classify_record, is_private_ip, looks_like_cloud_lan


class NetTests(unittest.TestCase):
    def test_private_ranges(self) -> None:
        self.assertTrue(is_private_ip("192.168.1.20"))
        self.assertTrue(is_private_ip("10.0.0.8"))
        self.assertTrue(is_private_ip("172.16.4.4"))
        self.assertTrue(is_private_ip("127.0.0.1"))
        self.assertFalse(is_private_ip("8.8.8.8"))
        self.assertFalse(is_private_ip("1.1.1.1"))

    def test_cloud_lan(self) -> None:
        self.assertTrue(looks_like_cloud_lan("172.30.0.2"))
        self.assertFalse(looks_like_cloud_lan("192.168.1.20"))

    def test_rejects_garbage(self) -> None:
        self.assertFalse(is_private_ip("not-an-ip"))
        self.assertFalse(is_private_ip(""))

    def test_classify_roku(self) -> None:
        kind, protocol = classify_record(
            name="Living Room",
            services=["roku:ecp"],
            ports=[8060],
        )
        self.assertEqual(kind, "tv")
        self.assertEqual(protocol, "roku")

    def test_classify_chromecast(self) -> None:
        kind, protocol = classify_record(
            name="Office TV",
            services=["_googlecast._tcp.local."],
            ports=[8009],
        )
        self.assertEqual(kind, "tv")
        self.assertEqual(protocol, "cast")

    def test_classify_sonos(self) -> None:
        kind, protocol = classify_record(
            name="Kitchen",
            services=["_sonos._tcp.local."],
            ports=[1400],
        )
        self.assertEqual(kind, "speaker")
        self.assertEqual(protocol, "sonos")

    def test_classify_kasa(self) -> None:
        kind, protocol = classify_record(
            name="HS103",
            services=[],
            ports=[9999],
            extra="TP-LINK kasa",
        )
        self.assertEqual(kind, "plug")
        self.assertEqual(protocol, "kasa")

    def test_classify_printer(self) -> None:
        kind, protocol = classify_record(
            name="Office Printer",
            services=["_ipp._tcp.local."],
            ports=[631],
        )
        self.assertEqual(kind, "printer")
        self.assertEqual(protocol, "ipp")


if __name__ == "__main__":
    unittest.main()
