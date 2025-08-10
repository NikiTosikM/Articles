import datetime


from loguru import logger
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import (
    ConnectionError,
    TimeoutError,
    DataError,
    ResponseError,
    RedisError,
)
import redis
from pydantic import ValidationError
from fastapi import HTTPException, status

from articles import (
    Article,
    DisplayOnPageArticle,
    Articles_model,
    decode_info,
    decode_keys_and_value,
)


class RedisDataManager:
    def __init__(self, host: str, port: int, max_connetion: int):
        self.host = host
        self.port = port
        self.max_connection = max_connetion
        self.pool = ConnectionPool(
            host=self.host, port=self.port, max_connections=self.max_connection
        )
        self.client: Redis = Redis(connection_pool=self.pool)

    async def close(self):
        await self.client.close()

    async def update_info(self, id_object, field, value) -> None:
        await self.client.hincrby(f"article:id:{id_object}", field, value)

    async def get_specific_article(self, id_object: int) -> Article:
        try:
            cached_data_code: dict[bytes, bytes] = await self.client.hgetall(
                f"article:id:{id_object}"
            )
            decode_cached_data: dict[str, str] = decode_keys_and_value(cached_data_code)
            object_article = Article(**decode_cached_data)
            logger.debug(f"Получил данные по объекту - {id_object}")
            return object_article
        except (ConnectionError, TimeoutError) as conn_error:
            logger.error(f"Проблемы с подключением к Redis.\nПодробнее: {conn_error}")
        except (ResponseError, DataError) as req_error:
            logger.error(f"Ошибка в запросе.\nПодробнее: {req_error}")

    async def get_all_articles_by_date(self, date_: str) -> list[DisplayOnPageArticle]:
        try:
            data_from_redis: set[bytes] = await self.client.smembers(
                f"article:date:{date_}"
            )
            pipline_all_articles = self.client.pipeline()
            for key in data_from_redis:
                pipline_all_articles.hmget(
                    key.decode("utf-8"), "id", "title", "category", "views"
                )
            cached_data: list[list[bytes]] = await pipline_all_articles.execute()

            articles_decode: list[dict[str, str]] = [
                decode_info(article_data_bytes) for article_data_bytes in cached_data
            ]
            try:
                return [
                    DisplayOnPageArticle(**article_data)
                    for article_data in articles_decode
                ]
            except ValidationError as error:
                logger.debug(
                    f"Объект не прошел валидацию.\nПодробнее об ошибке: {error}"
                )
                raise ValidationError("Объект не прошел валидацию")
        except redis.ConnectionError as error:
            logger.debug(f"Ошибка при работе с Redis\nПодробнее: {error}")
            raise ConnectionError("Ошибка при работе с Redis")

    async def get_articles_by_date_category(
        self,
        date_: datetime.date,
        category: str,
    ) -> list[DisplayOnPageArticle]:
        try:
            article_ids = await self.client.sinter(
                f"article:date:{date_}", f"article:category:{category}"
            )
            category_pipline = self.client.pipeline()
            for article_id in article_ids:
                try:
                    await category_pipline.hmget(
                        article_id.decode("utf-8"), "id", "title", "category", "views"
                    )
                except (ValueError, AttributeError, TypeError) as error:
                    logger.error(f"Ошибка, связанная с {error}")
                    raise RedisError(f"Ошибка при работе с Redis.\nПодробнее: {error}")

            cached_code_articles: list[list[bytes]] = await category_pipline.execute()
            decode_cached_articles = [
                decode_info(article_info) for article_info in cached_code_articles
            ]
            try:
                return [
                    DisplayOnPageArticle(**article_info)
                    for article_info in decode_cached_articles
                ]
            except ValidationError as valid_error:
                logger.error(f"Объект не прошел валидацию.\nПодробнее {valid_error}")
                raise ValidationError("Объект не прошел валидацию")

        except redis.ConnectionError as error:
            logger.error(f"Redis Server недоступен. {error}")
            return {
                "status": "error",
                "desc": "Redis Server недоступен",
                "detail": error,
                "type": "connecton_type",
            }
        except Exception as error:
            logger.error(f"Неизвестная ошибка: {error}")
            return {
                "status": "error",
                "desc": "Непредвиденная ошибка",
                "detail": error,
                "type": "internal_error",
            }

    async def insert_articles(self, data: list[Articles_model]) -> None:
        assert data is not None, "Данные не могут быть пустыми"
        logger.debug("Вставка данных в Redis")
        try:
            for article in data:
                try:
                    published_at: str = datetime.datetime.strftime(
                        article.published_at, "%Y-%m-%d"
                    )
                    article_desc = article.description if article.description else ""
                    await self.client.hset(
                        f"article:id:{article.id}",
                        mapping={
                            "id": article.id,
                            "title": article.title,
                            "category": article.category,
                            "description": article_desc,
                            "views": article.views,
                            "published_at": published_at,
                            "content": article.content,
                        },
                    )
                    await self.client.sadd(
                        f"article:date:{published_at}", f"article:id:{article.id}"
                    )
                    await self.client.sadd(
                        f"article:category:{article.category}",
                        f"article:id:{article.id}",
                    )
                    logger.debug("Данные успешно вставленны в Redis")
                except (ValueError, KeyError, AttributeError) as error:
                    logger.error(
                        f"Произошла ошибка связанная с: {type(error).__name__}\
                        Подробнее: {error}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail=f"Ошибка при вставке даных в redis.\n \
                        Тип ошибки: {type(error).__name__}",
                    )
        except redis.ConnectionError as error:
            logger.error(f"Redis Server недоступен. {error}")
            return {
                "status": "error",
                "desc": "Redis Server недоступен",
                "detail": str(error),
                "type": "connection_type",
            }
        except Exception as error:
            logger.error(f"Ошибка типа: {type(error).__name__}\n{error}")
            return {
                "status": "error",
                "detail": str(error),
            }
