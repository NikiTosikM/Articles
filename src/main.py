from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import uvicorn

from core import settings
from article.api import main_router


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(main_router)

@app.get("/")
async def main():
    return RedirectResponse("/articles/all")


if __name__ == "__main__":
    logger.info("Сервер запущен")
    uvicorn.run(
        "main:app", 
        port=settings.uvicorn.port, 
        host=settings.uvicorn.host, 
        reload=True
    )
    logger.info("Сервер остановлен")
