from functools import lru_cache

from redis import Redis
from rq import Queue

from sigserve.config import get_settings

QUEUE_NAME = "sigserve"


@lru_cache
def get_queue() -> Queue:
    settings = get_settings()
    return Queue(QUEUE_NAME, connection=Redis.from_url(settings.redis_url))
