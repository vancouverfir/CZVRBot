import os
import asyncio
import aiohttp
import pymysql
import discord
import json
from datetime import datetime, timezone, timedelta
from discord.ext import commands, tasks
from discord import app_commands
from cogs.CustomLogging import log

DATA_FILE = "supervision_data.json"

class ATC(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.supervision_requests = self.load_data()
        self.booking_api_url = os.getenv('BOOKING-API-URL', 'https://atc-bookings.vatsim.net/api/booking')
        self.booking_api_key = os.getenv('BOOKING-API-KEY')
        self.booking_notification_channel = int(os.getenv('BOOKING-NOTIFICATION-CHANNEL', 0)) if os.getenv('BOOKING-NOTIFICATION-CHANNEL') else 0
        self.supervision_channel = int(os.getenv('SUPERVISION-REQUEST-CHANNEL', 0)) if os.getenv('SUPERVISION-REQUEST-CHANNEL') else 0

        self.conn = pymysql.connect(
            host=os.getenv("DB-HOST"),
            user=os.getenv("DB-USER"),
            password=os.getenv("DB-PASS"),
            port=int(os.getenv("DB-PORT")),
            database=os.getenv("DB-NAME"),
            cursorclass=pymysql.cursors.DictCursor
        )

        self.cleanup_supervision_messages.start()

    def cog_unload(self):
        self.cleanup_supervision_messages.cancel()

    def ensure_conn(self):
        try:
            self.conn.ping(reconnect=True)
        except Exception:
            self.conn = pymysql.connect(
                host=os.getenv("DB-HOST"),
                user=os.getenv("DB-USER"),
                password=os.getenv("DB-PASS"),
                port=int(os.getenv("DB-PORT")),
                database=os.getenv("DB-NAME"),
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        return self.conn

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                log(f"Error loading JSON: {e}", "error")
                return {}
        return {}

    def save_data(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(self.supervision_requests, f, indent=4)
        except Exception as e:
            log(f"Error saving JSON: {e}", "error")

    def get_user_cid(self, discord_user_id):
        try:
            conn = self.ensure_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE discord_user_id=%s", (discord_user_id,))
                row = cur.fetchone()
                return row["id"] if row else None
        except Exception as e:
            log(f"Error fetching CID for user {discord_user_id}: {e}", "error")
            return None

    def parse_booking_times(self, start_time, end_time):
        current_year = datetime.now(timezone.utc).year
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        try:
            start_dt = datetime.strptime(f"{current_year}-{start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{current_year}-{end_time}", "%Y-%m-%d %H:%M")

            if start_dt < now:
                start_dt = start_dt.replace(year=current_year + 1)
                end_dt = end_dt.replace(year=current_year + 1)

            return start_dt, end_dt
        except ValueError:
            return None, None

    def booking_overlaps_wcw_event(self, start_dt, end_dt):
        try:
            conn = self.ensure_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM events
                    WHERE LOWER(name) LIKE %s
                    AND start_timestamp < %s
                    AND end_timestamp > %s
                    LIMIT 1
                    """,
                    ("%west coast weekend%", end_dt, start_dt)
                )
                return cur.fetchone() is not None
        except Exception as e:
            log(f"Error checking West Coast Weekend event overlap: {e}", "error")
            return None

    def validate_booking_rules(self, start_dt, end_dt, enforce_advance=True):
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if end_dt <= start_dt:
            return "❌ Booking end time must be after the start time."

        duration = end_dt - start_dt

        if duration < timedelta(minutes=45):
            return "❌ Your booking cannot be less than 45 minutes."

        if enforce_advance and start_dt - now < timedelta(hours=4):
            return "❌ Bookings must be created at least 4 hours in advance."

        overlaps_wcw = self.booking_overlaps_wcw_event(start_dt, end_dt)

        if overlaps_wcw is None:
            return "❌ Could not validate event booking rules. Please try again later."

        max_duration = timedelta(hours=2 if overlaps_wcw else 4)

        if duration > max_duration:
            if overlaps_wcw:
                return "❌ Reserved bookings during West Coast Weekend cannot be longer than 2 hours."
            return "❌ Reserved bookings cannot be longer than 4 hours."

        return None

    @tasks.loop(minutes=5)
    async def cleanup_supervision_messages(self):
        now = datetime.now(timezone.utc)
        to_remove = []
        channel = self.client.get_channel(self.supervision_channel)

        if not channel:
            return

        for msg_id_str, data in list(self.supervision_requests.items()):
            try:
                start_clean = data["start_time"].replace("Z", "")
                end_clean = data["end_time"].replace("Z", "")

                start_dt = datetime.strptime(start_clean, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                end_dt = datetime.strptime(end_clean, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)

                status = data.get("status", "pending")

                if (status == "pending" and now >= start_dt) or (status in ("accepted", "accepted_manual") and now >= end_dt) or status == "expired":
                    try:
                        msg = await channel.fetch_message(int(msg_id_str))
                        await msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass

                    to_remove.append(msg_id_str)

            except Exception as e:
                log(f"Cleanup error for msg {msg_id_str}: {e}", "error")

        if to_remove:
            for mid in to_remove:
                self.supervision_requests.pop(mid, None)
            self.save_data()

    @app_commands.command(name="create_booking", description="Create an ATC booking")
    @app_commands.describe(position="Position (e.g., CZVR_CTR)", start_time="MM-DD HH:MM", end_time="MM-DD HH:MM")
    async def make_booking(self, interaction: discord.Interaction, position: str, start_time: str, end_time: str):
        cid = self.get_user_cid(interaction.user.id)
        if not cid:
            await interaction.response.send_message("❌ CID not found in database!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        start_dt, end_dt = self.parse_booking_times(start_time, end_time)
        if not start_dt or not end_dt:
            await interaction.followup.send("❌ Use format: `MM-DD HH:MM` (e.g., 01-01 11:15)", ephemeral=True)
            return

        validation_error = self.validate_booking_rules(start_dt, end_dt)
        if validation_error:
            await interaction.followup.send(validation_error, ephemeral=True)
            return

        headers = {'Authorization': f'Bearer {self.booking_api_key}'}
        data = {
            'callsign': position.upper(),
            'cid': cid,
            'type': 'booking',
            'start': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'end': end_dt.strftime('%Y-%m-%d %H:%M:%S'),
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.booking_api_url, json=data, headers=headers) as resp:
                if resp.ok:
                    await interaction.followup.send(f"✅ Booking created for **{position.upper()}**!", ephemeral=True)
                else:
                    error_text = await resp.text()
                    await interaction.followup.send(f"❌ API Error: {error_text[:200]}", ephemeral=True)

    @app_commands.command(name="cancel_booking", description="Cancel one of your active VATSIM ATC bookings")
    async def cancel_booking(self, interaction: discord.Interaction):
        cid = self.get_user_cid(interaction.user.id)
        if not cid:
            await interaction.response.send_message("❌ CID not found!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        headers = {'Authorization': f'Bearer {self.booking_api_key}', 'Accept': 'application/json'}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.booking_api_url}?cid={cid}", headers=headers) as resp:
                if resp.ok:
                    bookings = await resp.json()
                    if not bookings:
                        await interaction.followup.send("No active bookings found!", ephemeral=True)
                        return

                    view = CancelBookingView(bookings, self.booking_api_url, self.booking_api_key, interaction.user)
                    await interaction.followup.send("Select a booking to cancel:", view=view, ephemeral=True)
                else:
                    await interaction.followup.send("❌ Error fetching bookings from API!", ephemeral=True)

    @app_commands.command(name="supervision_request", description="Command to request supervision")
    @app_commands.describe(position="Position (e.g., CZVR_CTR)", start_time="MM-DD HH:MM", end_time="MM-DD HH:MM")
    async def supervision_request(self, interaction: discord.Interaction, position: str, start_time: str, end_time: str):
        position = position.upper()

        start_dt, end_dt = self.parse_booking_times(start_time, end_time)
        if not start_dt or not end_dt:
            await interaction.response.send_message("❌ Format: `MM-DD HH:MM` (e.g., 05-20 18:00)", ephemeral=True)
            return

        validation_error = self.validate_booking_rules(start_dt, end_dt, enforce_advance=False)
        if validation_error:
            await interaction.response.send_message(validation_error, ephemeral=True)
            return

        start_str_z = start_dt.strftime('%Y-%m-%d %H:%MZ')
        end_str_z = end_dt.strftime('%Y-%m-%d %H:%MZ')

        clean_start = start_str_z[5:]
        clean_end = end_str_z[5:]
        ts_start = int(start_dt.timestamp())

        embed = discord.Embed(title="Supervision Request", color=0x800080, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Controller", value=interaction.user.mention, inline=True)
        embed.add_field(name="Position", value=f"`{position}`", inline=True)

        embed.add_field(
            name="Start Time",
            value=f"`{clean_start}` (<t:{ts_start}:F>)",
            inline=False
        )
        embed.add_field(
            name="End Time",
            value=f"`{clean_end}`",
            inline=False
        )
        embed.add_field(name="Status", value="Pending", inline=False)

        channel = self.client.get_channel(self.supervision_channel)
        if not channel:
            await interaction.response.send_message("❌ Supervision channel not configured!", ephemeral=True)
            return

        try:
            view = SupervisionRequestView(self, interaction.user.id, position, start_str_z, end_str_z)
            message = await channel.send(embed=embed, view=view)
            view.message = message

            self.supervision_requests[str(message.id)] = {
                'user_id': interaction.user.id,
                'position': position,
                'start_time': start_str_z,
                'end_time': end_str_z,
                'status': 'pending'
            }
            self.save_data()

            await interaction.response.send_message("✅ Supervision request submitted!", ephemeral=True)
        except Exception as e:
            log(f"Failed to send request: {e}", "error")
            await interaction.response.send_message("❌ Error sending request!", ephemeral=True)

    @app_commands.command(name="cancel_supervision_request", description="Cancel your last supervision request")
    async def cancel_supervision(self, interaction: discord.Interaction):
        target_msg_id = None
        for msg_id, data in self.supervision_requests.items():
            if data['user_id'] == interaction.user.id and data['status'] == 'pending':
                target_msg_id = msg_id
                break

        if not target_msg_id:
            await interaction.response.send_message("❌ You have no pending requests to cancel!", ephemeral=True)
            return

        try:
            channel = self.client.get_channel(self.supervision_channel)
            if channel:
                try:
                    msg = await channel.fetch_message(int(target_msg_id))
                    await msg.delete()
                except discord.NotFound:
                    pass

            del self.supervision_requests[target_msg_id]
            self.save_data()
            await interaction.response.send_message("✅ Request cancelled and removed!", ephemeral=True)
        except Exception as e:
            log(f"Cancel error: {e}", "error")
            await interaction.response.send_message("❌ Failed to remove the request!", ephemeral=True)

class CancelBookingSelect(discord.ui.Select):
    def __init__(self, bookings, api_url, api_key, requesting_user):
        options = []
        for b in bookings[:25]:
            raw_start = b.get('start', 'Unknown')

            try:
                formatted_start = raw_start[5:16]
            except:
                formatted_start = raw_start

            options.append(
                discord.SelectOption(
                    label=f"{b.get('callsign')}",
                    value=str(b.get('id')),
                    description=f"Starts: `{formatted_start}`"
                )
            )

        super().__init__(placeholder="Choose a booking to remove...", options=options)
        self.api_url = api_url
        self.api_key = api_key

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        headers = {'Authorization': f'Bearer {self.api_key}'}
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{self.api_url}/{self.values[0]}", headers=headers) as resp:
                if resp.ok:
                    await interaction.followup.send("✅ Booking cancelled!", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Error: API rejected the cancellation.", ephemeral=True)

        for item in self.view.children:
            item.disabled = True
        await interaction.edit_original_response(view=self.view)

class CancelBookingView(discord.ui.View):
    def __init__(self, bookings, api_url, api_key, user):
        super().__init__(timeout=120)
        self.add_item(CancelBookingSelect(bookings, api_url, api_key, user))

class SupervisionRequestView(discord.ui.View):
    def __init__(self, cog, user_id, position, start_time, end_time):
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id
        self.position = position
        self.start_time = start_time
        self.end_time = end_time
        self.message = None

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        mentor_role = int(os.getenv('MENTOR-ROLE', 0))
        inst_role = int(os.getenv('INSTRUCTOR-ROLE', 0))
        user_roles = [r.id for r in interaction.user.roles]

        if mentor_role not in user_roles and inst_role not in user_roles:
            await interaction.response.send_message("❌ Only Mentors or Instructors can accept!", ephemeral=True)
            return

        s_time = self.start_time.replace('Z', '')
        e_time = self.end_time.replace('Z', '')
        start_dt = datetime.strptime(s_time, '%Y-%m-%d %H:%M')
        end_dt = datetime.strptime(e_time, '%Y-%m-%d %H:%M')

        msg_id_str = str(interaction.message.id)

        if datetime.now(timezone.utc).replace(tzinfo=None) >= start_dt:
            if msg_id_str in self.cog.supervision_requests:
                del self.cog.supervision_requests[msg_id_str]
                self.cog.save_data()

            await interaction.message.delete()
            await interaction.response.send_message("❌ This supervision request has expired.", ephemeral=True)
            return

        validation_error = self.cog.validate_booking_rules(start_dt, end_dt, enforce_advance=False)
        if validation_error:
            await interaction.response.send_message(validation_error, ephemeral=True)
            return

        await interaction.response.defer()

        cid = self.cog.get_user_cid(self.user_id)
        api_success = False

        if cid:
            headers = {'Authorization': f'Bearer {self.cog.booking_api_key}'}

            payload = {
                'callsign': self.position.upper(),
                'cid': cid,
                'type': 'booking',
                'start': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'end': end_dt.strftime('%Y-%m-%d %H:%M:%S'),
            }

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(self.cog.booking_api_url, json=payload, headers=headers) as resp:
                        if resp.ok:
                            api_success = True
                        else:
                            err = await resp.text()
                            log(f"API Error: {err}", "error")
                except Exception as e:
                    log(f"Connection error: {e}", "error")

        embed = interaction.message.embeds[0]

        if api_success:
            embed.color = 0x00ff00
            status_text = f"✅ Accepted & Booked by {interaction.user.mention}"
            if msg_id_str in self.cog.supervision_requests:
                self.cog.supervision_requests[msg_id_str]['status'] = 'accepted'
        else:
            embed.color = 0x800080
            status_text = f"❗ Accepted by {interaction.user.mention} (API Failed)"
            if msg_id_str in self.cog.supervision_requests:
                self.cog.supervision_requests[msg_id_str]['status'] = 'accepted_manual'

        for i, field in enumerate(embed.fields):
            if field.name == "Status":
                embed.set_field_at(i, name="Status", value=status_text, inline=False)

        self.cog.save_data()
        await interaction.edit_original_response(embed=embed, view=None)

        user = interaction.guild.get_member(self.user_id)
        if user:
            try:
                await user.send(
                    f"✅ Your supervision for **{self.position}** was accepted by {interaction.user.mention}!"
                )
            except discord.Forbidden:
                log(f"Could not DM user {self.user_id} (DMs off).", "warning")
            except Exception as e:
                log(f"DM Error: {e}", "error")
        self.stop()

async def setup(client):
    await client.add_cog(ATC(client))
