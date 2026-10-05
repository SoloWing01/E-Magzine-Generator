from app.database.database import SessionLocal
from app.database.models import Article


def article_exists(url: str) -> bool:
    """
    Check whether an article URL already exists.
    """

    db = SessionLocal()

    try:
        article = (
            db.query(Article)
            .filter(Article.url == url)
            .first()
        )

        return article is not None

    finally:
        db.close()


def save_article(article_data: dict):
    """
    Save an article to SQLite.

    Returns:
        Article object if saved.
        None if the article already exists.
    """

    db = SessionLocal()

    try:

        # Duplicate protection
        existing_article = (
            db.query(Article)
            .filter(
                Article.url == article_data["url"]
            )
            .first()
        )

        if existing_article:
            print(
                f"Duplicate article skipped: "
                f"{article_data['title']}"
            )

            return None

        article = Article(
            title=article_data["title"],
            url=article_data["url"],
            source=article_data["source"],
            author=article_data.get("author"),
            published_date=article_data.get(
                "published_date"
            ),
            content=article_data["content"],
            status="raw",
        )

        db.add(article)
        db.commit()
        db.refresh(article)

        print(
            f"Article saved successfully "
            f"(ID: {article.id})"
        )

        return article

    except Exception:

        db.rollback()
        raise

    finally:
        db.close()