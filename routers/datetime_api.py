from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/datetime", tags=["DateTime"])


@router.get("/today")
def get_today():
    """
    Return structured information about today's date.

    Includes the full date, day name, month name, year, numeric day-of-year, and ISO week number.
    All values are based on the server's local time.
    """
    now = datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A"),
        "month": now.strftime("%B"),
        "year": now.year,
        "day_of_year": now.timetuple().tm_yday,
        "week_number": now.isocalendar().week,
    }


@router.get("/now")
def get_now(tz: str = Query(default="UTC", description="IANA timezone, e.g. Asia/Kolkata")):
    """
    Return the current date and time in a given timezone.

    - `tz` must be a valid IANA timezone name (e.g. `UTC`, `Asia/Kolkata`, `America/New_York`)
    - Returns ISO 8601 datetime, UTC offset, and Unix timestamp
    - Defaults to `UTC` if no timezone is specified
    """
    try:
        zone = ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        raise HTTPException(status_code=400, detail=f"Unknown timezone: {tz}")
    now = datetime.now(zone)
    return {
        "datetime": now.isoformat(),
        "timezone": tz,
        "utc_offset": now.strftime("%z"),
        "timestamp_unix": int(now.timestamp()),
    }


@router.get("/timestamp")
def get_timestamp():
    """
    Return the current Unix timestamp in multiple formats.

    - `unix` — seconds since epoch (UTC)
    - `unix_ms` — milliseconds since epoch (useful for JavaScript)
    - `iso8601` — human-readable UTC datetime string
    """
    now = datetime.now(timezone.utc)
    return {
        "unix": int(now.timestamp()),
        "unix_ms": int(now.timestamp() * 1000),
        "iso8601": now.isoformat(),
    }


@router.get("/format")
def format_date(
    date: str = Query(..., description="Date string in YYYY-MM-DD format"),
    fmt: str = Query(default="%B %d, %Y", description="strftime format string"),
):
    """
    Format a date string using a custom strftime pattern.

    - `date` must be in `YYYY-MM-DD` format (e.g. `2026-01-15`)
    - `fmt` is a Python strftime format string (default: `%B %d, %Y` → `January 15, 2026`)
    - Common tokens: `%Y` year, `%m` month number, `%d` day, `%A` weekday name, `%B` month name
    """
    try:
        parsed = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")
    return {"input": date, "formatted": parsed.strftime(fmt), "format_used": fmt}


@router.get("/diff")
def date_diff(
    from_date: str = Query(..., description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., description="End date YYYY-MM-DD"),
):
    """
    Calculate the difference between two dates.

    - Both dates must be in `YYYY-MM-DD` format
    - Returns the difference in days, weeks, approximate months, and approximate years
    - A negative result means `to_date` is earlier than `from_date`
    """
    try:
        d1 = datetime.strptime(from_date, "%Y-%m-%d")
        d2 = datetime.strptime(to_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Dates must be in YYYY-MM-DD format")
    delta = d2 - d1
    return {
        "from": from_date,
        "to": to_date,
        "days": delta.days,
        "weeks": delta.days // 7,
        "months_approx": round(delta.days / 30.44, 2),
        "years_approx": round(delta.days / 365.25, 2),
    }
