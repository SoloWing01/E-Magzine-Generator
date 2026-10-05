from app.database.database import SessionLocal
from app.database.models import Article


def cleanup():

    db = SessionLocal()

    try:
        deleted = (
            db.query(Article)
            .filter(Article.title == "Test Article")
            .delete(
                synchronize_session=False
            )
        )

        db.commit()

        print(
            f"Deleted {deleted} test article(s)."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    cleanup()