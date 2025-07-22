from datetime import datetime, date

import aiohttp
import redis
from redis.asyncio import Redis, ConnectionPool
from sqlalchemy import select, and_, cast, Date, Result
from sqlalchemy.exc import DatabaseError
from loguru import logger
from fastapi.exceptions import HTTPException
from fastapi import status
from pydantic import ValidationError

from .utils import date_format, decode_keys_and_value
from ..database import create_session
from .models import Articles
from ..config import redis_config
from .schemas import Article as Article_schema


class RequestArticle:
    async def request_article(self, api_key: str, category: str) -> dict:
        date: str = date_format()
        async with aiohttp.ClientSession() as client:
            try:
                url = (
                    "https://newsapi.org/v2/everything"
                    f"?q={category}"
                    "&searchIn=title"
                    "&language=en"
                    f"&from={date}"
                    f"&to={date}"
                    f"&apiKey={api_key}"
                )
                async with client.get(url) as response:
                    data = await response.json()
                    assert isinstance(data, dict)
                    logger.debug("Данные от API полученны")
                    if data.get("status", None) != "ok":
                        raise aiohttp.client.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"Статус ответа {response.status}",
                        )
                    logger.debug("Запрос успешен. Никаких проблем не возникло")
                    return data["articles"]
            except aiohttp.client.ClientResponseError as error:
                logger.error(f"Статус API запроса {error.status}")
                return {
                    "status": error.status,
                    "url": error.request_info.url,
                    "message": error.message,
                }
            except aiohttp.client.ClientError as error:
                logger.error(
                    f"Ошибка при запросе новостей. URL: {url}. Date: {date}. Category: {category}. Description: {str(error)}"
                )
                return {
                    "status": "error",
                    "message": "Возникла ошибка при попытке получить данные",
                    "url": url,
                    "description": str(error),
                }


class PostgresDataManager:
    async def insert_articles(self, articles: dict[str, list]) -> list[Articles]:
        assert articles is not None
        try:
            list_articles_objects = []
            async with create_session() as session:
                for category, list_articles in articles.items():
                    for article in list_articles:
                        published_at = article["publishedAt"]
                        date_publ = datetime.strptime(
                            published_at, "%Y-%m-%dT%H:%M:%SZ"
                        )
                        try:
                            article_model_object = Articles(
                                category=category,
                                title=article.get("title"),
                                description=article.get("description"),
                                published_at=date_publ,
                                content=article.get("content"),
                            )
                            session.add(article_model_object)
                            session.flush()
                            list_articles_objects.append(article_model_object)
                            logger.debug(
                                f"Данные в бд успешно записаны. ID: {article_model_object.id}"
                            )
                        except DatabaseError as error:
                            logger.error(f"Ошибка при работе с БД. {error}")
                    logger.debug("Список данных сформирован")
                await session.commit()
                return list_articles_objects

        except KeyError as error:
            logger.error(f"Ошибка при занесесии данных в бд.Отсутствует поле: {error}")
        except Exception as error:
            logger.error(f"Ошибка с БД: {error}")

    async def select_all_articles(self, date_publish: str) -> list[Articles]:
        try:
            async with create_session() as session:
                publish_date = datetime.strptime(date_publish, "%Y-%m-%d").date()
                query = (
                    select(Articles)
                    .where(cast(Articles.published_at, Date) == publish_date)
                )
                logger.debug(
                    f"Запрос для получения всех статей с датой: {date_publish}"
                )
                articles_responce: Result = await session.execute(query)
                logger.debug("Запрос выполнен успешно. Все статьи полученны ")
                articles_list: list = articles_responce.scalars().all()

                return articles_list
        except DatabaseError as error:
            logger.error(f"Ошибка при работе с БД. {error}")
            return {
                "status": "error",
                "description": "Произошла ошибка при работе с БД при получении всех статей",
            }

    async def select_articles(self, category: str, date_publish: str) -> list[Articles]:
        try:
            async with create_session() as session:
                publish_date = datetime.strptime(date_publish, "%Y-%m-%d").date()
                query = (
                    select(Articles)
                    .where(
                        and_(
                            Articles.category == category,
                            cast(Articles.published_at, Date) == publish_date,
                        )
                    )
                    .limit(10)
                )
                logger.debug(f"Запрос в бд с параметрами: {category}, {date_publish}")
                articles_responce: Result = await session.execute(query)
                logger.debug(
                    f"Запрос выполнен успешно. Данные которые получил пользователь - {articles_responce}"
                )
                articles_list: list = articles_responce.scalars().all()

                return articles_list
        except DatabaseError as error:
            logger.error(f"Ошибка при работе с БД. {error}")

            return {
                "status": "error",
                "description": "Произошла ошибка при работе с БД",
            }


class RedisDataManager:
    host = redis_config.host
    port = redis_config.port
    max_connection = 10

    def __init__(self):
        self.pool = ConnectionPool(
            host=self.host, port=self.port, max_connections=self.max_connection
        )
        self.client: Redis = Redis(connection_pool=self.pool)

    async def close(self):
        await self.client.close()

    async def get_all_articles_by_date(self, date_: str) -> list[Articles]:
        article_list_objects = []
        try:
            data_from_redis: set[bytes] = await self.client.smembers(
                f"article:date:{date_}"
            )
            for key in data_from_redis:
                article_data_bytes: dict[bytes, bytes] = await self.client.hgetall(
                    key.decode("utf-8")
                )
                article_decode: dict = decode_keys_and_value(article_data_bytes)
                try:
                    object_schema = Article_schema(**article_decode)
                except ValidationError as error:
                    logger.debug(
                        f"Объект не прошел валидацию.\nПодробнее об ошибке: {error}"
                    )
                    raise ValidationError("Объект не прошел валидацию")
                article_list_objects.append(object_schema)

            return article_list_objects
        except redis.ConnectionError as error:
            logger.debug(f"Ошибка при работе с Redis\nПодробнее: {error}")
            raise ConnectionError("Ошибка при работе с Redis")

    async def get_articles_by_date_category(
        self,
        date_: date,
        category: str,
    ) -> list[Articles]:
        try:
            article_ids = await self.client.sinter(
                f"article:date:{date_}", f"article:category:{category}"
            )
            article_list = []
            for article_id in article_ids:
                try:
                    article_data: dict[bytes, bytes] = await self.client.hgetall(
                        article_id.decode("utf-8")
                    )
                    article_decode = decode_keys_and_value(article_data)
                    object_data = Article_schema(**article_decode)
                    article_list.append(object_data)
                except (ValueError, AttributeError, TypeError) as error:
                    logger.error(f"Ошибка, связанная с {error}")
                    continue

            return article_list

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

    async def insert_articles(self, data: list[Articles]) -> None:
        assert data is not None, "Данные не могут быть пустыми"
        logger.debug("Вставка данных в Redis")
        try:
            for article in data:
                try:
                    published_at: str = datetime.strftime(
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
