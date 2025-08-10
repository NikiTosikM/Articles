from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, BaseModel


class RunSettings:
    host: str = "localhost"
    port: int = 8080
    

class DBSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    username: str = "postgres"
    name: str
    password: SecretStr


class RedisSettings(BaseModel):
    host: str
    port: int
    db_number: int = 0
    max_connection = 50
    
    
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="_",
        case_sensitive=False
    )
    api_key: str
    redis: RedisSettings 
    db: DBSettings       
    uvicorn: RunSettings = RunSettings() 
    

settings = Settings()

print(settings)