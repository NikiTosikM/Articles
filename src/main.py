from fastapi import FastAPI
from loguru import logger
import uvicorn

from .config import uvicorn_config


app = FastAPI()


if __name__ == "__main__":
    logger.info("Сервер запущен")
    uvicorn.run(
        "src.main:app", 
        port=uvicorn_config.port,
        host=uvicorn_config.host    
    )
    logger.info("Сервер остановлен")