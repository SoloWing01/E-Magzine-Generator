from app.database.database import SessionLocal
from app.database.models import Article
from app.preprocessing.deduplicator import ArticleDeduplicator


def main():
    print("=" * 80)
    print("NORTHEAST SENTINEL - DEDUPLICATION TEST")
    print("=" * 80)

    db = SessionLocal()

    try:
        # --------------------------------------------------
        # Get relevant/scored articles from SQLite
        # --------------------------------------------------

        articles_db = (
            db.query(Article)
            .filter(
                Article.relevance_score > 0,
                Article.article_score > 0,
            )
            .order_by(Article.article_score.desc())
            .all()
        )

        print(
            f"\nRelevant articles loaded: "
            f"{len(articles_db)}"
        )

        # --------------------------------------------------
        # Convert SQLAlchemy objects to dictionaries
        # --------------------------------------------------

        articles = []

        for article in articles_db:
            articles.append(
                {
                    "id": article.id,
                    "title": article.title,
                    "url": article.url,
                    "source": article.source,
                    "published_date": article.published_date,
                    "content": article.content,
                    "category": article.category,
                    "article_score": article.article_score,
                }
            )

        # --------------------------------------------------
        # Run deduplication
        # --------------------------------------------------

        deduplicator = ArticleDeduplicator()

        unique_articles, duplicate_records = (
            deduplicator.deduplicate(
                articles
            )
        )

        # --------------------------------------------------
        # Display unique articles
        # --------------------------------------------------

        print("\n")
        print("=" * 80)
        print("UNIQUE ARTICLES")
        print("=" * 80)

        for index, article in enumerate(
            unique_articles,
            start=1,
        ):
            print(
                f"\n{index:02d}. "
                f"ID {article['id']} | "
                f"Score {article['article_score']}"
            )

            print(
                f"Category: "
                f"{article['category']}"
            )

            print(
                f"Title: "
                f"{article['title']}"
            )

        # --------------------------------------------------
        # Display duplicates
        # --------------------------------------------------

        print("\n")
        print("=" * 80)
        print("DUPLICATE DETECTION RESULTS")
        print("=" * 80)

        if not duplicate_records:
            print(
                "\nNo duplicate articles detected."
            )

        else:
            for index, duplicate in enumerate(
                duplicate_records,
                start=1,
            ):
                duplicate_article = (
                    duplicate["duplicate_article"]
                )

                matched_article = (
                    duplicate["matched_article"]
                )

                print(
                    f"\nDuplicate #{index}"
                )

                print(
                    f"Reason: "
                    f"{duplicate['reason']}"
                )

                print(
                    f"Similarity: "
                    f"{duplicate['similarity']}"
                )

                print(
                    f"Duplicate article:"
                )

                print(
                    f"  ID: "
                    f"{duplicate_article['id']}"
                )

                print(
                    f"  Title: "
                    f"{duplicate_article['title']}"
                )

                print(
                    f"Matched article:"
                )

                print(
                    f"  ID: "
                    f"{matched_article['id']}"
                )

                print(
                    f"  Title: "
                    f"{matched_article['title']}"
                )

        # --------------------------------------------------
        # Summary
        # --------------------------------------------------

        print("\n")
        print("=" * 80)
        print("DEDUPLICATION SUMMARY")
        print("=" * 80)

        print(
            f"Input articles       : "
            f"{len(articles)}"
        )

        print(
            f"Unique articles      : "
            f"{len(unique_articles)}"
        )

        print(
            f"Duplicate records    : "
            f"{len(duplicate_records)}"
        )

        print(
            f"Articles removed     : "
            f"{len(articles) - len(unique_articles)}"
        )

        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()