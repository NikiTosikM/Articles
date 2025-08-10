import asyncio

from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from loguru import logger
from redis import RedisError
from sqlalchemy.exc import SQLAlchemyError
import aiohttp

from article.models.article_models import Articles
from article.service import (
    RedisDataManager,
    PostgresDataManager,
    RequestArticleApi
)
from article.schemas import Category, ArticleSchema
from api.dependencies import (
    get_postgre_man, 
    get_redis_man, 
    get_request_api_man
)
from article.utils import DateFormatter


article_router = APIRouter(tags=["articles"], prefix="/articles")

templates = Jinja2Templates(directory="templates/")


@article_router.get("/all")
async def display_all_articles(
    request: Request,
    redis_man: RedisDataManager = Depends(get_redis_man),
    postgre_man: PostgresDataManager = Depends(get_postgre_man),
    request_man: RequestArticleApi = Depends(get_request_api_man),
):
    published_at_filter: str = DateFormatter.converting_date_to_string(1)
    data_display_on_page: list[Articles] = []
    cached_data: list[Articles] | None = await redis_man.get_all_articles_by_date(
        published_at_filter
    )
    if not cached_data:
        data_from_postgre: list[Articles] = await postgre_man.select_all_articles(
            date_publish=published_at_filter
        )
        if data_from_postgre:
            await redis_man.insert_articles(data_from_postgre)
        else:
            categories = (
                "business",
                "entertainment",
                "general",
                "health",
                "science",
                "sports",
                "technology",
            )
            сategorization_news = {}
            tasks_get_info_from_api = []
            async with aiohttp.ClientSession() as client:
                for category in categories:
                    tasks_get_info_from_api.append(
                        request_man.request_article(
                        client=client,
                        category=category,
                        published_at=published_at_filter,
                    )
                )
                info_about_articles: list[list] = await asyncio.gather(*tasks_get_info_from_api)
            for i_categ, name_category in enumerate(categories):
                сategorization_news[name_category] = info_about_articles[i_categ]
            update_postgre_data = await postgre_man.insert_articles(
                сategorization_news
            )
            await redis_man.insert_articles(update_postgre_data)
    data_display_on_page = await redis_man.get_all_articles_by_date(
        date_=published_at_filter
    )
    return templates.TemplateResponse(
        "main.html", {"request": request, "articles": data_display_on_page}
    )


@article_router.get("/{category}")
async def display_specific_category(
    request: Request,
    category: Category,
    redis_man: RedisDataManager = Depends(get_redis_man),
    postgre_man: PostgresDataManager = Depends(get_postgre_man),
    request_man: RequestArticleApi = Depends(get_request_api_man),
):
    published_at_filter: str = DateFormatter.converting_date_to_string(1)
    data_display_on_page: list[Articles] = []
    data_redis: list[Articles] = await redis_man.get_articles_by_date_category(
        date_=published_at_filter, category=category
    )
    if not data_redis:
        data_postgre = await postgre_man.select_articles(
            category=category, date_publish=published_at_filter
        )
        if data_postgre:
            await redis_man.insert_articles(data_postgre)
        else:
            data_from_request: dict = await request_man.request_article(
                category=category
            )
            articles: list[Articles] = await postgre_man.insert_articles(
                data_from_request
            )
            await redis_man.insert_articles(articles)
    data_display_on_page = await redis_man.get_articles_by_date_category(
        date_=published_at_filter, category=category
    )

    return templates.TemplateResponse(
        "main.html", {"request": request, "articles": data_display_on_page}
    )


@article_router.get("/about/{id_article}")
async def detail_desc_article(
    id_article: int,
    request: Request,
    redis_man: RedisDataManager = Depends(get_redis_man),
    postgre_man: PostgresDataManager = Depends(get_postgre_man),
):
    logger.info(f"Открыл страницу объекта с ID - {id_article}")
    try:
        tasks_for_update_info_article = [
            redis_man.update_info(id_article, "views", 1),
            postgre_man.update_info_object(id_article, "views", 1),
        ]
        asyncio.gather(*tasks_for_update_info_article)
        cached_data: ArticleSchema = await redis_man.get_specific_article(id_article)
        return templates.TemplateResponse(
            "about_article.html", {"request": request, "article": cached_data}
        )
    except RedisError:
        try:
            postgre_data = await postgre_man.get_specific_article(id_article)
            return templates.TemplateResponse(
                "about_article.html", {"request": request, "article": postgre_data}
            )
        except SQLAlchemyError:
            raise HTTPException(
                status_code=500,
                detail={"type": "db connection", "desc": "Не удается связаться с бд"},
            )
    except Exception as error:
        logger.error(f"Неожиданная ошибка: {error}")
