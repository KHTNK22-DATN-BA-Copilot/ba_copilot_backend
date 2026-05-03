import json
import redis
from app.core.config import settings


class EventEmitter:
    def emit(self, event: dict):
        raise NotImplementedError


class RedisEventEmitter(EventEmitter):
    def __init__(self):
        self.r = redis.Redis.from_url(settings.CELERY_BROKER_URL)

    def emit(self, event: dict):
        self.r.publish("events", json.dumps(event))


emitter = RedisEventEmitter()
