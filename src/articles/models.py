from datetime import datetime, timedelta

from src.database import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Integer, DateTime, TIMESTAMP


class Articles(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(String(300))
    views: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[TIMESTAMP] = mapped_column(
        DateTime, default=lambda: datetime.now() - timedelta(days=1)
    )
    content: Mapped[str] = mapped_column(Text)
    
    def __repr__(self):
        return f"<Article(id={self.id}, category={self.category}, title={self.title})>"
