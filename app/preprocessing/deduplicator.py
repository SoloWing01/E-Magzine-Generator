"""
Northeast Sentinel
==================

Phase 7 — Article Deduplication

Detects duplicate or highly similar Northeast news articles.

Current methods:

1. Exact URL matching
2. Normalized title matching
3. Title similarity
4. Basic content similarity

Semantic embedding-based deduplication can be added in a later
phase when embeddings are already available.

IMPORTANT:
This module does NOT delete articles from SQLite.

It only identifies duplicates and produces the unique article
set for validation.
"""

import re

from difflib import SequenceMatcher


from app.database.database import SessionLocal
from app.database.models import Article


class ArticleDeduplicator:
    """
    Detects duplicate or highly similar articles.

    Current version uses:

    1. Exact URL matching
    2. Normalized title matching
    3. Title similarity
    4. Basic content similarity

    Semantic embedding-based deduplication will be added later.
    """

    # ==========================================================
    # Thresholds
    # ==========================================================

    TITLE_SIMILARITY_THRESHOLD = 0.85

    CONTENT_SIMILARITY_THRESHOLD = 0.90

    # ==========================================================
    # Initialization
    # ==========================================================

    def __init__(self):
        self.seen_urls = set()

        self.seen_titles = {}

    # ==========================================================
    # Text normalization
    # ==========================================================

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for comparison.
        """

        if not text:
            return ""

        text = str(text).lower()

        # ------------------------------------------------------
        # Remove punctuation
        # ------------------------------------------------------

        text = re.sub(
            r"[^\w\s]",
            " ",
            text,
        )

        # ------------------------------------------------------
        # Remove extra whitespace
        # ------------------------------------------------------

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ==========================================================
    # URL duplicate detection
    # ==========================================================

    def is_duplicate_url(
        self,
        url: str,
    ) -> bool:
        """
        Check whether URL has already been seen.
        """

        if not url:
            return False

        normalized_url = (
            url.strip().lower()
        )

        if normalized_url in self.seen_urls:
            return True

        self.seen_urls.add(
            normalized_url
        )

        return False

    # ==========================================================
    # Title similarity
    # ==========================================================

    def title_similarity(
        self,
        title_a: str,
        title_b: str,
    ) -> float:
        """
        Calculate similarity between two titles.
        """

        title_a = self.normalize_text(
            title_a
        )

        title_b = self.normalize_text(
            title_b
        )

        if not title_a or not title_b:
            return 0.0

        if title_a == title_b:
            return 1.0

        return SequenceMatcher(
            None,
            title_a,
            title_b,
        ).ratio()

    # ==========================================================
    # Content similarity
    # ==========================================================

    def content_similarity(
        self,
        content_a: str,
        content_b: str,
    ) -> float:
        """
        Calculate basic similarity between article contents.

        This is intentionally conservative because large article
        bodies can be expensive to compare.
        """

        content_a = self.normalize_text(
            content_a
        )

        content_b = self.normalize_text(
            content_b
        )

        if not content_a or not content_b:
            return 0.0

        if content_a == content_b:
            return 1.0

        # ------------------------------------------------------
        # Compare first 5000 characters.
        #
        # This provides a lightweight baseline.
        # ------------------------------------------------------

        content_a = content_a[:5000]

        content_b = content_b[:5000]

        return SequenceMatcher(
            None,
            content_a,
            content_b,
        ).ratio()

    # ==========================================================
    # Duplicate detection
    # ==========================================================

    def find_duplicate(
        self,
        article: dict,
        existing_articles: list[dict],
    ) -> dict | None:
        """
        Find whether an article duplicates an existing article.

        Returns information about the duplicate when found.

        Otherwise returns None.
        """

        article_url = article.get(
            "url",
            "",
        )

        article_title = article.get(
            "title",
            "",
        )

        article_content = article.get(
            "content",
            "",
        )

        # ======================================================
        # 1. URL duplicate
        # ======================================================

        for existing in existing_articles:

            existing_url = existing.get(
                "url",
                "",
            )

            if (
                article_url
                and existing_url
                and article_url.strip().lower()
                == existing_url.strip().lower()
            ):
                return {
                    "duplicate": True,
                    "reason": "exact_url",
                    "similarity": 1.0,
                    "matched_article": existing,
                }

        # ======================================================
        # 2. Title duplicate / similarity
        # ======================================================

        for existing in existing_articles:

            existing_title = existing.get(
                "title",
                "",
            )

            similarity = self.title_similarity(
                article_title,
                existing_title,
            )

            if (
                similarity
                >= self.TITLE_SIMILARITY_THRESHOLD
            ):
                return {
                    "duplicate": True,
                    "reason": "similar_title",
                    "similarity": round(
                        similarity,
                        4,
                    ),
                    "matched_article": existing,
                }

        # ======================================================
        # 3. Content similarity
        # ======================================================

        for existing in existing_articles:

            existing_content = existing.get(
                "content",
                "",
            )

            similarity = self.content_similarity(
                article_content,
                existing_content,
            )

            if (
                similarity
                >= self.CONTENT_SIMILARITY_THRESHOLD
            ):
                return {
                    "duplicate": True,
                    "reason": "similar_content",
                    "similarity": round(
                        similarity,
                        4,
                    ),
                    "matched_article": existing,
                }

        return None

    # ==========================================================
    # Select article to keep
    # ==========================================================

    @staticmethod
    def choose_best_article(
        article_a: dict,
        article_b: dict,
    ) -> dict:
        """
        Choose the better article when two articles are
        duplicates.

        Primary criterion:
            article_score

        Secondary criterion:
            content length
        """

        score_a = article_a.get(
            "article_score",
            0,
        )

        score_b = article_b.get(
            "article_score",
            0,
        )

        # ------------------------------------------------------
        # Compare article scores
        # ------------------------------------------------------

        if score_a > score_b:
            return article_a

        if score_b > score_a:
            return article_b

        # ------------------------------------------------------
        # If scores are equal, compare content length
        # ------------------------------------------------------

        content_a = len(
            article_a.get(
                "content",
                "",
            )
        )

        content_b = len(
            article_b.get(
                "content",
                "",
            )
        )

        if content_a >= content_b:
            return article_a

        return article_b

    # ==========================================================
    # Deduplicate a list of articles
    # ==========================================================

    def deduplicate(
        self,
        articles: list[dict],
    ) -> tuple[list[dict], list[dict]]:
        """
        Deduplicate articles.

        Returns:

            unique_articles
            duplicate_records
        """

        unique_articles = []

        duplicate_records = []

        # ------------------------------------------------------
        # Process articles one by one
        # ------------------------------------------------------

        for article in articles:

            duplicate = self.find_duplicate(
                article,
                unique_articles,
            )

            # --------------------------------------------------
            # Article is unique
            # --------------------------------------------------

            if duplicate is None:

                unique_articles.append(
                    article
                )

                continue

            # --------------------------------------------------
            # Duplicate found
            # --------------------------------------------------

            matched_article = duplicate[
                "matched_article"
            ]

            # --------------------------------------------------
            # Select the better article
            # --------------------------------------------------

            best_article = (
                self.choose_best_article(
                    article,
                    matched_article,
                )
            )

            # --------------------------------------------------
            # Save duplicate information
            # --------------------------------------------------

            duplicate_records.append(
                {
                    "duplicate_article": article,
                    "matched_article": matched_article,
                    "reason": duplicate[
                        "reason"
                    ],
                    "similarity": duplicate[
                        "similarity"
                    ],
                }
            )

            # --------------------------------------------------
            # Replace existing article if the new article
            # has a higher score / better content
            # --------------------------------------------------

            if best_article is article:

                index = (
                    unique_articles.index(
                        matched_article
                    )
                )

                unique_articles[index] = (
                    article
                )

        return (
            unique_articles,
            duplicate_records,
        )


# ==============================================================
# DATABASE PIPELINE
# ==============================================================

def run_deduplication():
    """
    Phase 7 — Article Deduplication

    Reads relevant articles from SQLite and runs the
    deduplication process.

    IMPORTANT:

    This function does NOT delete anything from the database.

    It only reports:
        - number of relevant articles
        - number of unique articles
        - number of duplicates
        - duplicate reasons
        - similarity values
        - final unique article ranking
    """

    print("=" * 80)

    print(
        "NORTHEAST SENTINEL - "
        "DEDUPLICATION PIPELINE"
    )

    print("=" * 80)

    session = SessionLocal()

    try:

        # ======================================================
        # STEP 1 — LOAD RELEVANT ARTICLES
        # ======================================================

        articles_db = (
            session
            .query(Article)
            .filter(
                Article.category.isnot(None),
                Article.category != "Not Relevant",
            )
            .order_by(
                Article.article_score.desc()
            )
            .all()
        )

        print()

        print(
            f"Relevant articles found: "
            f"{len(articles_db)}"
        )

        # ------------------------------------------------------
        # No relevant articles
        # ------------------------------------------------------

        if not articles_db:

            print()

            print(
                "No relevant articles found."
            )

            return

        # ======================================================
        # STEP 2 — CONVERT DATABASE OBJECTS TO DICTIONARIES
        # ======================================================

        articles = []

        for article in articles_db:

            article_data = {
                "id": article.id,

                "article_id": article.id,

                "title": (
                    article.title
                    or ""
                ),

                "url": (
                    article.url
                    or ""
                ),

                "content": (
                    article.content
                    or ""
                ),

                "category": (
                    article.category
                    or ""
                ),

                "article_score": (
                    article.article_score
                    if article.article_score is not None
                    else 0
                ),

                "source": (
                    getattr(
                        article,
                        "source",
                        "",
                    )
                    or ""
                ),
            }

            articles.append(
                article_data
            )

        # ======================================================
        # STEP 3 — RUN DEDUPLICATION
        # ======================================================

        print()

        print(
            "[1] Running duplicate detection..."
        )

        deduplicator = (
            ArticleDeduplicator()
        )

        (
            unique_articles,
            duplicate_records,
        ) = deduplicator.deduplicate(
            articles
        )

        # ======================================================
        # STEP 4 — BASIC RESULTS
        # ======================================================

        print()

        print("=" * 80)

        print(
            "DEDUPLICATION RESULTS"
        )

        print("=" * 80)

        print()

        print(
            f"Input articles       : "
            f"{len(articles)}"
        )

        print(
            f"Unique articles      : "
            f"{len(unique_articles)}"
        )

        print(
            f"Duplicate articles   : "
            f"{len(duplicate_records)}"
        )

        # ======================================================
        # STEP 5 — DUPLICATE DETAILS
        # ======================================================

        if not duplicate_records:

            print()

            print(
                "No duplicate articles detected."
            )

        else:

            print()

            print(
                "DUPLICATE ARTICLES"
            )

            print(
                "-" * 80
            )

            for index, record in enumerate(
                duplicate_records,
                start=1,
            ):

                duplicate_article = (
                    record[
                        "duplicate_article"
                    ]
                )

                matched_article = (
                    record[
                        "matched_article"
                    ]
                )

                reason = (
                    record[
                        "reason"
                    ]
                )

                similarity = (
                    record[
                        "similarity"
                    ]
                )

                duplicate_id = (
                    duplicate_article.get(
                        "article_id"
                    )
                )

                matched_id = (
                    matched_article.get(
                        "article_id"
                    )
                )

                duplicate_title = (
                    duplicate_article.get(
                        "title",
                        "Untitled",
                    )
                )

                matched_title = (
                    matched_article.get(
                        "title",
                        "Untitled",
                    )
                )

                duplicate_score = (
                    duplicate_article.get(
                        "article_score",
                        0,
                    )
                )

                matched_score = (
                    matched_article.get(
                        "article_score",
                        0,
                    )
                )

                print()

                print(
                    f"[{index}] "
                    f"Duplicate Article ID: "
                    f"{duplicate_id}"
                )

                print(
                    f"Title      : "
                    f"{duplicate_title}"
                )

                print(
                    f"Score      : "
                    f"{duplicate_score}"
                )

                print()

                print(
                    f"Matched ID : "
                    f"{matched_id}"
                )

                print(
                    f"Matched    : "
                    f"{matched_title}"
                )

                print(
                    f"Score      : "
                    f"{matched_score}"
                )

                print()

                print(
                    f"Reason     : "
                    f"{reason}"
                )

                print(
                    f"Similarity : "
                    f"{similarity:.4f}"
                )

        # ======================================================
        # STEP 6 — FINAL UNIQUE ARTICLE SET
        # ======================================================

        print()

        print("=" * 80)

        print(
            "FINAL UNIQUE ARTICLE SET"
        )

        print("=" * 80)

        for rank, article in enumerate(
            unique_articles,
            start=1,
        ):

            score = article.get(
                "article_score",
                0,
            )

            try:
                score_display = (
                    f"{float(score):.0f}"
                )
            except (
                TypeError,
                ValueError,
            ):
                score_display = "0"

            print()

            print(
                f"Rank {rank:02d} | "
                f"ID {article.get('article_id')} | "
                f"Score {score_display}"
            )

            print(
                f"Category : "
                f"{article.get('category', '')}"
            )

            print(
                f"Title    : "
                f"{article.get('title', '')}"
            )

        # ======================================================
        # STEP 7 — FINAL SUMMARY
        # ======================================================

        print()

        print("=" * 80)

        print(
            "PHASE 7 DEDUPLICATION COMPLETE"
        )

        print("=" * 80)

        print()

        print(
            f"Original relevant articles : "
            f"{len(articles)}"
        )

        print(
            f"Unique articles            : "
            f"{len(unique_articles)}"
        )

        print(
            f"Duplicates detected        : "
            f"{len(duplicate_records)}"
        )

        print()

        if duplicate_records:

            duplicate_percentage = (
                len(duplicate_records)
                / len(articles)
                * 100
            )

            print(
                f"Duplicate percentage      : "
                f"{duplicate_percentage:.2f}%"
            )

        else:

            print(
                "Duplicate percentage      : "
                "0.00%"
            )

        print()

        print(
            "Database records were NOT "
            "deleted or modified."
        )

        print(
            "This phase only validates "
            "the deduplication result."
        )

        print()

    except Exception as exc:

        session.rollback()

        print()

        print("=" * 80)

        print(
            "PHASE 7 FAILED"
        )

        print("=" * 80)

        print()

        print(
            f"Error: {exc}"
        )

        raise

    finally:

        session.close()


# ==============================================================
# ENTRY POINT
# ==============================================================

def main():
    """
    Command-line entry point.
    """

    run_deduplication()


if __name__ == "__main__":
    main()