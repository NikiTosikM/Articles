from fastapi import FastAPI
import uvicorn

from .config import uvicorn_config


app = FastAPI()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app", 
        port=uvicorn_config.port,
        host=uvicorn_config.host    
    )