"""Events shown in the homepage's upcoming-events list.

Anyone may read them (see api/rotary_events_api.py); only an Admin may add or
delete one. Dates are stored as real dates and travel as ISO `YYYY-MM-DD`, so
the database can order and filter by them instead of relying on a hand-kept
sort column.
"""

from datetime import date, datetime

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from __init__ import app, db

# Matches the _program / _speaker column widths.
MAX_TEXT = 255


def parse_event_date(value):
    """A `YYYY-MM-DD` string (what the frontend sends) -> (date, None), or
    (None, message) when it is missing or not an ISO date."""
    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None
    if not isinstance(value, str) or not value.strip():
        return None, "date is required, as YYYY-MM-DD"
    raw = value.strip()
    try:
        return date.fromisoformat(raw), None
    except ValueError:
        return None, f"date must be YYYY-MM-DD, got {raw!r}"


def validate_event(data):
    """Validation shared by the create endpoint and the seed below.

    Returns (fields, errors): fields is ready to splat into RotaryEvent(),
    errors is a list of human-readable problems (empty when valid).
    """
    fields, errors = {}, []

    parsed, date_error = parse_event_date(data.get("date"))
    if date_error:
        errors.append(date_error)
    else:
        fields["date"] = parsed

    for name in ("program", "speaker"):
        value = data.get(name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name} is required")
            continue
        value = value.strip()
        if len(value) > MAX_TEXT:
            errors.append(f"{name} must be at most {MAX_TEXT} characters")
            continue
        fields[name] = value

    return fields, errors


class RotaryEvent(db.Model):
    __tablename__ = 'rotary_events'

    id = db.Column(db.Integer, primary_key=True)
    _date = db.Column(db.Date, nullable=False)
    _program = db.Column(db.String(MAX_TEXT), nullable=False)
    _speaker = db.Column(db.String(MAX_TEXT), nullable=False)
    _created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, date, program, speaker):
        self._date = date
        self._program = program
        self._speaker = speaker

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def read(self):
        return {
            'id': self.id,
            'date': self._date.isoformat(),
            'program': self._program,
            'speaker': self._speaker,
        }

    @staticmethod
    def find(event_id):
        return db.session.get(RotaryEvent, event_id) if isinstance(event_id, int) else None

    @staticmethod
    def get_all():
        """Soonest first; the homepage depends on the order."""
        return RotaryEvent.query.order_by(
            RotaryEvent._date.asc(),
            RotaryEvent.id.asc(),
        ).all()


# PowPAC's current mainstage run (The Wisdom of Eve, Nov 13 - Dec 13, 2026) plus the
# 2027 season announcement, matching the shows already described on the homepage.
# Dates are deliberately in the near future so a fresh database has a sensible
# upcoming list to demo; an Admin can add or delete from here on.
SAMPLE_EVENTS = [
    {'date': '2026-11-13', 'program': 'The Wisdom of Eve - Opening Night',
     'speaker': 'Cast of The Wisdom of Eve'},
    {'date': '2026-11-21', 'program': 'The Wisdom of Eve - Saturday Matinee, 2:00 PM',
     'speaker': 'Cast of The Wisdom of Eve'},
    {'date': '2026-12-05', 'program': 'The Wisdom of Eve - Saturday Matinee, 2:00 PM',
     'speaker': 'Cast of The Wisdom of Eve'},
    {'date': '2026-12-13', 'program': 'The Wisdom of Eve - Closing Performance, 2:00 PM',
     'speaker': 'Cast of The Wisdom of Eve'},
    {'date': '2027-01-15', 'program': 'Season 45 - 2027 Season Announcement',
     'speaker': 'PowPAC Board'},
]


def initRotaryEvents(seed=False):
    """Create the table on a new database, and seed it on the run that creates it.

    Seeding is tied to the table being created, not to it being empty: once an
    Admin has deleted every event, a restart must not bring the samples back.

    seed=True is for the data-generation path (scripts/db_init.py, `flask custom
    generate_data`), which runs db.create_all() itself -- so the table already
    exists by the time this is called and would otherwise stay empty.
    """
    with app.app_context():
        table_created = not inspect(db.engine).has_table('rotary_events')
        RotaryEvent.__table__.create(bind=db.engine, checkfirst=True)
        if not (table_created or seed):
            return
        if RotaryEvent.query.first():  # never duplicate rows
            return

        for sample in SAMPLE_EVENTS:
            fields, errors = validate_event(sample)
            if errors:  # a typo in the samples above, surfaced at startup
                raise ValueError(f"SAMPLE_EVENTS entry {sample!r}: {'; '.join(errors)}")
            db.session.add(RotaryEvent(**fields))

        db.session.commit()
