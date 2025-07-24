from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from redis.exceptions import ConnectionError, ResponseError, DataError, TimeoutError as  TimeoutErrorRedis
from loguru import logger
from sqlalchemy.exc import (
    OperationalError,
    ProgrammingError,
    TimeoutError as TimeoutErrorDb,
    IntegrityError,
)

from .models import Articles
from .service import (
    RedisDataManager,
    PostgresDataManager,
    RequestArticle,
)
from .utils import date_format
from ..config import base_config
from .schemas import Category
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
    logger.info("Пользователь отправил запрос на получение всех статей")
    published_at_filter: str = date_format()
    data_display_on_page: list[Articles] = []
    try:
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
                    info_about_articles_by_category[category] = (
                        request_info_about_articles
                    )
                update_postgre_data = await postgre_man.insert_articles(
                    info_about_articles_by_category
                )
                await redis_man.insert_articles(update_postgre_data)
        data_display_on_page = await redis_man.get_all_articles_by_date(
            date_=published_at_filter
        )
        logger.info("Пользователь получил данные")
        return templates.TemplateResponse(
            "main.html", {"request": request, "articles": data_display_on_page}
        )

    except (ConnectionError, TimeoutErrorRedis) as redis_error_con:
        logger.error(f"Ошибка подключения к Redis.\nПодробнее: {redis_error_con}")
        try:
            data_from_postgre: list[Articles] = await postgre_man.select_all_articles(
                date_publish=published_at_filter
            )
            return templates.TemplateResponse(
                "main.html", {"request": request, "articles": data_from_postgre}
            )
        except (OperationalError, TimeoutErrorDb) as postgre_error:
            logger.error(f"Ошибка БД.\nПодробнее: {postgre_error}")
            raise HTTPException(
                status_code=500,
                detail="Сервис временно недоступен. Повторите ваш запрос чуть позже",
            )
        except (ProgrammingError, IntegrityError, DataError) as syntax_limit_error:
            logger.error(
                f"Нарушение синтаксиса или ограничений при sql запросе.\nПодробнее: {syntax_limit_error}"
            )
            raise HTTPException(
                status_code=500,
                detail="Ошибка при работе с базой данных. Повторите ваш запрос чуть позже",
            )
    except (ResponseError, DataError) as error:
        logger.error(f"Ошибка Redis.\nПодробнее: {error}")
        raise HTTPException(
            status_code=500,
            detail="Временные проблемы с данными. Попробуйте позже.",
        )
    except Exception as error:
        logger.debug(f"Неожиданная ошибка: {error}")


@article_router.get("/{category}")
async def display_specific_category(
    request: Request,
    category: Category,
    redis_man: RedisDataManager = Depends(get_redis_man),
    postgre_man: PostgresDataManager = Depends(get_postgre_man),
):
    logger.info(f"Пользователь перешел в категорию {category}")
    published_at_filter: str = date_format()
    data_display_on_page: list[Articles] = []
    try:
        caching_data: list[Articles] = await redis_man.get_articles_by_date_category(
            date_=published_at_filter, category=category
        )
        data_display_on_page = caching_data
    except (ConnectionError, TimeoutErrorRedis) as error:
        logger.error(f"Redis не отвечает на запросы.\nПодробнее: {error}")
        try:
            data_postgre: list[Articles] = await postgre_man.select_articles(
                category=category, date_publish=published_at_filter
            )
            data_display_on_page = data_postgre
        except (OperationalError, TimeoutErrorDb) as error:
            logger.error(f"Проблема с подключением к БД.\nПодробнее: {error}")
            raise HTTPException(
                status_code=500,
                detail="Проблема на стороне базы данных. Повторите ваш запрос чуть позже",
            )
        except (ProgrammingError, IntegrityError, DataError) as syntax_limit_error:
            logger.error(
                f"Нарушение синтаксиса или ограничений при sql запросе.\nПодробнее: {syntax_limit_error}"
            )
            raise HTTPException(
                status_code=500,
                detail="Ошибка при работе с базой данных. Повторите ваш запрос чуть позже",
            )
    except (ResponseError, DataError) as error:
        logger.error(f"Ошибка Redis.\nПодробнее: {error}")
        raise HTTPException(
            status_code=500,
            detail="Временные проблемы с данными. Попробуйте позже.",
        )
    except Exception as error:
        logger.error(f"Неожиданная ошибка: {error}")
    logger.info(f"Пользователь получил данные по статье {category}")
    return templates.TemplateResponse(
        "main.html", {"request": request, "articles": data_display_on_page}
    )
