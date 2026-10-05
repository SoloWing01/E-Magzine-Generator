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
        Get only articles that passed the previous
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
        Build a focused retrieval/generation query.

        Keep this query close to the actual article title.
        This reduces the chance of Mistral drifting into
        unrelated information.
        """

        title = (article.title or "").strip()
        category = (article.category or "").strip()

        if category:
            return (
                f"Write a factual magazine article about "
                f"the following Northeast India news story. "
                f"Focus specifically on the reported facts "
                f"from the retrieved source.\n\n"
                f"Category: {category}\n"
                f"Article title: {title}"
            )

        return (
            "Write a factual magazine article about the "
            "following Northeast India news story. "
            "Use only the retrieved source material.\n\n"
            f"Article title: {title}"
        )

    # =========================================================
    # RETRY QUERY
    # =========================================================

    @staticmethod
    def _build_retry_query(article: Article, attempt: int) -> str:
        """
        A more restrictive query used when the first generation
        fails.

        The important part is telling the model to stay tightly
        focused on the selected article and avoid repeated
        citation markers.
        """

        title = (article.title or "").strip()
        category = (article.category or "").strip()

        return (
            "Write ONE grounded magazine article using ONLY "
            "the retrieved evidence for this specific article.\n\n"
            f"Article title: {title}\n"
            f"Category: {category}\n\n"
            "STRICT REQUIREMENTS:\n"
            "1. Use only facts explicitly supported by the "
            "retrieved source.\n"
            "2. Do not add outside knowledge.\n"
            "3. Do not invent facts, numbers, dates, quotes "
            "or explanations.\n"
            "4. Write approximately 4 to 6 paragraphs.\n"
            "5. Put exactly ONE [Source 1] citation at the "
            "end of each factual paragraph.\n"
            "6. Do not repeat [Source 1] continuously.\n"
            "7. Do not output a bibliography.\n"
            "8. Return only valid JSON.\n"
            "9. The JSON must contain exactly these fields:\n"
            "   headline, article, source_ids\n"
            "10. source_ids must be [1] when Source 1 is used."
        )

    # =========================================================
    # RESULT SERIALIZATION
    # =========================================================

    @staticmethod
    def _serialize_date(value):
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        return str(value)

    # =========================================================
    # RETRIEVED ARTICLE METADATA
    # =========================================================

    @staticmethod
    def _serialize_retrieved_articles(
        retrieved_articles,
    ) -> list[dict[str, Any]]:
        """
        Convert RAG ArticleResult objects into JSON-safe
        dictionaries.
        """

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
        """
        Keep grounding information in the editorial JSON.

        This is useful later for QA and magazine generation.
        """

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
    # SUCCESS RESULT
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
    # FAILURE RESULT
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
        # Initial generation
        # -----------------------------------------------------

        generator = RAGGenerator(
            top_k=3,
            min_similarity=0.20,
            grounding_threshold=0.45,
            max_generation_attempts=2,
        )

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

            # -------------------------------------------------
            # Retry only when another attempt remains
            # -------------------------------------------------

            if attempt < self.max_article_retries:

                print(
                    "Retrying with a stricter "
                    "article-specific prompt..."
                )

        # -----------------------------------------------------
        # All retries failed
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