from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class DoNotDisturbCalculator:
    def next_send_at(
        self,
        now: int,
        dnd: dict[str, str] | None,
        *,
        user_timezone: str = "UTC",
    ) -> int | None:
        if not dnd or not dnd.get("from") or not dnd.get("to"):
            return None
        timezone_name = dnd.get("tz") or user_timezone
        try:
            timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            timezone = ZoneInfo("UTC")
        local = datetime.fromtimestamp(now, UTC).astimezone(timezone)
        start_hour, start_minute = map(int, dnd["from"].split(":"))
        end_hour, end_minute = map(int, dnd["to"].split(":"))
        start = local.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        end = local.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
        if end <= start:
            if local < end:
                start -= timedelta(days=1)
            else:
                end += timedelta(days=1)
        if start <= local < end:
            return int(end.astimezone(UTC).timestamp())
        return None
