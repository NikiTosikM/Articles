import datetime

from sqlalchemy import select, and_, cast, Date, Result, update
from sqlalchemy.exc import (
    DatabaseError,
    OperationalError,
    TimeoutError as TimeoutErrorPostgre,
    NoResultFound,
    SQLAlchemyError,
    ProgrammingError,
)
from loguru import logger

from articles import Articles, create_session


class PostgresDataManager:
    async def insert_articles(self, articles: dict[str, list]) -> list[Articles]:
        assert articles is not None
        try:
            list_articles_objects = []
            async with create_session() as session:
                for category, list_articles in articles.items():
                    for article in list_articles:
                        published_at = article["publishedAt"]
                        date_publ = datetime.datetime.strptime(
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
                            await session.flush()
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

    async def get_specific_article(self, id_object: int) -> Articles:
        try:
            async with create_session() as session:
                query = select(Articles).where(id=id_object)
                result_request: Result = await session.execute(query)
                article_object = result_request.scalars().one()
                return article_object
        except (OperationalError, TimeoutErrorPostgre) as conn_error:
            logger.error(f"Проблема с подклчением к бд.\nПодробнее: {conn_error}")
            raise SQLAlchemyError()
        except (DatabaseError, NoResultFound) as req_error:
            logger.error(f"Ошибка при запроса в бд.\nПодробнее: {req_error}")
            raise SQLAlchemyError()

    async def select_all_articles(self, date_publish: str) -> list[Articles]:
        try:
            async with create_session() as session:
                publish_date = datetime.datetime.strptime(date_publish, "%Y-%m-%d").date()
                query = select(Articles).where(
                    cast(Articles.published_at, Date) == publish_date
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
                publish_date = datetime.datetime.strptime(date_publish, "%Y-%m-%d").date()
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

    async def update_info_object(self, id_object: int, field: str, value: any) -> None:
        try:
            async with create_session() as session:
                update_values = {field: Articles.__table__.c[field] + value}
                query = (
                    update(Articles)
                    .where(Articles.id == id_object)
                    .values(**update_values)
                )
                await session.execute(query)
        except (OperationalError, TimeoutErrorPostgre) as conn_error:
            logger.error(f"Ошибка при обращении к БД.\nПодробнее: {conn_error}")
            raise SQLAlchemyError("БД не отвечает")
        except ProgrammingError as sql_error:
            logger.error(
                f"Невозможно преобразовать запрос в sql.\nПодробнее: {sql_error}"
            )
            raise SQLAlchemyError("Ошибка синтаксиса")