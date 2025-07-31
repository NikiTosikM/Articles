from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    business = "business"
    entertainment = "entertainment"
    general = "general"
    health = "health"
    science = "science"
    sports = "sports"
    technology = "technology"
    
    def __str__(self):
        return self.value


class Article(BaseModel):
    id: int
    category: Category
    title: str = Field(max_length=150)
    description: str | None = Field(max_length=300)
    views: int
    published_at: str 
    

class DisplayOnPageArticle(BaseModel):
    id: int
    title: str
    category: Category
    views: int