from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from loguru import logger
from redis import RedisError
from sqlalchemy.exc import SQLAlchemyError

from .models import Articles
from .service import (
    RedisDataManager,
    PostgresDataManager,
    RequestArticle,
)
from .utils import date_format
from ..config import base_config
from .schemas import Category, Article as Article_schema
from .dependencies import get_postgre_man, get_redis_man, get_request_man


article_router = APIRouter(tags=["articles"], prefix="/articles")

templates = Jinja2Templates(directory="templates/")


@article_router.get("/all")
async def display_all_articles(
    request: Request,
    redis_man: RedisDataManager = Depends(get_redis_man),
    postgre_man: PostgresDataManager = Depends(get_postgre_man),
    request_man: RequestArticle = Depends(get_request_man),
):
    published_at_filter: str = date_format()
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
            info_about_articles_by_category = {}
            for category in categories:
                request_info_about_articles: list[
                    dict
                ] = await request_man.request_article(
                    api_key=base_config.api_key, category=category
                )
                info_about_articles_by_category[category] = request_info_about_articles
            update_postgre_data = await postgre_man.insert_articles(
                info_about_articles_by_category
            )
            await redis_man.insert_articles(update_postgre_data)
    data_display_on_page = await redis_man.get_all_articles_by_date(
        date_=published_at_filter
    )
    return templates.TemplateResponse(
        "main.html", {"request": request, "articles": data_display_on_page}
    )


@article_router.get("/{category}")
async def display_specific_category(  # noqa: F811
    request: Request,
    category: Category,
    redis_man: RedisDataManager = Depends(get_redis_man),
    postgre_man: PostgresDataManager = Depends(get_postgre_man),
    request_man: RequestArticle = Depends(get_request_man),
):
    published_at_filter: str = date_format()
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
                base_config.api_key, category
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
        cached_data: Article_schema = await redis_man.get_specific_article(id_article)
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
            raise HTTPException(status_code=500, detail={
                "type": "db connection",
                "desc": "Не удается связаться с бд"
            })
    except Exception as error:
        logger.error(f"Неожиданная ошибка: {error}")
        
