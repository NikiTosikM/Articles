from functools import lru_cache

from article.service  import (
    RequestArticleApi,
    RedisDataManager,
    PostgresDataManager
)
from core import settings


def get_request_api_man():
    ''' Returns an object for getting information about articles '''
    return RequestArticleApi(api_key=settings.api_key)


@lru_cache
def get_postgre_man():
    ''' Returns an object for working with the db '''
    return PostgresDataManager()


@lru_cache
def get_redis_man():
    ''' Returns an object for working with the redis '''
    return RedisDataManager(
        host=settings.redis.host,
        port=settings.redis.port,
        max_connetion=settings.redis.max_connection
    )