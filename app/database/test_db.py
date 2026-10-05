from datetime import datetime

from app.database.database import SessionLocal
from app.database.models import Article


def test_database():
    db = SessionLocal()

    unique_url = (
        f"https://example.com/test-article-"
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    )

    article = Article(
        title="Test Article",
        url=unique_url,
        source="Test Source",
        content="This is a test article.",
        status="raw",
    )

    try:
        db.add(article)
        db.commit()
        db.refresh(article)

        print("Database test successful!")
        print(f"Article ID: {article.id}")
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")

    except Exception as e:
        db.rollback()
        print(f"Database test failed: {e}")

    finally:
        db.close()


if __name__ == "__main__":
    test_database()