import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from channel_displays import (
    home_controller_count,
    utc_channel_name,
    vancouver_channel_name,
)


class ChannelDisplayFormattingTests(unittest.TestCase):
    def test_utc_formatting(self):
        now = datetime(2026, 7, 15, 22, 45, tzinfo=timezone.utc)
        self.assertEqual(utc_channel_name(now), "UTC Live Time: 22:45")

    def test_vancouver_daylight_time(self):
        now = datetime(2026, 7, 15, 22, 45, tzinfo=timezone.utc)
        self.assertEqual(
            vancouver_channel_name(now),
            "PDT Live Time (UTC-7): 15:45",
        )

    def test_vancouver_standard_time(self):
        now = datetime(2026, 1, 15, 22, 45, tzinfo=timezone.utc)
        self.assertEqual(
            vancouver_channel_name(now),
            "PST Live Time (UTC-8): 14:45",
        )

    def test_home_controller_count(self):
        role = lambda role_id: SimpleNamespace(id=role_id)
        members = [
            SimpleNamespace(roles=[role(1), role(720782657516077126)]),
            SimpleNamespace(roles=[role(2)]),
            SimpleNamespace(roles=[role(720782657516077126)]),
        ]
        self.assertEqual(home_controller_count(members, 720782657516077126), 2)


if __name__ == "__main__":
    unittest.main()
