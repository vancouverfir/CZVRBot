import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord

from cogs.ChannelDisplays import ChannelDisplays, FIVE_MINUTE_BOUNDARIES


class ChannelDisplayCogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = Mock()
        self.cog = ChannelDisplays(self.client)

    def test_clock_schedule_uses_utc_five_minute_boundaries(self):
        self.assertEqual(len(FIVE_MINUTE_BOUNDARIES), 288)
        self.assertTrue(all(value.minute % 5 == 0 for value in FIVE_MINUTE_BOUNDARIES))
        self.assertTrue(all(value.tzinfo is not None for value in FIVE_MINUTE_BOUNDARIES))

    async def test_matching_channel_name_is_not_edited(self):
        channel = SimpleNamespace(
            name="UTC Live Time: 22:45",
            edit=AsyncMock(),
        )
        self.client.get_channel.return_value = channel

        await self.cog.update_channel_name(1, "UTC Live Time: 22:45")

        channel.edit.assert_not_awaited()

    async def test_http_error_does_not_escape_update(self):
        response = SimpleNamespace(status=503, reason="Service Unavailable")
        channel = SimpleNamespace(
            name="old name",
            edit=AsyncMock(side_effect=discord.HTTPException(response, "temporary")),
        )
        self.client.get_channel.return_value = channel

        await self.cog.update_channel_name(1, "new name")

        channel.edit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
