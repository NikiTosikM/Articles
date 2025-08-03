from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import uvicorn

from .config import uvicorn_config
from .articles.router import article_router
from .articles.service import RedisDataManager, PostgresDataManager, RequestArticle


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_man = RedisDataManager()
    app.state.postgre_man = PostgresDataManager()
    app.state.request_man = RequestArticle()

    yield

    await app.state.redis_man.close()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def main():
    return RedirectResponse("/articles/all")


app.include_router(article_router)

if __name__ == "__main__":
    logger.info("Сервер запущен")
    uvicorn.run(
        "src.main:app", port=uvicorn_config.port, host=uvicorn_config.host
    )
    logger.info("Сервер остановлен")
