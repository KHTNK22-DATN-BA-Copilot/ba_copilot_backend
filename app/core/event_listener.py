import asyncio
import json
import logging
import redis.asyncio as redis

from app.core.config import settings
from app.services.step_ws_notifier import StepWSNotifier

logger = logging.getLogger(__name__)


async def redis_event_listener():
    r = redis.from_url(settings.CELERY_BROKER_URL)
    pubsub = r.pubsub()

    await pubsub.subscribe("events")
    logger.info("Subscribed to Redis channel: events")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = json.loads(message["data"])
            logger.info(f"Received event: {data}")

            notifier = StepWSNotifier(data["project_id"], data["step"])

            await notifier.send(data)

    except asyncio.CancelledError:
        logger.info("Redis listener shutting down...")
        await pubsub.unsubscribe("events")
        await pubsub.close()
        raise
