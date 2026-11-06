"""Parse the "Vervoerschema" table from the Taxsys parent portal.

Pure functions, no Home Assistant imports, so they are easy to test.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from html.parser import HTMLParser

from .const import PART_AFTERNOON, PART_MORNING, PORTAL_TZ

SCHEDULE_MARKER = 'id="tblvvs"'
LOGIN_FORM_MARKER = 'name="password"'


@dataclass
class Ride:
    """One ride from the schedule."""

    date: date
    day: str
    part: str  # PART_MORNING or PART_AFTERNOON
    pickup_time: str  # O-tijd, "HH:MM"
    arrival_time: str  # A-tijd, "HH:MM"
    pickup: datetime | None
    arrival: datetime | None
    origin: str
    destination: str
    status: str
    route: str
    driver: str
    live_location: str | None = None
    live_time: str | None = None

    def as_dict(self) -> dict:
        """Return a JSON-serialisable dict."""
        data = asdict(self)
        data["date"] = self.date.isoformat()
        data["pickup"] = self.pickup.isoformat() if self.pickup else None
        data["arrival"] = self.arrival.isoformat() if self.arrival else None
        return data


class _ScheduleTableParser(HTMLParser):
    """Collect the rows of <table id="tblvvs">."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.table_depth = 0
        self.row: list[dict] | None = None
        self.cell: dict | None = None
        self.rows: list[list[dict]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "table":
            if self.in_table:
                self.table_depth += 1
            elif a.get("id") == "tblvvs":
                self.in_table = True
                self.table_depth = 0
            return
        if not self.in_table:
            return
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = {
                "tag": tag,
                "id": a.get("id") or "",
                "class": a.get("class") or "",
                "text": [],
            }
        elif tag in ("br", "div") and self.cell is not None:
            self.cell["text"].append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_table:
            return
        if tag == "table":
            if self.table_depth:
                self.table_depth -= 1
            else:
                self.in_table = False
        elif tag in ("td", "th") and self.cell is not None and self.row is not None:
            raw = "".join(self.cell["text"])
            lines = [re.sub(r"\s+", " ", line).strip() for line in raw.split("\n")]
            self.cell["text"] = "\n".join(line for line in lines if line)
            self.row.append(self.cell)
            self.cell = None
        elif tag == "div" and self.cell is not None:
            self.cell["text"].append("\n")
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell["text"].append(data)


def _to_datetime(day: date, hhmm: str) -> datetime | None:
    if not re.fullmatch(r"\d{1,2}:\d{2}", hhmm or ""):
        return None
    hour, minute = map(int, hhmm.split(":"))
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=PORTAL_TZ)


def _first_line(text: str) -> str:
    return text.split("\n")[0].strip()


def parse_schedule(html: str) -> list[Ride]:
    """Return all rides found in the schedule table, in page order."""
    parser = _ScheduleTableParser()
    parser.feed(html)
    rides: list[Ride] = []
    for row in parser.rows:
        if any(c["tag"] == "th" for c in row):
            continue
        cells = [c for c in row if c["id"] == "middle" and "hide" not in c["class"]]
        if len(cells) >= 8:
            t = [c["text"] for c in cells]
            m = re.search(r"(\d{2})-(\d{2})-(\d{2,4})", t[0])
            if not m:
                continue
            year = int(m.group(3))
            day = date(
                year + 2000 if year < 100 else year, int(m.group(2)), int(m.group(1))
            )
            pickup_time = _first_line(t[1])
            arrival_time = _first_line(t[3])
            rides.append(
                Ride(
                    date=day,
                    day=_first_line(t[0]).capitalize(),
                    part=PART_MORNING if pickup_time < "12:00" else PART_AFTERNOON,
                    pickup_time=pickup_time,
                    arrival_time=arrival_time,
                    pickup=_to_datetime(day, pickup_time),
                    arrival=_to_datetime(day, arrival_time),
                    origin=t[2].replace("\n", ", "),
                    destination=t[4].replace("\n", ", "),
                    status=t[5],
                    route=t[6],
                    driver=t[7],
                )
            )
        elif len(row) == 1 and rides and "Locatie voertuig" in row[0]["text"]:
            txt = row[0]["text"]
            loc = re.search(r"Locatie voertuig\s*:\s*(.+)", txt)
            tm = re.search(r"Tijdstip meting\s*:\s*(\d{1,2}:\d{2})", txt)
            rides[-1].live_location = loc.group(1).strip() if loc else None
            rides[-1].live_time = tm.group(1) if tm else None
    return rides


def next_ride(rides: list[Ride], part: str, today: date) -> Ride | None:
    """First ride of the given part (morning/afternoon) today or later."""
    for ride in rides:
        if ride.part == part and ride.date >= today:
            return ride
    return None
