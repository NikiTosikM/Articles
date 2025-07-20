from fastapi import Request, APIRouter, Depends
from fastapi.templating import Jinja2Templates

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
    request: Request, redis_man: RedisDataManager = Depends(get_redis_man)
):
    return templates.TemplateResponse("main.html", {"request": request})


@article_router.get("/{category}")
async def display_specific_category (  # noqa: F811
    request: Request,
    category: Category,
    redis_man: RedisDataManager = Depends(get_redis_man),
    postgre_man: PostgresDataManager = Depends(get_postgre_man),
    request_man: RequestArticle = Depends(get_request_man),
) -> list[Article_schema]:
    published_at_filter: str = date_format()
    data_display_on_page: list[Articles] = []
    data_redis: list[Articles] = await redis_man.get_articles_by_date_category(
        date_=published_at_filter, category=category
    )
    if not data_redis:
        data_postgre = await postgre_man.select_articles(category=category, date_publish=published_at_filter)
        if data_postgre:
            await redis_man.insert_articles(data_postgre)
        else:
            data_from_request: dict = await request_man.request_article(
                base_config.api_key, category
            )
            articles:list[Articles] = await postgre_man.insert_articles(data_from_request)
            await redis_man.insert_articles(articles)
    data_display_on_page = await redis_man.get_articles_by_date_category(
        date_=published_at_filter, category=category
    )

    return templates.TemplateResponse(
        "main.html", {"request": request, "articles": data_display_on_page}
    )
