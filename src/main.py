from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
import uvicorn

from core import settings



app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def main():
    return RedirectResponse("/articles/all")


if __name__ == "__main__":
    logger.info("Сервер запущен")
    uvicorn.run(
        "src.main:app", 
        port=settings.uvicorn.port, 
        host=settings.uvicorn.host, 
        reload=True
    )
    logger.info("Сервер остановлен")
