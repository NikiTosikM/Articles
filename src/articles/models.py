from datetime import datetime, timedelta

from src.database import Base
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy import String, Text, Integer, DateTime, TIMESTAMP
from loguru import logger


class Articles(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(String(300), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[TIMESTAMP] = mapped_column(
        DateTime, default=lambda: datetime.now() - timedelta(days=1)
    )
    content: Mapped[str] = mapped_column(Text)
    
    def __repr__(self):
        return f"<Article(id={self.id}, category={self.category}, title={self.title})>"
    
    @classmethod
    def validate_len_value(cls, str_value, max_len):
        if  len(str_value) > max_len:
            words_in_str = str_value.split()
            final_str = []
            for word in words_in_str:
                if len(" ".join(final_str)) + len(word) < max_len:
                    final_str.append(word)
                else:
                    break
            return " ".join(final_str)
        return str_value
    
    @logger.catch
    @validates("title")
    def validate_title(self, key, title):
       final_title = self.validate_len_value(title, 150) if title else None
       
       return final_title
    
    @logger.catch
    @validates("description")
    def validate_description(self, key, desc):
       final_desc = self.validate_len_value(desc, 300) if desc else None
       
       return final_desc

