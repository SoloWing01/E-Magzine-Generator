from app.database.database import SessionLocal
from app.database.models import Article
from app.nlp.relevance import NortheastRelevanceClassifier
from app.scoring.article_scorer import ArticleScorer


def main():
    print("=" * 80)
    print("NORTHEAST SENTINEL - ARTICLE SCORING DEBUG TEST")
    print("=" * 80)

    db = SessionLocal()

    try:
        articles = (
            db.query(Article)
            .order_by(Article.id)
            .all()
        )

        print(f"\nTotal articles in database: {len(articles)}")

        classifier = NortheastRelevanceClassifier()
        scorer = ArticleScorer()

        scored_articles = []

        print("\nRunning relevance classification and scoring...")

        for article in articles:

            # --------------------------------------------------
            # 1. Run relevance classifier
            # --------------------------------------------------

            classification = classifier.classify(
                title=article.title,
                content=article.content,
            )

            classification_dict = classification.to_dict()

            # --------------------------------------------------
            # DEBUG
            # --------------------------------------------------

            if article.id == 29:
                print("\n")
                print("=" * 80)
                print("DEBUG CLASSIFICATION - ARTICLE ID 29")
                print("=" * 80)
                print(classification_dict)
                print("=" * 80)
                print("\n")

            # --------------------------------------------------
            # 2. Keep only relevant articles
            # --------------------------------------------------

            if not classification_dict.get("relevant", False):
                continue

            # --------------------------------------------------
            # 3. Prepare article data
            # --------------------------------------------------

            article_data = {
                "id": article.id,
                "title": article.title,
                "url": article.url,
                "source": article.source,
                "author": article.author,
                "published_date": article.published_date,
                "content": article.content,
            }

            # --------------------------------------------------
            # 4. Score article
            # --------------------------------------------------

            score = scorer.score_article(
                article=article_data,
                classification=classification_dict,
            )

            scored_articles.append(score)

        # ------------------------------------------------------
        # 5. Sort by final score
        # ------------------------------------------------------

        scored_articles.sort(
            key=lambda x: x["final_score"],
            reverse=True,
        )

        # ------------------------------------------------------
        # 6. Display ranking
        # ------------------------------------------------------

        print("\n")
        print("=" * 80)
        print("ARTICLE RANKING")
        print("=" * 80)

        if not scored_articles:
            print("\nNo relevant articles found.")
            return

        for rank, article in enumerate(
            scored_articles,
            start=1,
        ):
            print("\n" + "-" * 80)

            print(f"RANK: {rank}")
            print(f"ID: {article['article_id']}")
            print(f"TITLE: {article['title']}")
            print(f"SOURCE: {article['source']}")
            print(f"DATE: {article['published_date']}")
            print(f"CATEGORY: {article['category']}")

            print("\nSCORES:")

            print(
                f"  Northeast Relevance : "
                f"{article['northeast_relevance']:.2f}"
            )

            print(
                f"  Theme Relevance     : "
                f"{article['theme_relevance']:.2f}"
            )

            print(
                f"  Security Relevance  : "
                f"{article['security_relevance']:.2f}"
            )

            print(
                f"  Freshness           : "
                f"{article['freshness']:.2f}"
            )

            print(
                f"  Source Quality      : "
                f"{article['source_quality']:.2f}"
            )

            print(
                f"  Content Quality     : "
                f"{article['content_quality']:.2f}"
            )

            print(
                f"\nFINAL SCORE: "
                f"{article['final_score']:.2f} / 100"
            )

        # ------------------------------------------------------
        # 7. Summary
        # ------------------------------------------------------

        print("\n")
        print("=" * 80)
        print("SCORING SUMMARY")
        print("=" * 80)

        print(
            f"Total articles        : {len(articles)}"
        )

        print(
            f"Relevant articles     : {len(scored_articles)}"
        )

        print(
            f"Rejected articles     : "
            f"{len(articles) - len(scored_articles)}"
        )

        print(
            f"Highest score         : "
            f"{scored_articles[0]['final_score']:.2f}"
        )

        print(
            f"Lowest relevant score : "
            f"{scored_articles[-1]['final_score']:.2f}"
        )

        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()