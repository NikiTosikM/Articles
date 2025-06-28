from datetime import datetime, timedelta, date
import asyncio

import aiohttp
from sqlalchemy import insert, select, and_, cast, Date
from sqlalchemy.exc import DatabaseError
from loguru import logger

from .utils import date_format, datetime_format
from ..database import create_session
from .models import Articles


@logger.catch
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
                return data
        except aiohttp.client.ClientResponseError as error:
            logger.error(f"Статус API запроса {error.status}")
            return {
                "status": error.status,
                "url": error.request_info.url,
                "message": error.message,
            }
        except aiohttp.client.ClientError as error:
            logger.error(
                f"Ошибка при запросе новостей. URL: {url}. Date: {date}. Category: {category}. Description: {error}"
            )
            return {
                "status": "error",
                "message": "Возникла ошибка при попытке получить данные",
                "url": url,
                "description": error,
            }


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
            logger.error(f"Ошибка при занесесии данных в бд.Отсутствует поле: {error}")
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
            published_at_filter: date = datetime.now().date() - timedelta(days=2)
            query = select(Articles).where(
                and_(
                    Articles.category == category,
                    cast(Articles.published_at, Date) == published_at_filter,
                )
            ).limit(10)
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

        return {"status": "error", "description": "Произошла ошибка при работе с БД"}


asyncio.run(select_articles("yellow"))
