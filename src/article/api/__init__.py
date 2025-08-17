from fastapi import APIRouter

from .router import article_router


main_router = APIRouter()

main_router.include_router(article_router)