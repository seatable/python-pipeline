import logging
import os
import time

import redis

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self._client = self.get_redis_client()

    def get_redis_client(self):
        pool = redis.ConnectionPool(
            host=os.environ.get("REDIS_HOST") or "127.0.0.1",
            port=int(os.environ.get("REDIS_PORT") or "6379"),
            db=int(os.environ.get("REDIS_DB") or "0"),
            password=os.environ.get("REDIS_PASSWORD", ""),
            socket_timeout=3,
            socket_connect_timeout=3,
            retry_on_timeout=True,
            health_check_interval=30,
            decode_responses=True,
        )

        return redis.Redis(connection_pool=pool)

    # ========= executor within retry logic =========

    def _execute(self, func, *args, **kwargs):
        retry_count = 0
        while retry_count <= 3:
            try:
                return func(*args, **kwargs)

            except (redis.TimeoutError, redis.ConnectionError) as e:
                logger.exception(e)
                retry_count += 1
                time.sleep(0.1 * 2**retry_count)
                continue

            except (redis.ResponseError, redis.DataError) as e:
                logger.exception(e)
                raise e

    # ========= KV =========

    def get(self, key: str):
        return self._execute(self._client.get, key)

    def set(self, key: str, value, ex: int | None = None):
        return self._execute(self._client.set, key, value, ex=ex)

    # ========= LIST =========

    def lpush(self, key: str, *values):
        return self._execute(self._client.lpush, key, *values)

    def rpush(self, key: str, *values):
        return self._execute(self._client.rpush, key, *values)

    def lpop(self, key: str):
        return self._execute(self._client.lpop, key)

    def rpop(self, key: str):
        return self._execute(self._client.rpop, key)

    def llen(self, key):
        return self._execute(self._client.llen, key)

    # ========= utils =========

    def exists(self, key: str) -> bool:
        return bool(self._execute(self._client.exists, key))

    def delete(self, *keys):
        return self._execute(self._client.delete, *keys)
