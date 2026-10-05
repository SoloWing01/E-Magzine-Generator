from app.database.database import SessionLocal
from app.database.models import Article
from app.nlp.relevance import NortheastRelevanceClassifier
from app.scoring.article_scorer import ArticleScorer


class ScoringPipeline:
    """
    Runs relevance classification and editorial scoring
    for all articles stored in SQLite.

    Flow:

    Article
        ↓
    Relevance Classification
        ↓
    Relevant?
        ↓
    Article Scoring
        ↓
    Save scores to database
        ↓
    Rank relevant articles
    """

    def __init__(self):
        self.classifier = NortheastRelevanceClassifier()
        self.scorer = ArticleScorer()

        self.stats = {
            "total": 0,
            "relevant": 0,
            "not_relevant": 0,
            "scored": 0,
            "failed": 0,
        }

    def classify_and_score(self, article):
        """
        Classify and score one article.
        """

        classification = self.classifier.classify(
            title=article.title,
            content=article.content,
        )

        classification_dict = classification.to_dict()

        # --------------------------------------------------
        # Save classification results
        # --------------------------------------------------

        article.relevance_score = int(
            classification_dict.get(
                "relevance_score",
                0
            )
        )

        article.northeast_score = int(
            classification_dict.get(
                "northeast_score",
                0
            )
        )

        article.security_score = int(
            classification_dict.get(
                "security_score",
                0
            )
        )

        article.development_score = int(
            classification_dict.get(
                "development_score",
                0
            )
        )

        article.society_score = int(
            classification_dict.get(
                "society_score",
                0
            )
        )

        article.sports_score = int(
            classification_dict.get(
                "sports_score",
                0
            )
        )

        article.category = classification_dict.get(
            "category"
        )

        # --------------------------------------------------
        # Check relevance
        # --------------------------------------------------

        if not classification_dict.get(
            "relevant",
            False
        ):
            article.article_score = 0
            article.theme_score = 0
            article.security_relevance_score = 0
            article.freshness_score = 0
            article.source_quality_score = 0
            article.content_quality_score = 0
            article.rank = None

            return False

        # --------------------------------------------------
        # Prepare article data for scorer
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
        # Calculate article score
        # --------------------------------------------------

        score = self.scorer.score_article(
            article=article_data,
            classification=classification_dict,
        )

        # --------------------------------------------------
        # Save scoring results
        # --------------------------------------------------

        article.article_score = int(
            round(score["final_score"])
        )

        article.theme_score = int(
            round(score["theme_relevance"])
        )

        article.security_relevance_score = int(
            round(score["security_relevance"])
        )

        article.freshness_score = int(
            round(score["freshness"])
        )

        article.source_quality_score = int(
            round(score["source_quality"])
        )

        article.content_quality_score = int(
            round(score["content_quality"])
        )

        return True

    def run(self):
        """
        Run scoring pipeline for all articles.
        """

        print("=" * 80)
        print("NORTHEAST SENTINEL - SCORING PIPELINE")
        print("=" * 80)

        db = SessionLocal()

        try:
            articles = (
                db.query(Article)
                .order_by(Article.id)
                .all()
            )

            self.stats["total"] = len(articles)

            print(
                f"\nTotal articles found: "
                f"{self.stats['total']}"
            )

            # --------------------------------------------------
            # First pass: classify and score
            # --------------------------------------------------

            print("\n[1] Classifying and scoring articles...")

            for index, article in enumerate(
                articles,
                start=1
            ):
                print(
                    f"\n[{index}/{len(articles)}] "
                    f"ID {article.id}: "
                    f"{article.title}"
                )

                try:
                    is_relevant = self.classify_and_score(
                        article
                    )

                    if is_relevant:
                        self.stats["relevant"] += 1
                        self.stats["scored"] += 1

                        print(
                            f"  Category : "
                            f"{article.category}"
                        )

                        print(
                            f"  Score    : "
                            f"{article.article_score}/100"
                        )

                    else:
                        self.stats["not_relevant"] += 1

                        print(
                            "  Status   : "
                            "Not Relevant"
                        )

                except Exception as e:
                    self.stats["failed"] += 1

                    print(
                        f"  ERROR: {e}"
                    )

            # --------------------------------------------------
            # Commit classification + scoring
            # --------------------------------------------------

            db.commit()

            print(
                "\nClassification and scoring saved."
            )

            # --------------------------------------------------
            # Second pass: calculate ranking
            # --------------------------------------------------

            print(
                "\n[2] Calculating article rankings..."
            )

            relevant_articles = (
                db.query(Article)
                .filter(
                    Article.relevance_score > 0,
                    Article.article_score > 0,
                )
                .order_by(
                    Article.article_score.desc(),
                    Article.published_date.desc(),
                )
                .all()
            )

            # --------------------------------------------------
            # Assign rank
            # --------------------------------------------------

            for rank, article in enumerate(
                relevant_articles,
                start=1
            ):
                article.rank = rank

            db.commit()

            # --------------------------------------------------
            # Print ranking
            # --------------------------------------------------

            print("\n")
            print("=" * 80)
            print("FINAL ARTICLE RANKING")
            print("=" * 80)

            for article in relevant_articles:
                print(
                    f"\nRank {article.rank:02d} | "
                    f"Score {article.article_score:03d} | "
                    f"ID {article.id}"
                )

                print(
                    f"Category: "
                    f"{article.category}"
                )

                print(
                    f"Title: "
                    f"{article.title}"
                )

            # --------------------------------------------------
            # Final statistics
            # --------------------------------------------------

            print("\n")
            print("=" * 80)
            print("SCORING PIPELINE SUMMARY")
            print("=" * 80)

            print(
                f"Total articles     : "
                f"{self.stats['total']}"
            )

            print(
                f"Relevant articles  : "
                f"{self.stats['relevant']}"
            )

            print(
                f"Not relevant       : "
                f"{self.stats['not_relevant']}"
            )

            print(
                f"Successfully scored: "
                f"{self.stats['scored']}"
            )

            print(
                f"Failed             : "
                f"{self.stats['failed']}"
            )

            print(
                f"Ranked articles    : "
                f"{len(relevant_articles)}"
            )

            print("=" * 80)

            return self.stats

        except Exception as e:
            db.rollback()

            print(
                f"\nScoring pipeline failed: {e}"
            )

            raise

        finally:
            db.close()


if __name__ == "__main__":
    pipeline = ScoringPipeline()
    pipeline.run()