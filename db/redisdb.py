import redis.asyncio as redis
# import aioredis
from config.config import get_settings

settings = get_settings()

auth_redis = redis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                            encoding="utf-8", decode_responses=True, db=1)


def get_auth_redis():
    return auth_redis

