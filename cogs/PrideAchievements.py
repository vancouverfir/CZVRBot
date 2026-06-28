import json
import os
import random
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


PRIDE_CHANNEL_ID = int(os.getenv("PRIDE_CHANNEL_ID", "0"))
DATA_FILE = Path("pride_achievements.json")

RANDOM_ACHIEVEMENT_CHANCE = 0.15
USER_COOLDOWN_SECONDS = 90


ACHIEVEMENTS = {
    # Message count milestones
    "found_channel": {
        "name": "🌈 Achievement unlocked: You found the channel!",
        "description": "Welcome!"
    },
    "channel_sample": {
        "name": "🧪 Achievement unlocked: Channel sample",
        "description": "Five messages collected. Results inconclusive."
    },
    "still_here": {
        "name": "💬 Achievement unlocked: Still here",
        "description": "You really like this channel huh"
    },
    "regular": {
        "name": "🎟️ Achievement unlocked: Regular",
        "description": "Not saying you live here, but the evidence is building."
    },
    "furniture": {
        "name": "🪑 Achievement unlocked: Part of the furniture",
        "description": "At this point we might have to name a chair after you."
    },
    "had_something_to_say": {
        "name": "📣 Achievement unlocked: Had something to say",
        "description": "Several things, apparently."
    },
    "channel_lore": {
        "name": "📜 Achievement unlocked: Channel lore",
        "description": "This may or may not be referenced later."
    },
    "survived": {
        "name": "🫡 Achievement unlocked: Survived the channel",
        "description": "Another message, another day."
    },
    "pride_channel_legend": {
        "name": "🏆 Achievement unlocked: Pride channel legend",
        "description": "Honestly, at this point, fair enough."
    },

    # Random-only achievements
    "rainbow_sighting": {
        "name": "🌈 Achievement unlocked: Rainbow sighting",
        "description": "Nature is healing."
    },
    "perfect_timing": {
        "name": "⏰ Achievement unlocked: Perfect timing",
        "description": "No one knows why, but that landed."
    },
    "rare_drop": {
        "name": "✨ Achievement unlocked: Rare drop",
        "description": "This one does nothing. Treasure it."
    },
    "reasonable_take": {
        "name": "🧠 Achievement unlocked: Reasonable take",
        "description": "Bold move for Discord."
    },
    "the_channel_approves": {
        "name": "✅ Achievement unlocked: The channel approves",
        "description": "No further questions at this time."
    },
    "bold_of_you": {
        "name": "📌 Achievement unlocked: Bold of you",
        "description": "Posting on Discord. In this economy?"
    },
    "noted": {
        "name": "📝 Achievement unlocked: Noted",
        "description": "Filed away for no particular reason."
    },
    "tiny_victory": {
        "name": "🏅 Achievement unlocked: Tiny victory",
        "description": "Small win. Still counts."
    },
    "this_counts": {
        "name": "✅ Achievement unlocked: This counts",
        "description": "Against what? Unclear."
    },
    "main_character_for_now": {
        "name": "🎬 Achievement unlocked: Main character, briefly",
        "description": "Enjoy the next seven seconds."
    },
    "unexpected": {
        "name": "❗ Achievement unlocked: Unexpected",
        "description": "Nobody had this on the bingo card."
    },
    "not_a_phase": {
        "name": "🌈 Achievement unlocked: Not a phase",
        "description": "The channel, obviously."
    },
    "rainbow_admin": {
        "name": "📋 Achievement unlocked: Rainbow paperwork",
        "description": "The form was submitted incorrectly, but accepted anyway."
    },
    "acceptable_use": {
        "name": "✅ Achievement unlocked: Acceptable use",
        "description": "This appears to be what the channel is for."
    },
    "channel_activity": {
        "name": "📊 Achievement unlocked: Channel activity",
        "description": "The graph goes up slightly."
    },
    "minor_event": {
        "name": "🔔 Achievement unlocked: Minor event",
        "description": "A thing happened. We are all changed."
    },
    "no_context": {
        "name": "❔ Achievement unlocked: No context",
        "description": "Probably makes sense to someone."
    },
    "seen_and_logged": {
        "name": "👁️ Achievement unlocked: Seen and logged",
        "description": "Not suspiciously. Just normally."
    },
    "message_received": {
        "name": "📨 Achievement unlocked: Message received",
        "description": "Technically, that is how Discord works."
    },
    "good_enough": {
        "name": "👍 Achievement unlocked: Good enough",
        "description": "The official standard of most things."
    },
    "somehow_relevant": {
        "name": "🧩 Achievement unlocked: Somehow relevant",
        "description": "We’ll allow it."
    },
    "within_tolerance": {
        "name": "📏 Achievement unlocked: Within tolerance",
        "description": "Close enough for community work."
    },
    "harmless": {
        "name": "🕊️ Achievement unlocked: Harmless",
        "description": "Against all odds, nothing caught fire."
    },
    "all_welcome": {
        "name": "🌈 Achievement unlocked: All welcome",
        "description": "That is kind of the point."
    },
    "small_step": {
        "name": "👣 Achievement unlocked: Small step",
        "description": "Not dramatic. Still nice."
    },
}


MILESTONES = {
    1: "found_channel",
    5: "channel_sample",
    10: "still_here",
    25: "regular",
    50: "furniture",
    100: "had_something_to_say",
    250: "channel_lore",
    300: "survived",
    500: "pride_channel_legend",
}


RANDOM_POOL = [
    "rainbow_sighting",
    "perfect_timing",
    "rare_drop",
    "reasonable_take",
    "the_channel_approves",
    "bold_of_you",
    "noted",
    "tiny_victory",
    "this_counts",
    "main_character_for_now",
    "unexpected",
    "not_a_phase",
    "rainbow_admin",
    "acceptable_use",
    "channel_activity",
    "minor_event",
    "no_context",
    "seen_and_logged",
    "message_received",
    "good_enough",
    "somehow_relevant",
    "within_tolerance",
    "harmless",
    "all_welcome",
    "small_step",
]


class PrideAchievements(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.data = self.load_data()

    def load_data(self):
        if not DATA_FILE.exists():
            return {}

        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self):
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4)

    def get_user_data(self, user_id: int):
        user_id = str(user_id)

        if user_id not in self.data:
            self.data[user_id] = {
                "message_count": 0,
                "last_achievement_time": 0,
                "achievements": [],
            }

        return self.data[user_id]

    def has_achievement(self, user_data, achievement_id: str):
        return achievement_id in user_data.get("achievements", [])

    def on_cooldown(self, user_data):
        last_time = user_data.get("last_achievement_time", 0)
        return time.time() - last_time < USER_COOLDOWN_SECONDS

    def is_pride_channel_interaction(self, interaction: discord.Interaction):
        return PRIDE_CHANNEL_ID != 0 and interaction.channel_id == PRIDE_CHANNEL_ID

    def get_available_random_achievements(self, user_data):
        unlocked = set(user_data.get("achievements", []))

        return [
            achievement_id
            for achievement_id in RANDOM_POOL
            if achievement_id not in unlocked
        ]

    async def unlock_achievement(
        self,
        message: discord.Message,
        user_data: dict,
        achievement_id: str,
        ignore_cooldown: bool = False,
    ):
        if achievement_id not in ACHIEVEMENTS:
            return False

        if self.has_achievement(user_data, achievement_id):
            return False

        if not ignore_cooldown and self.on_cooldown(user_data):
            return False

        achievement = ACHIEVEMENTS[achievement_id]

        user_data["achievements"].append(achievement_id)
        user_data["last_achievement_time"] = time.time()
        self.save_data()

        await message.reply(
            f"{achievement['name']}\n*{achievement['description']}*",
            mention_author=False,
        )

        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if PRIDE_CHANNEL_ID == 0:
            return

        if message.channel.id != PRIDE_CHANNEL_ID:
            return

        user_data = self.get_user_data(message.author.id)
        user_data["message_count"] += 1
        message_count = user_data["message_count"]

        self.save_data()

        # Guaranteed count-based achievements.
        if message_count in MILESTONES:
            await self.unlock_achievement(
                message=message,
                user_data=user_data,
                achievement_id=MILESTONES[message_count],
                ignore_cooldown=True,
            )
            return

        # Random non-repeat achievements.
        available_random = self.get_available_random_achievements(user_data)

        if not available_random:
            return

        if self.on_cooldown(user_data):
            return

        if random.random() > RANDOM_ACHIEVEMENT_CHANCE:
            return

        achievement_id = random.choice(available_random)

        await self.unlock_achievement(
            message=message,
            user_data=user_data,
            achievement_id=achievement_id,
        )

    @app_commands.command(
        name="prideachievements",
        description="View your Pride channel achievements.",
    )
    async def prideachievements(self, interaction: discord.Interaction):
        if not self.is_pride_channel_interaction(interaction):
            await interaction.response.send_message(
                "This command only works in the Pride channel.",
                ephemeral=True,
            )
            return

        user_data = self.get_user_data(interaction.user.id)
        achievement_ids = user_data.get("achievements", [])

        if not achievement_ids:
            await interaction.response.send_message(
                "You do not have any Pride channel achievements yet.",
                ephemeral=True,
            )
            return

        lines = []

        for achievement_id in achievement_ids:
            achievement = ACHIEVEMENTS.get(achievement_id)

            if achievement:
                lines.append(f"- {achievement['name']}")

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Pride Achievements",
            description="\n".join(lines),
            colour=0x9B59B6,
        )

        embed.set_footer(
            text=f"{user_data['message_count']} messages counted in the Pride channel"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="pridestats",
        description="View your Pride channel message count.",
    )
    async def pridestats(self, interaction: discord.Interaction):
        if not self.is_pride_channel_interaction(interaction):
            await interaction.response.send_message(
                "This command only works in the Pride channel.",
                ephemeral=True,
            )
            return

        user_data = self.get_user_data(interaction.user.id)

        await interaction.response.send_message(
            f"You have sent **{user_data['message_count']}** messages in the Pride channel "
            f"and unlocked **{len(user_data['achievements'])}** achievements.",
            ephemeral=True,
        )


async def setup(client):
    await client.add_cog(PrideAchievements(client))
