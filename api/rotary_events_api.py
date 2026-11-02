"""Upcoming events, read by the homepage and managed by Admins.

    GET    /api/rotary/events            public   list, soonest first
    POST   /api/rotary/events            Admin    {date, program, speaker}
    DELETE /api/rotary/events/<id>       Admin    remove one

A date travels as `YYYY-MM-DD`; the frontend formats it for display.
Request/response examples: api/rotary_events.http.
"""

from functools import wraps

from flask import Blueprint, current_app, request
from flask_restful import Api, Resource

from __init__ import db
from api.authorize import token_required
from model.rotary_event import RotaryEvent, validate_event


rotary_events_api = Blueprint('rotary_events_api', __name__, url_prefix='/api/rotary')
api = Api(rotary_events_api)


def json_errors(func):
    """Last resort for the write endpoints: a JSON body instead of an HTML
    error page, with the traceback in the server log."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:  # noqa: BLE001 - logged with the traceback below
            db.session.rollback()
            current_app.logger.exception('rotary events API error')
            return {'message': 'Server error in the rotary events API'}, 500
    return wrapper


class UpcomingEventsAPI(Resource):
    method_decorators = [json_errors]

    def get(self):
        """Public: every event, soonest first. This is what the homepage calls."""
        try:
            events = RotaryEvent.get_all()
        except Exception:
            current_app.logger.exception('Failed to load Rotary events')
            return {'message': 'Failed to fetch upcoming events.'}, 503

        return [event.read() for event in events]

    @token_required("Admin")
    def post(self):
        """Admin only. Body: {"date": "2026-11-12", "program": "...", "speaker": "..."}"""
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {'message': 'JSON object body required'}, 400

        fields, errors = validate_event(data)
        if errors:
            return {'message': 'Invalid event', 'errors': errors}, 400

        event = RotaryEvent(**fields).create()
        if event is None:
            return {'message': 'Could not save the event'}, 500

        return event.read(), 201


class EventAPI(Resource):
    method_decorators = [json_errors]

    @token_required("Admin")
    def delete(self, event_id):
        """Admin only. Returns the deleted event so the caller can confirm it."""
        event = RotaryEvent.find(event_id)
        if event is None:
            return {'message': f'No event with id {event_id}'}, 404

        deleted = event.read()
        event.delete()
        return {'message': f'Deleted event {event_id}', 'event': deleted}, 200


api.add_resource(UpcomingEventsAPI, '/events')
api.add_resource(EventAPI, '/events/<int:event_id>')
