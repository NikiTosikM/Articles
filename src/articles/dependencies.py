from fastapi import Request
from .service import (
    RequestArticleApi,
    RedisDataManager,
    PostgresDataManager
)
from core import settings


def get_request_api_man():
    ''' Returns an object for getting information about articles '''
    return RequestArticleApi(api_key=settings.api_key)


def get_postgre_man():
    ''' Returns an object for working with the db '''
    return PostgresDataManager()


def get_redis_man():
    return RedisDataManager(
        host=settings.redis.host,
        port=settings.redis.port,
        max_connetion=settings.redis.max_connection
    )