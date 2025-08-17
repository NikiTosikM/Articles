from sqlalchemy import  MetaData
from sqlalchemy.orm import  DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from contextlib import asynccontextmanager

from core import settings


url_connect_db = settings.db.create_db_connection_url
engine = create_async_engine(
    url_connect_db
)

async_session = async_sessionmaker(engine, class_=AsyncSession ,expire_on_commit=False)


class Base(DeclarativeBase):
   metadata = MetaData()
   

@asynccontextmanager
async def create_session():
    async with async_session() as session:
        async with session.begin():
            yield session
    
    
    