from flask import Blueprint, current_app, jsonify
from flask_restful import Api, Resource

from model.rotary_event import RotaryEvent


rotary_events_api = Blueprint('rotary_events_api', __name__, url_prefix='/api/rotary')
api = Api(rotary_events_api)


class UpcomingEventsAPI(Resource):
    def get(self):
        try:
            events = RotaryEvent.get_all()
        except Exception:
            current_app.logger.exception('Failed to load Rotary events')
            return {'message': 'Failed to fetch upcoming events.'}, 503

        return jsonify([event.read() for event in events])


api.add_resource(UpcomingEventsAPI, '/events')
