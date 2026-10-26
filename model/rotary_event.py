from datetime import datetime
from sqlite3 import IntegrityError

from __init__ import app, db


class RotaryEvent(db.Model):
    __tablename__ = 'rotary_events'

    id = db.Column(db.Integer, primary_key=True)
    _date = db.Column(db.String(100), nullable=False)
    _program = db.Column(db.String(255), nullable=False)
    _speaker = db.Column(db.String(255), nullable=False)
    _sort_order = db.Column(db.Integer, nullable=False, default=0)
    _created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(self, date, program, speaker, sort_order=0):
        self._date = date
        self._program = program
        self._speaker = speaker
        self._sort_order = sort_order

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def read(self):
        return {
            'id': self.id,
            'date': self._date,
            'program': self._program,
            'speaker': self._speaker,
        }

    @staticmethod
    def get_all():
        return RotaryEvent.query.order_by(
            RotaryEvent._sort_order.asc(),
            RotaryEvent.id.asc(),
        ).all()


SAMPLE_EVENTS = [
    ('Sept 12, Sat', 'Poway Rotary Parade, 9-11 AM on Poway Road', 'Community Event'),
    ('Sept 16', "Robin's Nest Rescue", 'Jenny Ng'),
    ('Sept 23', 'Special Needs Support', 'Tony Rubino'),
    ('Nov 26', 'San Diego Blood Bank Drive', 'Service Project'),
]


def initRotaryEvents():
    with app.app_context():
        RotaryEvent.__table__.create(bind=db.engine, checkfirst=True)

        if RotaryEvent.query.first():
            return

        for sort_order, (date, program, speaker) in enumerate(SAMPLE_EVENTS):
            db.session.add(RotaryEvent(
                date=date,
                program=program,
                speaker=speaker,
                sort_order=sort_order,
            ))

        db.session.commit()
