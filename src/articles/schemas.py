from enum import Enum

from pydantic import BaseModel, Field


class Categories(str, Enum):
    business = "business"
    entertainment = "entertainment"
    general = "general"
    health = "health"
    science = "science"
    sports = "sports"
    technology = "technology"


class Article(BaseModel):
    id: int
    category: Categories
    title: str = Field(max_length=150)
    description: str | None = Field(max_length=300)
    views: int
    published_at: str 