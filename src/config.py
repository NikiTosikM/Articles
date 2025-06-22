import sys

from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict


logger.remove()

logger.add(
    sink="logging.log",
    level="DEBUG", 
    format = "<green>{time}<green> | {level} | {message}"
    )



class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )


class UvicornConfig(BaseConfig):
    model_config = SettingsConfigDict(
        env_prefix="UVICORN_"
    )
    port: int
    host: str
    
    
uvicorn_config = UvicornConfig()