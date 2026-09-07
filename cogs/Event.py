import os

import json
from datetime import datetime, timedelta
import pymysql
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View, Button, Modal, TextInput

from cogs.CustomLogging import log

EVENT_ROLE_ID = int(os.getenv('EVENT_ROLE_ID'))
EVENT_PING_ID = int(os.getenv('EVENT_PING_ID'))
EVENT_CHANNELS_FILE = "event_channels.json"


def load_event_channels():
    if not os.path.exists(EVENT_CHANNELS_FILE):
        return {}
    with open(EVENT_CHANNELS_FILE, "r") as f:
        return json.load(f)


def save_event_channels(data):
    with open(EVENT_CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def cleanup_expired_event_channels(conn):
    data = load_event_channels()
    if not data:
        return
    cleaned = {}
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        for channel_id, event_id in data.items():
            cur.execute("SELECT end_timestamp FROM events WHERE id=%s", (event_id,))
            row = cur.fetchone()
            if not row:
                continue
            end_ts = row["end_timestamp"]
            if isinstance(end_ts, str):
                end_ts = datetime.strptime(end_ts, "%Y-%m-%d %H:%M:%S")
            if end_ts > datetime.utcnow():
                cleaned[channel_id] = event_id
    if cleaned != data:
        save_event_channels(cleaned)


class Event(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.conn = pymysql.connect(
            host=os.getenv("DB-HOST"),
            user=os.getenv("DB-USER"),
            password=os.getenv("DB-PASS"),
            port=int(os.getenv("DB-PORT")),
            database=os.getenv("DB-NAME"),
            cursorclass=pymysql.cursors.DictCursor
        )
        cleanup_expired_event_channels(self.conn)

    # -------------------------
    # DB Helpers
    # -------------------------
    def db_query(self, sql, params=None):
        conn = self.ensure_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def db_exec(self, sql, params=None):
        conn = self.ensure_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)

    def db_one(self, sql, params=None):
        rows = self.db_query(sql, params)
        return rows[0] if rows else None

    def ensure_conn(self):
        try:
            self.ensure_conn().ping(reconnect=True)
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


    # -------------------------
    # Compact UI / Embed factories
    # -------------------------
    def _view_from_items(self, items, timeout=None):
        v = View(timeout=timeout)
        for label, style, cid in items:
            v.add_item(Button(label=label, style=style, custom_id=cid))
        return v

    def make_team_buttons(self):
        return self._view_from_items([
            ("Open Bookings", discord.ButtonStyle.success, "open_bookings"),
            ("Close Bookings", discord.ButtonStyle.danger, "close_bookings"),
            ("Applicants", discord.ButtonStyle.primary, "applicants"),
            ("Confirmed", discord.ButtonStyle.primary, "confirmed"),
            ("Positions", discord.ButtonStyle.primary, "positions"),
            ("Manual Add", discord.ButtonStyle.success, "manual_add"),
        ])

    def make_public_view(self):
        return self._view_from_items([
            ("Sign Up", discord.ButtonStyle.primary, "public_signup"),
            ("View Available Positions", discord.ButtonStyle.success, "public_positions")
        ])


    def build_embed(self, title=None, description=None, color=0x3498db, fields=None, image=None):
        e = discord.Embed(title=title or "", description=description or "", color=color)
        if fields:
            for name, value in fields:
                e.add_field(name=name, value=value, inline=False)
        if image:
            e.set_image(url=image)
        return e

    def embed_event(self, event_row):
        return self.build_embed(
            title=event_row["name"],
            description=event_row.get("description") or "No description available!",
            color=0x3498db,
            fields=[
                ("Start", str(event_row["start_timestamp"])),
                ("End", str(event_row["end_timestamp"]))
            ],
            image=event_row.get("image_url")
        )

    async def safe_send(self, interaction: discord.Interaction, content=None, **kwargs):
        """Send a response safely (response or followup)"""
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(content, **kwargs)
            else:
                await interaction.followup.send(content, **kwargs)
        except Exception:
            pass

    # -------------------------
    # Different Modals
    # -------------------------
    class SignupModal(Modal):
        def __init__(self, parent, event_id, conn, discord_id):
            super().__init__(title="Event Signup")
            self.parent = parent
            self.event_id = event_id
            self.conn = conn
            self.discord_id = discord_id

            self.airport_input = TextInput(label="Airport", placeholder="Example CZVR_CTR (Optional)", required=False)
            self.start_input = TextInput(label="Start Availability (HHMM) UTC", placeholder="Example 1900")
            self.end_input = TextInput(label="End Availability (HHMM) UTC", placeholder="Example 2100")
            self.comment_input = TextInput(label="Comment", placeholder="Anything else? (Optional)", required=False, style=discord.TextStyle.paragraph)

            for it in (self.airport_input, self.start_input, self.end_input, self.comment_input):
                self.add_item(it)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                cur = self.parent.ensure_conn().cursor(pymysql.cursors.DictCursor)
                cur.execute("SELECT id FROM users WHERE discord_user_id=%s", (self.discord_id,))
                user_row = cur.fetchone()
                if not user_row:
                    await self.parent.safe_send(interaction, "❌ You haven't linked your Discord yet!", ephemeral=True)
                    return
                internal_user_id = user_row["id"]

                cur.execute("SELECT 1 FROM event_controller_applications WHERE user_id=%s AND event_id=%s",
                            (internal_user_id, self.event_id))
                if cur.fetchone():
                    await self.parent.safe_send(interaction, "⚠️ You have already signed up!", ephemeral=True)
                    return

                cur.execute("SELECT 1 FROM event_confirms WHERE user_id=%s AND event_id=%s", (internal_user_id, self.event_id))
                if cur.fetchone():
                    await self.parent.safe_send(interaction, "⚠️ You are already confirmed for this event! Please ping the Events Coordinator or the Events Team if you wish to withdraw!", ephemeral=True)
                    return

                cur.execute("SELECT name, start_timestamp, controller_applications_open FROM events WHERE id=%s", (self.event_id,))
                event = cur.fetchone()
                if not event:
                    await self.parent.safe_send(interaction, "❌ Event not found!", ephemeral=True)
                    return
                if event["controller_applications_open"] == 0:
                    await self.parent.safe_send(interaction, "🚫 Bookings are closed!", ephemeral=True)
                    return

                start_ts = event["start_timestamp"]
                event_date = start_ts.date() if not isinstance(start_ts, str) else datetime.strptime(start_ts, "%Y-%m-%d %H:%M:%S").date()

                try:
                    start_time = datetime.strptime(self.start_input.value.strip(), "%H%M").time()
                    end_time = datetime.strptime(self.end_input.value.strip(), "%H%M").time()
                except ValueError:
                    await self.parent.safe_send(interaction, "❌ Invalid time format! Use HHMM, e.g., 1900", ephemeral=True)
                    return

                start_dt = datetime.combine(event_date, start_time)
                end_dt = datetime.combine(event_date, end_time)
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)

                user_comment = self.comment_input.value.strip() or "Signed up via Discord!"

                cur.execute("""
                    INSERT INTO event_controller_applications
                    (event_id, user_id, start_availability_timestamp, end_availability_timestamp, airport, comments, submission_timestamp, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,NOW(),NOW(),NOW())
                """, (
                    self.event_id,
                    internal_user_id,
                    start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    self.airport_input.value.strip(),
                    user_comment
                ))
                self.parent.ensure_conn().commit()

                await self.parent.safe_send(
                    interaction,
                    f"✅ Signed up for **{event['name']}** as **{self.airport_input.value.strip()}** from {start_dt.strftime('%H:%M')} to {end_dt.strftime('%H:%M')} UTC!",
                    ephemeral=True
                )
            except Exception as e:
                log(f"SignupModal error: {e}", "error")
                await self.parent.safe_send(interaction, "❌ Uh Oh! Something went wrong!", ephemeral=True)

    class AddPositionModal(Modal):
        def __init__(self, parent, conn, event_id):
            super().__init__(title="Add New Position")
            self.parent = parent
            self.conn = conn
            self.event_id = event_id
            self.position_input = TextInput(label="Position Name", placeholder="e.g. CZVR_CTR", required=True)
            self.add_item(self.position_input)

        async def on_submit(self, interaction: discord.Interaction):
            new_position = self.position_input.value.strip()
            if not new_position:
                await self.parent.safe_send(interaction, "❌ Position name cannot be empty!", ephemeral=True)
                return
            try:
                with self.parent.ensure_conn().cursor() as c:
                    c.execute("""
                        INSERT INTO event_positions (event_id, position, created_at, updated_at)
                        VALUES (%s, %s, NOW(), NOW())
                    """, (self.event_id, new_position))
                self.parent.ensure_conn().commit()
                await self.parent.safe_send(interaction, f"✅ Added position **{new_position}** for this event!", ephemeral=True)
            except Exception as e:
                log(f"AddPositionModal error: {e}", "error")
                await self.parent.safe_send(interaction, f"❌ Database error while adding position: {e}", ephemeral=True)

    class ManualAddModal(Modal):
        def __init__(self, parent, conn, event_id):
            super().__init__(title="Manually Add Confirmed Controller")
            self.parent = parent
            self.conn = conn
            self.event_id = event_id

            self.discord_id_input = TextInput(label="Discord Username", placeholder="e.g. Discord Username", required=True)
            self.airport_input = TextInput(label="Airport", placeholder="e.g. CZVR_CTR", required=True)
            self.start_input = TextInput(label="Start Time (HHMM UTC)", placeholder="e.g. 1800", required=True)
            self.end_input = TextInput(label="End Time (HHMM UTC)", placeholder="e.g. 2100", required=True)

            self.add_item(self.discord_id_input)
            self.add_item(self.airport_input)
            self.add_item(self.start_input)
            self.add_item(self.end_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                user_input = self.discord_id_input.value.strip()
                guild = interaction.guild

                member = guild.get_member_named(user_input)
                if not member:
                    await self.parent.safe_send(interaction, f"❌ User `{user_input}` is not in this server!", ephemeral=True)
                    return

                discord_user_id = member.id

                cursor = self.parent.ensure_conn().cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT id FROM users WHERE discord_user_id=%s", (discord_user_id,))
                user_row = cursor.fetchone()
                if not user_row:
                    await self.parent.safe_send(interaction, f"❌ User `{user_input}` not found in database!", ephemeral=True)
                    return
                user_id = user_row["id"]

                cursor.execute("SELECT start_timestamp FROM events WHERE id=%s", (self.event_id,))
                event = cursor.fetchone()
                if not event:
                    await self.parent.safe_send(interaction, "❌ Event not found!", ephemeral=True)
                    return
                event_date = event["start_timestamp"].date()

                try:
                    start_time = datetime.strptime(self.start_input.value.strip(), "%H%M").time()
                    end_time = datetime.strptime(self.end_input.value.strip(), "%H%M").time()
                except ValueError:
                    await self.parent.safe_send(interaction, "❌ Invalid time format! Use HHMM (e.g. 1900)", ephemeral=True)
                    return

                start_dt = datetime.combine(event_date, start_time)
                end_dt = datetime.combine(event_date, end_time)
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)

                cursor.execute("""
                    INSERT INTO event_confirms
                    (event_id, user_id, airport, start_timestamp, end_timestamp, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,NOW(),NOW())
                """, (
                    self.event_id,
                    user_id,
                    self.airport_input.value.strip(),
                    start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    end_dt.strftime("%Y-%m-%d %H:%M:%S")
                ))
                self.parent.ensure_conn().commit()

                await self.parent.safe_send(
                    interaction,
                    f"✅ Manually added confirmed controller (User ID {user_id}) for **{self.airport_input.value.strip()}** from {start_dt.strftime('%H:%M')}–{end_dt.strftime('%H:%M')} UTC!",
                    ephemeral=True
                )
            except Exception as e:
                log(f"ManualAddModal error: {e}", "error")
                await self.parent.safe_send(interaction, f"❌ Error adding controller: {e}", ephemeral=True)


    # -------------------------
    # Slash command
    # -------------------------
    @app_commands.command(name="event", description="Manage events (Events Team only)")
    @app_commands.checks.has_role(EVENT_ROLE_ID)
    async def event(self, interaction: discord.Interaction):
        cleanup_expired_event_channels(self.ensure_conn())
        event_channels = load_event_channels()
        linked_event_id = event_channels.get(str(interaction.channel.id))

        if linked_event_id:
            rows = self.db_query("SELECT id, name, start_timestamp, end_timestamp, description, image_url FROM events WHERE id=%s", (linked_event_id,))
            if not rows:
                await self.safe_send(interaction, "❌ Linked event not found!", ephemeral=True)
                return
            event = rows[0]
            await self.safe_send(interaction, embed=self.embed_event(event), view=self.make_team_buttons(), ephemeral=True)
            return

        rows = self.db_query("SELECT id, name, start_timestamp, end_timestamp, description, image_url FROM events ORDER BY start_timestamp ASC LIMIT 25")
        if not rows:
            await self.safe_send(interaction, "No events found!", ephemeral=True)
            return

        options = [
            discord.SelectOption(
                label=f"{r['name']} ({r['start_timestamp'].strftime('%Y-%m-%d')})",
                description=(r['description'][:50] + "...") if r.get('description') else None,
                value=str(r['id'])
            ) for r in rows
        ]
        select = Select(placeholder="Select an event to manage...", options=options, min_values=1, max_values=1)

        async def select_cb(interact: discord.Interaction):
            selected_id = int(select.values[0])
            event_row = next(r for r in rows if r["id"] == selected_id)

            existing_channel = next((ch for ch, eid in event_channels.items() if eid == selected_id), None)
            if existing_channel:
                await self.safe_send(
                    interact,
                    f"⚠️ This event (**{event_row['name']}**) is already linked to another channel (<#{existing_channel}>)!",
                    ephemeral=True
                )
                return

            event_channels[str(interact.channel.id)] = selected_id
            save_event_channels(event_channels)

            await self.safe_send(
                interact,
                f"✅ Channel linked to **{event_row['name']}**",
                view=self.make_team_buttons(),
                ephemeral=True
            )
            guild = interact.guild
            role = guild.get_role(EVENT_PING_ID)
            ping_text = role.mention if role else ""
            await interact.channel.send(content=f"{ping_text}", embed=self.embed_event(event_row), view=self.make_public_view())

        select.callback = select_cb
        view = View()
        view.add_item(select)
        await self.safe_send(interaction, "Select an event to manage:", view=view, ephemeral=True)

    # -------------------------
    # Component routing
    # -------------------------
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id")
        if not cid:
            return

        event_channels = load_event_channels()
        event_id = event_channels.get(str(interaction.channel.id))
        if not event_id:
            await self.safe_send(interaction, "❌ This channel is not linked to an event!", ephemeral=True)
            return

        if cid == "public_signup":
            return await self.handle_public_signup(interaction, event_id)
        if cid == "public_positions":
            return await self.show_event_positions(interaction, event_id)
        if cid.startswith("withdraw_"):
            return await self.handle_withdraw(interaction, cid)
        if cid.startswith("approve_") or cid.startswith("disapprove_"):
            return await self.handle_approve_disapprove(interaction, cid)
        if cid in ["open_bookings", "close_bookings", "applicants", "confirmed", "positions", "manual_add"]:
            return await self.handle_team_action(interaction, cid, event_id)
        if cid == "complete_event":
            await interaction.response.defer(ephemeral=True)
            self.client.loop.create_task(self._publish_confirms(interaction))
            return

    # -------------------------
    # Handlers
    # -------------------------
    async def handle_public_signup(self, interaction: discord.Interaction, event_id: int):
        cur = self.ensure_conn().cursor(pymysql.cursors.DictCursor)
        cur.execute("SELECT id FROM users WHERE discord_user_id=%s", (interaction.user.id,))
        user_row = cur.fetchone()
        if not user_row:
            await self.safe_send(interaction, "❌ You haven't linked your Discord yet!", ephemeral=True)
            return
        internal_user_id = user_row["id"]

        cur.execute("SELECT id FROM event_controller_applications WHERE event_id=%s AND user_id=%s", (event_id, internal_user_id))
        existing = cur.fetchone()
        if existing:
            withdraw_view = View()
            withdraw_view.add_item(Button(label="Withdraw Application", style=discord.ButtonStyle.danger, custom_id=f"withdraw_{existing['id']}"))
            await self.safe_send(interaction, "⚠️ You’ve already signed up for this event. Would you like to withdraw your application?", view=withdraw_view, ephemeral=True)
            return

        modal = Event.SignupModal(self, event_id, self.ensure_conn(), interaction.user.id)
        await interaction.response.send_modal(modal)

    async def show_event_positions(self, interaction: discord.Interaction, event_id: int):
        rows = self.db_query(
            "SELECT position FROM event_positions WHERE event_id=%s ORDER BY position ASC",
            (event_id,)
        )

        if not rows:
            await self.safe_send(interaction, "There are no positions defined for this event!", ephemeral=True)
            return

        text = "\n".join(row["position"] for row in rows)

        embed = self.build_embed(
            title="Event Positions Available!",
            description=text,
            color=0x3498db
        )

        await self.safe_send(interaction, embed=embed, ephemeral=True)

    async def handle_withdraw(self, interaction: discord.Interaction, cid: str):
        try:
            app_id = int(cid.split("_", 1)[1])
            self.db_exec("DELETE FROM event_controller_applications WHERE id=%s", (app_id,))
            await self.safe_send(interaction, "✅ Your application has been withdrawn!", ephemeral=True)
        except Exception as e:
            log(f"Withdraw error: {e}", "error")
            await self.safe_send(interaction, "❌ Failed to withdraw your application!", ephemeral=True)

    async def handle_approve_disapprove(self, interaction: discord.Interaction, cid: str):
        try:
            app_id = int(cid.split("_", 1)[1])
            rows = self.db_query("""
                SELECT e.*, u.fname, u.lname
                FROM event_controller_applications e
                JOIN users u ON u.id = e.user_id
                WHERE e.id=%s
            """, (app_id,))
            if not rows:
                await self.safe_send(interaction, "❌ Application not found!", ephemeral=True)
                return
            app = rows[0]

            if cid.startswith("approve_"):
                self.db_exec("""
                    INSERT INTO event_confirms
                    (event_id, user_id, airport, start_timestamp, end_timestamp, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,NOW(),NOW())
                """, (
                    app['event_id'],
                    app['user_id'],
                    app['airport'],
                    app['start_availability_timestamp'],
                    app['end_availability_timestamp']
                ))
                self.db_exec("DELETE FROM event_controller_applications WHERE id=%s", (app_id,))
                await self.safe_send(interaction, f"✅ Approved **{app['fname']} {app['lname']}** for {app['airport']}!", ephemeral=True)
            else:
                self.db_exec("DELETE FROM event_controller_applications WHERE id=%s", (app_id,))
                await self.safe_send(interaction, f"❌ Disapproved **{app['fname']} {app['lname']}** for {app['airport']}!", ephemeral=True)
        except Exception as e:
            log(f"approve_disapprove error: {e}", "error")
            await self.safe_send(interaction, "❌ Something went wrong while processing that action!", ephemeral=True)

    async def handle_team_action(self, interaction: discord.Interaction, cid: str, event_id: int):
        if cid == "open_bookings":
            self.db_exec("UPDATE events SET controller_applications_open=1 WHERE id=%s", (event_id,))
            await self.safe_send(interaction, "✅ Controller bookings are now OPEN!", ephemeral=True)
            log(f"Controller bookings opened for event {event_id}", "success")
            return
        if cid == "close_bookings":
            self.db_exec("UPDATE events SET controller_applications_open=0 WHERE id=%s", (event_id,))
            await self.safe_send(interaction, "🔒 Controller bookings are now CLOSED!", ephemeral=True)
            log(f"Controller bookings closed for event {event_id}", "success")
            return
        if cid == "applicants":
            await self._show_applicants(interaction, event_id); return
        if cid == "confirmed":
            await self._show_confirmed(interaction, event_id); return
        if cid == "positions":
            await self._show_positions(interaction, event_id); return
        if cid == "manual_add":
            modal = Event.ManualAddModal(self, self.ensure_conn(), event_id)
            await interaction.response.send_modal(modal); return

    # -------------------------
    # Complex UI flows
    # -------------------------
    async def _show_applicants(self, interaction: discord.Interaction, event_id: int):
        rows = self.db_query("""
            SELECT e.id AS application_id, e.event_id, u.fname, u.lname, e.user_id, e.airport,
                   e.start_availability_timestamp, e.end_availability_timestamp, e.comments
            FROM event_controller_applications e
            JOIN users u ON u.id = e.user_id
            WHERE e.event_id=%s
            ORDER BY e.submission_timestamp ASC
        """, (event_id,))
        if not rows:
            await self.safe_send(interaction, "No applicants found!", ephemeral=True); return

        def make_applicant_embed(sel=None):
            fields = []
            for r in rows:
                name = f"{r['fname']} {r['lname']}" + (" ⬅️" if sel == r['application_id'] else "")
                fields.append((
                    name,
                    (f"**Position:** {r['airport']}\n"
                     f"**Availability:** {r['start_availability_timestamp'].strftime('%H:%M')} – {r['end_availability_timestamp'].strftime('%H:%M')} UTC\n"
                     f"**Comments:** {r['comments'] or 'None'}")
                ))
            return self.build_embed("Pending Applicants", color=0xf1c40f, fields=fields)

        options = [discord.SelectOption(label=f"{r['fname']} {r['lname']}",
                                        description=f"{r['airport']} | {r['start_availability_timestamp'].strftime('%H:%M')}–{r['end_availability_timestamp'].strftime('%H:%M')} UTC",
                                        value=str(r['application_id'])) for r in rows]
        dropdown = Select(placeholder="Select applicant...", options=options, min_values=1, max_values=1)
        approve_btn = Button(label="✅ Approve", style=discord.ButtonStyle.success)
        reject_btn = Button(label="❌ Reject", style=discord.ButtonStyle.danger)

        view = View(timeout=300)
        for w in (dropdown, approve_btn, reject_btn):
            view.add_item(w)

        selected = {"id": None}

        async def dropdown_cb(interact: discord.Interaction):
            selected["id"] = int(dropdown.values[0])
            await interact.response.edit_message(embed=make_applicant_embed(selected["id"]), view=view)

        async def approve_cb(interact: discord.Interaction):
            if not selected["id"]:
                await self.safe_send(interact, "❌ Please select an applicant first!", ephemeral=True); return
            await interact.response.defer(ephemeral=True)
            try:
                app = next(r for r in rows if r['application_id'] == selected["id"])
                self.db_exec("""
                    INSERT INTO event_confirms
                    (event_id, user_id, airport, start_timestamp, end_timestamp, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,NOW(),NOW())
                """, (app['event_id'], app['user_id'], app['airport'], app['start_availability_timestamp'], app['end_availability_timestamp']))
                self.db_exec("DELETE FROM event_controller_applications WHERE id=%s", (selected["id"],))
                rows.remove(app); selected["id"] = None

                if rows:
                    dropdown.options = [discord.SelectOption(label=f"{r['fname']} {r['lname']}",
                                                             description=f"{r['airport']} | {r['start_availability_timestamp'].strftime('%H:%M')}–{r['end_availability_timestamp'].strftime('%H:%M')} UTC",
                                                             value=str(r['application_id'])) for r in rows]
                    await interact.edit_original_response(embed=make_applicant_embed(), view=view)
                else:
                    finished = self.build_embed(title="No more pending applicants 🎉", description="All applications have been reviewed!", color=0x00ff00)
                    await interact.edit_original_response(embed=finished, view=None)
            except Exception as e:
                log(f"approve_cb error: {e}", "error")
                await interact.followup.send(f"❌ Error while approving: {e}", ephemeral=True)

        async def reject_cb(interact: discord.Interaction):
            if not selected["id"]:
                await self.safe_send(interact, "❌ Please select an applicant first!", ephemeral=True); return
            await interact.response.defer(ephemeral=True)
            try:
                app = next(r for r in rows if r['application_id'] == selected["id"])
                self.db_exec("DELETE FROM event_controller_applications WHERE id=%s", (selected["id"],))
                rows.remove(app); selected["id"] = None
                if rows:
                    dropdown.options = [discord.SelectOption(label=f"{r['fname']} {r['lname']}",
                                                             description=f"{r['airport']} | {r['start_availability_timestamp'].strftime('%H:%M')}–{r['end_availability_timestamp'].strftime('%H:%M')} UTC",
                                                             value=str(r['application_id'])) for r in rows]
                    await interact.edit_original_response(embed=make_applicant_embed(), view=view)
                else:
                    finished = self.build_embed(title="No more applicants 🎉", description="All pending applications have been reviewed!", color=0x00ff00)
                    await interact.edit_original_response(embed=finished, view=None)
            except Exception as e:
                log(f"reject_cb error: {e}", "error")
                await interact.followup.send(f"❌ Error rejecting applicant: {e}", ephemeral=True)

        dropdown.callback = dropdown_cb
        approve_btn.callback = approve_cb
        reject_btn.callback = reject_cb

        await self.safe_send(interaction, embed=make_applicant_embed(), view=view, ephemeral=True)

    async def _show_confirmed(self, interaction: discord.Interaction, event_id: int):
        rows = self.db_query("""
            SELECT c.id AS confirm_id, c.event_id, u.fname, u.lname, c.airport,
                c.start_timestamp, c.end_timestamp
            FROM event_confirms c
            JOIN users u ON u.id = c.user_id
            WHERE c.event_id=%s
            ORDER BY u.fname ASC, u.lname ASC
        """, (event_id,))
        if not rows:
            await self.safe_send(interaction, "No confirmed users!", ephemeral=True); return

        def make_confirmed_embed(sel=None):
            fields = []
            for r in rows:
                name = f"{r['fname']} {r['lname']}" + (" ⬅️" if sel == r['confirm_id'] else "")
                fields.append((name, f"**Position:** {r['airport']}\n**Availability:** {r['start_timestamp'].strftime('%H:%M')}  – {r['end_timestamp'].strftime('%H:%M')} UTC"))
            return self.build_embed("Confirmed Users", color=0x00ff00, fields=fields)

        options = [discord.SelectOption(label=f"{r['fname']} {r['lname']}",
                                        description=f"{r['airport']} | {r['start_timestamp'].strftime('%H:%M')}–{r['end_timestamp'].strftime('%H:%M')} UTC",
                                        value=str(r['confirm_id'])) for r in rows]
        dropdown = Select(placeholder="Select a confirmed user...", options=options, min_values=1, max_values=1)
        remove_btn = Button(label="❌ Remove", style=discord.ButtonStyle.danger)

        view = View(timeout=300)
        view.add_item(dropdown); view.add_item(remove_btn)

        selected = {"id": None}

        async def dd_cb(interact: discord.Interaction):
            selected["id"] = int(dropdown.values[0])
            await interact.response.edit_message(embed=make_confirmed_embed(selected["id"]), view=view)

        async def remove_cb(interact: discord.Interaction):
            if not selected["id"]:
                await self.safe_send(interact, "❌ Please select a user first!", ephemeral=True); return
            await interact.response.defer(ephemeral=True)
            try:
                user = next(r for r in rows if r['confirm_id'] == selected["id"])
                self.db_exec("DELETE FROM event_confirms WHERE id=%s", (selected["id"],))
                rows.remove(user); selected["id"] = None
                if rows:
                    dropdown.options = [discord.SelectOption(label=f"{r['fname']} {r['lname']}",
                                                             description=f"{r['airport']} | {r['start_timestamp'].strftime('%H:%M')}–{r['end_timestamp'].strftime('%H:%M')} UTC",
                                                             value=str(r['confirm_id'])) for r in rows]
                    await interact.edit_original_response(embed=make_confirmed_embed(), view=view)
                else:
                    finished = self.build_embed(title="No confirmed users remaining 🎉", description="All confirmations have been removed!", color=0x00ff00)
                    await interact.edit_original_response(embed=finished, view=None)
            except Exception as e:
                log(f"remove_cb error: {e}", "error")
                await interact.followup.send(f"❌ Error removing user: {e}", ephemeral=True)

        dropdown.callback = dd_cb
        remove_btn.callback = remove_cb

        await self.safe_send(interaction, embed=make_confirmed_embed(), view=view, ephemeral=True)

    async def _show_positions(self, interaction: discord.Interaction, event_id: int):
        rows = self.db_query("SELECT id, position FROM event_positions WHERE event_id=%s ORDER BY id ASC", (event_id,))
        if rows:
            fields = [(f"ID: {r['id']}", r['position']) for r in rows]
            embed = self.build_embed(title="Event Positions", color=0x00ff00, fields=fields)
        else:
            embed = self.build_embed(title="Event Positions", color=0x00ff00, description="No positions defined yet for this event!")

        view = View(timeout=300)
        add_btn = Button(label="➕ Add Position", style=discord.ButtonStyle.success)
        del_btn = Button(label="🗑️ Delete Position", style=discord.ButtonStyle.danger)
        refresh_btn = Button(label="🔄 Refresh", style=discord.ButtonStyle.secondary)
        for b in (add_btn, del_btn, refresh_btn):
            view.add_item(b)

        dropdown = None
        sel = {"id": None}
        if rows:
            options = [discord.SelectOption(label=r["position"], value=str(r["id"])) for r in rows]
            dropdown = Select(placeholder="Select position to delete...", options=options, min_values=1, max_values=1)
            view.add_item(dropdown)

            async def dd_cb(interact: discord.Interaction):
                sel["id"] = int(dropdown.values[0])
                await interact.response.defer()

            async def del_cb(interact: discord.Interaction):
                if not sel["id"]:
                    await self.safe_send(interact, "❌ Please select a position first!", ephemeral=True); return
                pos_name = next((r["position"] for r in rows if r["id"] == sel["id"]), "Unknown")
                try:
                    self.db_exec("DELETE FROM event_positions WHERE id=%s", (sel["id"],))
                    await self.safe_send(interact, f"🗑️ Deleted position **{pos_name}**!", ephemeral=True)
                    refreshed = self.db_query("SELECT id, position FROM event_positions WHERE event_id=%s ORDER BY id ASC", (event_id,))
                    if refreshed:
                        refreshed_embed = self.build_embed(title="Event Positions", color=0x00ff00, fields=[(f"ID: {r['id']}", r['position']) for r in refreshed])
                    else:
                        refreshed_embed = self.build_embed(title="Event Positions", color=0x00ff00, description="No positions defined yet for this event!")
                    try:
                        await interact.message.edit(embed=refreshed_embed, view=view)
                    except Exception:
                        pass
                except Exception as e:
                    log(f"delete position error: {e}", "error")
                    await self.safe_send(interact, f"❌ Error deleting position: {e}", ephemeral=True)

            dropdown.callback = dd_cb
            del_btn.callback = del_cb

        async def add_cb(interact: discord.Interaction):
            modal = Event.AddPositionModal(self, self.ensure_conn(), event_id)
            await interact.response.send_modal(modal)

        async def refresh_cb(interact: discord.Interaction):
            refreshed = self.db_query("SELECT id, position FROM event_positions WHERE event_id=%s ORDER BY id ASC", (event_id,))
            if refreshed:
                refreshed_embed = self.build_embed(title="Event Positions", color=0x00ff00, fields=[(f"ID: {r['id']}", r['position']) for r in refreshed])
            else:
                refreshed_embed = self.build_embed(title="Event Positions", color=0x00ff00, description="No positions defined yet for this event!")
            await interact.response.edit_message(embed=refreshed_embed, view=view)

        add_btn.callback = add_cb
        refresh_btn.callback = refresh_cb

        await self.safe_send(interaction, embed=embed, view=view, ephemeral=True)

    # -------------------------
    # Error handler
    # -------------------------
    @event.error
    async def event_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingRole):
            await self.safe_send(interaction, "You don’t have permission to use this command! (Events Team only)!", ephemeral=True)
            return
        log(f"/event command error: {error}", "error")
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ Something went wrong while running this command!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Something went wrong while running this command!", ephemeral=True)
        except Exception as e:
            log(f"Error sending /event error message: {e}", "error")


async def setup(client):
    await client.add_cog(Event(client))
