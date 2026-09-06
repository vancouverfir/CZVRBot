from datetime import datetime, timezone
from zoneinfo import ZoneInfo


VANCOUVER_TIMEZONE = ZoneInfo("America/Vancouver")


def utc_channel_name(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"UTC Live Time: {now.astimezone(timezone.utc):%H:%M}"


def vancouver_channel_name(now: datetime | None = None) -> str:
    now = (now or datetime.now(timezone.utc)).astimezone(VANCOUVER_TIMEZONE)
    offset = now.utcoffset()
    if offset is None:
        raise ValueError("America/Vancouver returned no UTC offset")

    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    offset_text = f"UTC{sign}{hours}"
    if minutes:
        offset_text += f":{minutes:02d}"

    return f"{now.tzname()} Live Time ({offset_text}): {now:%H:%M}"


def home_controller_count(members, role_id: int) -> int:
    return sum(any(role.id == role_id for role in member.roles) for member in members)
