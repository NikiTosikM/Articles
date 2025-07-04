from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


logger.remove()

logger.add(
    sink="logging/log_info.log",
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:MM:SS}</green> | {level} | {message}",
)

logger.add(
    sink="logging/log_debug.log",
    level="DEBUG",
    format="<yellow>{time}</yellow>| {level} | {message} - {line} | {name}",
)


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    api_key: str = Field(..., alias="API_KEY")


class PostgreConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")
    host: str
    port: int
    username: str
    name: str
    password: int


class UvicornConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="UVICORN_", extra="ignore")
    port: int
    host: str


class RedisConfig(BaseConfig):
    model_config = SettingsConfigDict(env_prefix="RD_", extra="ignore")
    host: str
    port: int
    


postg_config = PostgreConfig()
uvicorn_config = UvicornConfig()
redis_config = RedisConfig()
