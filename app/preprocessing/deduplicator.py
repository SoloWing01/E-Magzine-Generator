import re
from difflib import SequenceMatcher


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

    # Thresholds
    TITLE_SIMILARITY_THRESHOLD = 0.85
    CONTENT_SIMILARITY_THRESHOLD = 0.90

    def __init__(self):
        self.seen_urls = set()
        self.seen_titles = {}

    # ----------------------------------------------------------
    # Text normalization
    # ----------------------------------------------------------

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for comparison.
        """

        if not text:
            return ""

        text = text.lower()

        # Remove punctuation
        text = re.sub(
            r"[^\w\s]",
            " ",
            text,
        )

        # Remove extra whitespace
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ----------------------------------------------------------
    # URL duplicate detection
    # ----------------------------------------------------------

    def is_duplicate_url(self, url: str) -> bool:
        """
        Check whether URL has already been seen.
        """

        if not url:
            return False

        normalized_url = url.strip().lower()

        if normalized_url in self.seen_urls:
            return True

        self.seen_urls.add(normalized_url)

        return False

    # ----------------------------------------------------------
    # Title similarity
    # ----------------------------------------------------------

    def title_similarity(
        self,
        title_a: str,
        title_b: str,
    ) -> float:
        """
        Calculate similarity between two titles.
        """

        title_a = self.normalize_text(title_a)
        title_b = self.normalize_text(title_b)

        if not title_a or not title_b:
            return 0.0

        if title_a == title_b:
            return 1.0

        return SequenceMatcher(
            None,
            title_a,
            title_b,
        ).ratio()

    # ----------------------------------------------------------
    # Content similarity
    # ----------------------------------------------------------

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

        content_a = self.normalize_text(content_a)
        content_b = self.normalize_text(content_b)

        if not content_a or not content_b:
            return 0.0

        if content_a == content_b:
            return 1.0

        # Compare first 5000 characters.
        # This provides a lightweight baseline.
        content_a = content_a[:5000]
        content_b = content_b[:5000]

        return SequenceMatcher(
            None,
            content_a,
            content_b,
        ).ratio()

    # ----------------------------------------------------------
    # Duplicate detection
    # ----------------------------------------------------------

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

        article_url = article.get("url", "")
        article_title = article.get("title", "")
        article_content = article.get("content", "")

        # ------------------------------------------------------
        # 1. URL duplicate
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # 2. Title duplicate / similarity
        # ------------------------------------------------------

        for existing in existing_articles:

            existing_title = existing.get(
                "title",
                "",
            )

            similarity = self.title_similarity(
                article_title,
                existing_title,
            )

            if similarity >= self.TITLE_SIMILARITY_THRESHOLD:

                return {
                    "duplicate": True,
                    "reason": "similar_title",
                    "similarity": round(
                        similarity,
                        4,
                    ),
                    "matched_article": existing,
                }

        # ------------------------------------------------------
        # 3. Content similarity
        # ------------------------------------------------------

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

    # ----------------------------------------------------------
    # Select article to keep
    # ----------------------------------------------------------

    @staticmethod
    def choose_best_article(
        article_a: dict,
        article_b: dict,
    ) -> dict:
        """
        Choose the better article when two articles are duplicates.

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

        if score_a > score_b:
            return article_a

        if score_b > score_a:
            return article_b

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

    # ----------------------------------------------------------
    # Deduplicate a list of articles
    # ----------------------------------------------------------

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

        for article in articles:

            duplicate = self.find_duplicate(
                article,
                unique_articles,
            )

            if duplicate is None:

                unique_articles.append(
                    article
                )

                continue

            matched_article = duplicate[
                "matched_article"
            ]

            best_article = self.choose_best_article(
                article,
                matched_article,
            )

            duplicate_records.append(
                {
                    "duplicate_article": article,
                    "matched_article": matched_article,
                    "reason": duplicate["reason"],
                    "similarity": duplicate[
                        "similarity"
                    ],
                }
            )

            # Replace existing article if
            # the new article is better.
            if best_article is article:

                index = unique_articles.index(
                    matched_article
                )

                unique_articles[index] = article

        return (
            unique_articles,
            duplicate_records,
        )