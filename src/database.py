from sqlalchemy import  MetaData
from sqlalchemy.orm import  DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from contextlib import asynccontextmanager

from .config import postg_config as post_conf


url_connect_db = ("postgresql+asyncpg://"
                f"{post_conf.username}:{post_conf.password}"
                f"@{post_conf.host}/{post_conf.name}"
            )
engine = create_async_engine(url_connect_db, echo=True)

async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
   metadata = MetaData()
   

@asynccontextmanager
async def create_session():
    async with async_session() as session:
        async with session.begin():
            yield session
    
    
    