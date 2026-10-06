import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.database.database import SessionLocal
from app.database.models import Article
from app.rag.generator import RAGGenerator


class EditorialContentGenerator:
    """
    Phase 14
    ---------------------------------------------------------
    Generates grounded editorial content for all relevant
    articles selected from SQLite.

    Flow:

        SQLite
          ↓
        Relevant articles
          ↓
        Article-specific retrieval query
          ↓
        RAGGenerator
          ↓
        Grounded article
          ↓
        Retry failed generation
          ↓
        Editorial JSON
    """

    def __init__(
        self,
        output_path: str | None = None,
        max_article_retries: int = 2,
    ):

        self.output_path = Path(
            output_path
            or (
                Path(settings.OUTPUT_DIR)
                / "editorial_content.json"
            )
        )

        self.max_article_retries = max_article_retries

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        print("=" * 70)
        print("NORTHEAST SENTINEL AI - EDITORIAL GENERATION")
        print("=" * 70)

    # =========================================================
    # ARTICLE SELECTION
    # =========================================================

    def _get_articles(self, db):
        """
        Select only articles that passed the previous
        relevance/classification pipeline.
        """

        return (
            db.query(Article)
            .filter(
                Article.category.isnot(None),
                Article.category != "Not Relevant",
            )
            .order_by(
                Article.article_score.desc(),
                Article.published_date.desc(),
            )
            .all()
        )

    # =========================================================
    # QUERY BUILDING
    # =========================================================

    @staticmethod
    def _build_query(article: Article) -> str:
        """
        Build an article-specific retrieval query.

        Important:
        Keep the query focused on the actual news article
        rather than asking a generic magazine-writing question.
        """

        title = (article.title or "").strip()
        category = (article.category or "").strip()
        source = (article.source or "").strip()

        parts = [
            "Retrieve the exact source article for the following "
            "Northeast India news story.",
            "",
            "Use the article title, category, and source as the "
            "primary retrieval anchors.",
            "",
            f"Article title: {title}",
        ]

        if category:
            parts.append(
                f"Category: {category}"
            )

        if source:
            parts.append(
                f"Source: {source}"
            )

        parts.extend(
            [
                "",
                "After retrieving the source, generate a factual "
                "magazine article using ONLY the retrieved evidence.",
                "Do not use outside knowledge.",
            ]
        )

        return "\n".join(parts)

    # =========================================================
    # RETRY QUERY
    # =========================================================

    @staticmethod
    def _build_retry_query(
        article: Article,
        attempt: int,
    ) -> str:
        """
        Strict retry query.

        IMPORTANT:
        Do not hardcode Source 1.

        The RAG system uses the actual retrieved source/article
        IDs. The model must cite the actual source ID returned
        in the evidence context.
        """

        title = (article.title or "").strip()
        category = (article.category or "").strip()
        source = (article.source or "").strip()

        return f"""
Retrieve the exact source article for this specific news story
and write one grounded magazine article using ONLY that source.

Article title:
{title}

Category:
{category}

Source:
{source}

STRICT REQUIREMENTS:

1. Use ONLY information explicitly supported by the retrieved
   source material.

2. Do NOT use outside knowledge.

3. Do NOT invent facts, numbers, dates, locations, organizations,
   quotes, explanations, or conclusions.

4. Stay focused on this exact article.

5. Write approximately 4 to 6 paragraphs.

6. Every factual paragraph MUST contain a citation.

7. Citation format MUST use the ACTUAL source ID supplied in
   the retrieved evidence.

8. Do NOT assume the source ID is 1.

9. The declared source_ids array MUST contain the SAME actual
   source IDs that appear in the article citations.

10. Do NOT create or invent source IDs.

11. Do NOT output a bibliography.

12. Return valid JSON only.

13. JSON must contain exactly these fields:

    headline
    article
    source_ids

14. The article should be written in a neutral,
    factual magazine-news style.

15. Do not add information merely because it is generally known.

Attempt:
{attempt}
""".strip()

    # =========================================================
    # DATE SERIALIZATION
    # =========================================================

    @staticmethod
    def _serialize_date(value):

        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        return str(value)

    # =========================================================
    # RETRIEVED ARTICLE SERIALIZATION
    # =========================================================

    @staticmethod
    def _serialize_retrieved_articles(
        retrieved_articles,
    ) -> list[dict[str, Any]]:

        serialized = []

        for item in retrieved_articles or []:

            serialized.append(
                {
                    "source_id": getattr(
                        item,
                        "source_id",
                        None,
                    ),

                    "article_id": getattr(
                        item,
                        "article_id",
                        None,
                    ),

                    "title": getattr(
                        item,
                        "title",
                        "",
                    ),

                    "source": getattr(
                        item,
                        "source",
                        "",
                    ),

                    "url": getattr(
                        item,
                        "url",
                        "",
                    ),

                    "published_date": (
                        getattr(
                            item,
                            "published_date",
                            None,
                        )
                    ),

                    "category": getattr(
                        item,
                        "category",
                        None,
                    ),

                    "similarity": round(
                        float(
                            getattr(
                                item,
                                "similarity",
                                0.0,
                            )
                        ),
                        4,
                    ),

                    "article_score": getattr(
                        item,
                        "article_score",
                        None,
                    ),
                }
            )

        return serialized

    # =========================================================
    # GROUNDING SERIALIZATION
    # =========================================================

    @staticmethod
    def _serialize_grounding(
        grounding: dict[str, Any] | None,
    ) -> dict[str, Any]:

        if not grounding:
            return {}

        return {
            "valid": grounding.get(
                "valid",
                False,
            ),

            "cited_source_ids": grounding.get(
                "cited_source_ids",
                [],
            ),

            "missing_source_ids": grounding.get(
                "missing_source_ids",
                [],
            ),

            "invalid_source_ids": grounding.get(
                "invalid_source_ids",
                [],
            ),

            "unsupported_claims": grounding.get(
                "unsupported_claims",
                [],
            ),

            "errors": grounding.get(
                "errors",
                [],
            ),

            "claim_results": grounding.get(
                "claim_results",
                [],
            ),
        }

    # =========================================================
    # SUCCESS RECORD
    # =========================================================

    def _build_success_record(
        self,
        article: Article,
        result: dict[str, Any],
        query: str,
    ) -> dict[str, Any]:

        retrieved_articles = result.get(
            "retrieved_articles",
            [],
        )

        grounding = result.get(
            "grounding",
            {},
        )

        return {
            "article_id": article.id,

            "status": "approved",

            "category": article.category,

            "original_title": article.title,

            "headline": result.get(
                "headline",
                article.title,
            ),

            "article": result.get(
                "article",
                "",
            ),

            "published_date": self._serialize_date(
                article.published_date
            ),

            "source": article.source,

            "source_url": article.url,

            "article_score": article.article_score,

            "northeast_score": article.northeast_score,

            "security_score": article.security_score,

            "development_score": article.development_score,

            "society_score": article.society_score,

            "sports_score": article.sports_score,

            "source_ids": result.get(
                "source_ids",
                [],
            ),

            "sources": result.get(
                "sources",
                [],
            ),

            "retrieved_article_ids": [
                item.article_id
                for item in retrieved_articles
                if getattr(
                    item,
                    "article_id",
                    None,
                ) is not None
            ],

            "retrieved_articles": (
                self._serialize_retrieved_articles(
                    retrieved_articles
                )
            ),

            "grounding": self._serialize_grounding(
                grounding
            ),

            "query": query,

            "generation_attempt": result.get(
                "attempt",
                1,
            ),

            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    # =========================================================
    # FAILURE RECORD
    # =========================================================

    def _build_failure_record(
        self,
        article: Article,
        result: dict[str, Any],
        query: str,
        attempts: int,
    ) -> dict[str, Any]:

        retrieved_articles = result.get(
            "retrieved_articles",
            [],
        )

        return {
            "article_id": article.id,

            "status": "failed",

            "category": article.category,

            "original_title": article.title,

            "headline": "",

            "article": "",

            "published_date": self._serialize_date(
                article.published_date
            ),

            "source": article.source,

            "source_url": article.url,

            "article_score": article.article_score,

            "northeast_score": article.northeast_score,

            "security_score": article.security_score,

            "development_score": article.development_score,

            "society_score": article.society_score,

            "sports_score": article.sports_score,

            "source_ids": result.get(
                "source_ids",
                [],
            ),

            "sources": result.get(
                "sources",
                [],
            ),

            "retrieved_article_ids": [
                item.article_id
                for item in retrieved_articles
                if getattr(
                    item,
                    "article_id",
                    None,
                ) is not None
            ],

            "retrieved_articles": (
                self._serialize_retrieved_articles(
                    retrieved_articles
                )
            ),

            "grounding": self._serialize_grounding(
                result.get(
                    "grounding",
                    {},
                )
            ),

            "query": query,

            "generation_attempts": attempts,

            "error_status": result.get(
                "status",
                "unknown",
            ),

            "error_message": result.get(
                "message",
                "Editorial generation failed.",
            ),

            "errors": result.get(
                "errors",
                [],
            ),

            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    # =========================================================
    # GENERATE ONE ARTICLE
    # =========================================================

    def _generate_article(
        self,
        article: Article,
    ) -> dict[str, Any]:

        print()
        print("-" * 70)
        print(
            f"ARTICLE ID: {article.id}"
        )
        print(
            f"Title: {article.title}"
        )
        print(
            f"Category: {article.category}"
        )

        query = self._build_query(article)

        last_result: dict[str, Any] = {
            "success": False,
            "status": "not_started",
            "message": "Generation was not attempted.",
            "errors": [],
        }

        # -----------------------------------------------------
        # Create ONE RAG generator for this article
        # -----------------------------------------------------

        generator = RAGGenerator(
            top_k=3,
            min_similarity=0.20,
            grounding_threshold=0.45,
            max_generation_attempts=2,
        )

        # -----------------------------------------------------
        # Article-level retries
        # -----------------------------------------------------

        for attempt in range(
            1,
            self.max_article_retries + 1,
        ):

            if attempt == 1:
                current_query = query
            else:
                current_query = self._build_retry_query(
                    article,
                    attempt,
                )

            print()
            print(
                f"Editorial generation attempt "
                f"{attempt}/{self.max_article_retries}"
            )

            try:

                result = generator.generate(
                    query=current_query
                )

            except Exception as exc:

                result = {
                    "success": False,
                    "status": "exception",
                    "message": str(exc),
                    "errors": [str(exc)],
                }

            last_result = result

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            if result.get("success") is True:

                print(
                    "Status: APPROVED"
                )

                print(
                    "Headline: "
                    f"{result.get('headline', article.title)}"
                )

                return self._build_success_record(
                    article=article,
                    result=result,
                    query=current_query,
                )

            # -------------------------------------------------
            # FAILED ATTEMPT
            # -------------------------------------------------

            print(
                "Status: FAILED"
            )

            print(
                "Reason: "
                f"{result.get('status', 'unknown')}"
            )

            print(
                "Message: "
                f"{result.get('message', 'Unknown error')}"
            )

            if attempt < self.max_article_retries:

                print(
                    "Retrying with a stricter "
                    "article-specific prompt..."
                )

        # -----------------------------------------------------
        # ALL RETRIES FAILED
        # -----------------------------------------------------

        print()
        print(
            "All editorial generation attempts failed."
        )

        return self._build_failure_record(
            article=article,
            result=last_result,
            query=query,
            attempts=self.max_article_retries,
        )

    # =========================================================
    # SAVE OUTPUT
    # =========================================================

    def _save_output(
        self,
        records: list[dict[str, Any]],
    ):

        payload = {
            "project": settings.PROJECT_NAME,

            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "date_range": {
                "start": settings.START_DATE,
                "end": settings.END_DATE,
            },

            "total_articles": len(records),

            "approved_articles": sum(
                1
                for item in records
                if item.get("status") == "approved"
            ),

            "failed_articles": sum(
                1
                for item in records
                if item.get("status") == "failed"
            ),

            "articles": records,
        }

        with open(
            self.output_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                payload,
                file,
                indent=2,
                ensure_ascii=False,
            )

    # =========================================================
    # RUN
    # =========================================================

    def run(self):

        db = SessionLocal()

        records: list[dict[str, Any]] = []

        approved = 0
        failed = 0

        try:

            articles = self._get_articles(db)

            print()
            print(
                "Articles selected for "
                "editorial generation: "
                f"{len(articles)}"
            )

            # -------------------------------------------------
            # Generate each article independently
            # -------------------------------------------------

            for index, article in enumerate(
                articles,
                start=1,
            ):

                print()
                print(
                    f"[{index}/{len(articles)}]"
                )

                try:

                    record = self._generate_article(
                        article
                    )

                    records.append(record)

                    if (
                        record.get("status")
                        == "approved"
                    ):
                        approved += 1
                    else:
                        failed += 1

                except Exception as exc:

                    print()
                    print(
                        "Unexpected article-level "
                        f"failure: {exc}"
                    )

                    failure_record = (
                        self._build_failure_record(
                            article=article,
                            result={
                                "status": "exception",
                                "message": str(exc),
                                "errors": [str(exc)],
                            },
                            query=self._build_query(
                                article
                            ),
                            attempts=(
                                self.max_article_retries
                            ),
                        )
                    )

                    records.append(
                        failure_record
                    )

                    failed += 1

            # -------------------------------------------------
            # Save
            # -------------------------------------------------

            self._save_output(records)

            print()
            print("=" * 70)
            print(
                "EDITORIAL GENERATION COMPLETE"
            )
            print("=" * 70)

            print(
                f"Generated: {approved}"
            )

            print(
                f"Failed: {failed}"
            )

            print(
                f"Total: {len(records)}"
            )

            print(
                f"Output: {self.output_path}"
            )

            print("=" * 70)

            return records

        finally:

            db.close()


# ======================================================================
# MAIN
# ======================================================================

if __name__ == "__main__":

    generator = EditorialContentGenerator(
        max_article_retries=2,
    )

    generator.run()