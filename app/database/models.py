from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(500), nullable=False)

    url = Column(String(1000), unique=True, nullable=False)

    source = Column(String(200), nullable=False)

    author = Column(String(300), nullable=True)

    published_date = Column(DateTime, nullable=True)

    content = Column(Text, nullable=False)

    relevance_score = Column(Integer, default=0, nullable=False)

    northeast_score = Column(Integer, default=0, nullable=False)
    security_score = Column(Integer, default=0, nullable=False)
    development_score = Column(Integer, default=0, nullable=False)
    society_score = Column(Integer, default=0, nullable=False)
    sports_score = Column(Integer, default=0, nullable=False)

    category = Column(String(100), nullable=True)

    article_score = Column(Integer, default=0, nullable=False)

    theme_score = Column(Integer, default=0, nullable=False)
    security_relevance_score = Column(Integer, default=0, nullable=False)
    freshness_score = Column(Integer, default=0, nullable=False)
    source_quality_score = Column(Integer, default=0, nullable=False)
    content_quality_score = Column(Integer, default=0, nullable=False)

    rank = Column(Integer, nullable=True)

    scraped_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    status = Column(
        String(50),
        default="raw",
        nullable=False,
    )

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title}')>"