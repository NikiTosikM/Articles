from datetime import datetime, date

import aiohttp
import redis
from sqlalchemy import insert, select, and_, cast, Date
from sqlalchemy.exc import DatabaseError
from loguru import logger
from redis import Redis, ConnectionPool

from .utils import date_format, datetime_format, decode_keys_and_value
from ..database import create_session
from .models import Articles
from ..config import redis_config


class RequestArticle:
    async def request_article(api_key: str, category: str) -> dict:
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
                    data["category"] = category
                    logger.debug("Запрос успешен. Никаких проблем не возникло")

                    return {"status": "ok", "data": data}

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
    async def insert_articles(articles) -> None:
        assert articles is not None
        values_for_db: list = []
        category: str = articles.get("category", None)
        for article in articles.get("articles"):
            date_publ: datetime = datetime_format(article["publishedAt"])
            try:
                values_for_db.append(
                    {
                        "category": category,
                        "title": article.get("title"),
                        "description": article.get("description"),
                        "published_at": date_publ,
                        "content": article.get("content"),
                    }
                )
            except KeyError as error:
                logger.error(
                    f"Ошибка при занесесии данных в бд.Отсутствует поле: {error}"
                )
        logger.debug("Список данных сформирован")
        try:
            async with create_session() as session:
                await session.execute(insert(Articles).values(values_for_db))
                logger.debug("Данные в бд успешно записаны")
        except DatabaseError as error:
            logger.error(f"Ошибка при работе с БД. {error}")

    async def select_articles(category: str) -> dict:
        try:
            async with create_session() as session:
                published_at_filter: date = date_format()
                query = (
                    select(Articles)
                    .where(
                        and_(
                            Articles.category == category,
                            cast(Articles.published_at, Date) == published_at_filter,
                        )
                    )
                    .limit(10)
                )
                logger.debug(
                    f"Запрос в бд с параметрами: {category}, {published_at_filter}"
                )
                articles: list = await session.execute(query)
                logger.debug(
                    f"Запрос выполнен успешно. Данные которые получил пользователь - {articles}"
                )
                responce = {"status": "ok", "data": articles}
                return responce
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

    async def get_articles_by_date_category(
        self,
        date_: date,
        category: str,
    ) -> list[Articles]:
        try:
            article_ids = await self.client.sinter(
                f"article:date:{date_}", f"article:category:{category}"
            )
            article_list: list[Articles] = []
            for article_id in article_ids:
                try:
                    article_data: dict[bytes, bytes] = await self.client.hgetall(
                        article_id.decode("utf-8")
                    )
                    article_decode = decode_keys_and_value(article_data)
                    object_data = Articles(**article_decode)
                    article_list.append(object_data)
                except (ValueError, AttributeError, TypeError) as error:
                    logger.error(f"Ошибка, связанная с {error}")
                    continue

            return {"status": "ok", "data": article_list}

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

    async def insert_articles(self, data: dict) -> dict | None:
        assert data["data"] is not None, "Данные не могут быть пустыми"
        logger.debug("Вставка данных в Redis")
        try:
            for article in data["data"]:
                try:
                    self.client.hset(
                        f"article:id:{article['id']}",
                        mapping={
                            "id": article["id"],
                            "category": article["category"],
                            "description": article["description"],
                            "views": article["views"],
                            "published_at": article["published_at"],
                            "content": article["content"],
                        },
                    )
                    date_for_set: date = datetime.strptime(article["date"], "%Y-%m-%d")
                    self.client.sadd(
                        f"article:date:{date_for_set}", f"article:id:{article['id']}"
                    )
                    self.client.sadd(
                        f"article:category:{article['category']}",
                        f"article:id:{article['id']}",
                    )
                    logger.debug("Данные успешно вставленны в Redis")
                except (ValueError, KeyError, AttributeError) as error:
                    logger.error(
                        f"Произошла ошибка связанная с: {type(error).__name__}"
                    )
                    return {
                        "status": "error",
                        "detail": str(error),
                        "type": type(error).__name__,
                    }
        except redis.ConnectionError as error:
            logger.error(f"Redis Server недоступен. {error}")
            return {
                "status": "error",
                "desc": "Redis Server недоступен",
                "detail": str(error),
                "type": "connection_type",
            }
        except Exception as error:
            logger.error(f"Ошибка типа: {type(error).__name__}")
            return {
                "status": "error",
                "detail": str(error),
                "type": type(error).__name__,
            }
