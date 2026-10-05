from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from app.images.search import ImageSearch
from app.images.downloader import ImageDownloader
from app.images.deduplicator import ImageDeduplicator
from app.images.relevance import ImageRelevance


@dataclass
class ImagePipelineResult:
    article_id: int

    search_query: str

    candidates_found: int

    candidates_after_filter: int

    images_downloaded: int

    unique_images: int

    relevant_images: int

    selected_image: str | None

    selected_score: float | None

    selected_rank: int | None

    downloaded_images: list[dict[str, Any]]

    relevance_results: list[dict[str, Any]]

    success: bool

    error: str | None = None


class ImagePipeline:
    """
    Complete article-image processing pipeline.

    Flow:

        Article
            ↓
        Article-aware Image Search
            ↓
        Source Quality Filtering
            ↓
        Image Download
            ↓
        Deduplication
            ↓
        CLIP Relevance
            ↓
        Best Image Selection
    """

    # ================================================================
    # SOURCE QUALITY
    # ================================================================

    HIGH_QUALITY_DOMAINS = {
        # Government
        "pib.gov.in",
        "mod.gov.in",
        "assam.gov.in",
        "mizoram.gov.in",
        "manipur.gov.in",
        "nagaland.gov.in",
        "meghalaya.gov.in",
        "tripura.gov.in",
        "arunachalpradesh.gov.in",
        "sikkim.gov.in",

        # Established news
        "assamtribune.com",
        "thehindu.com",
        "indianexpress.com",
        "hindustantimes.com",
        "telegraphindia.com",
        "timesofindia.indiatimes.com",
        "ndtv.com",
        "indiatoday.in",
        "deccanherald.com",
        "theprint.in",
    }

    MEDIUM_QUALITY_DOMAINS = {
        "news18.com",
        "eastmojo.com",
        "northeasttoday.in",
        "nenow.in",
        "sentinelassam.com",
        "pratidintime.com",
        "assamlive.com",
        "guwahatiplus.com",
    }

    LOW_QUALITY_PATTERNS = {
        "tour",
        "tourism",
        "travel",
        "map",
        "maps",
        "blogspot",
        "wordpress",
        "pinterest",
        "stock",
        "wallpaper",
        "clipart",
    }

    # ================================================================
    # INITIALIZATION
    # ================================================================

    def __init__(
        self,
        searcher: ImageSearch | None = None,
        downloader: ImageDownloader | None = None,
        deduplicator: ImageDeduplicator | None = None,
        relevance: ImageRelevance | None = None,
        max_search_results: int = 10,
        max_downloads: int = 5,
        relevance_threshold: float = 0.20,
    ):

        self.searcher = (
            searcher
            if searcher is not None
            else ImageSearch()
        )

        self.downloader = (
            downloader
            if downloader is not None
            else ImageDownloader()
        )

        self.deduplicator = (
            deduplicator
            if deduplicator is not None
            else ImageDeduplicator()
        )

        self.relevance = (
            relevance
            if relevance is not None
            else ImageRelevance(
                threshold=relevance_threshold
            )
        )

        self.max_search_results = (
            max_search_results
        )

        self.max_downloads = (
            max_downloads
        )

        self.relevance_threshold = (
            relevance_threshold
        )

    # ================================================================
    # SOURCE QUALITY
    # ================================================================

    def source_quality_score(
        self,
        source_domain: str,
    ) -> float:

        domain = (
            source_domain
            or ""
        ).lower().strip()

        domain = domain.removeprefix(
            "www."
        )

        if not domain:
            return 0.30

        if domain in self.HIGH_QUALITY_DOMAINS:
            return 1.00

        if domain in self.MEDIUM_QUALITY_DOMAINS:
            return 0.75

        for pattern in self.LOW_QUALITY_PATTERNS:

            if pattern in domain:
                return 0.10

        # Unknown sources are allowed as fallback.
        return 0.50

    def filter_search_results(
        self,
        results,
    ):

        filtered = []

        print(
            "\nSOURCE QUALITY FILTER"
        )

        print(
            "-" * 70
        )

        for result in results:

            domain = (
                result.source_domain
                or ""
            ).lower()

            quality = (
                self.source_quality_score(
                    domain
                )
            )

            if quality <= 0.10:

                print(
                    f"REJECTED : "
                    f"{domain or 'unknown'}"
                )

                print(
                    "Reason   : "
                    "low-quality source"
                )

                continue

            print(
                f"ACCEPTED : "
                f"{domain or 'unknown'} "
                f"(quality={quality:.2f})"
            )

            filtered.append(
                result
            )

        return filtered

    # ================================================================
    # PROCESS ONE ARTICLE
    # ================================================================

    def process_article(
        self,
        article: dict,
    ) -> ImagePipelineResult:

        article_id = article.get(
            "id"
        )

        if article_id is None:
            raise ValueError(
                "Article must contain an 'id'."
            )

        title = article.get(
            "title",
            "",
        )

        print("\n")
        print("=" * 70)
        print("IMAGE PIPELINE")
        print("=" * 70)

        print(
            f"Article ID : {article_id}"
        )

        print(
            f"Title      : {title}"
        )

        try:

            # ========================================================
            # STEP 1 — SEARCH
            # ========================================================

            print(
                "\n[1/5] "
                "ARTICLE-AWARE IMAGE SEARCH"
            )

            search_results = (
                self.searcher.search_for_article(
                    article=article,
                    max_results=(
                        self.max_search_results
                    ),
                )
            )

            candidates_found = len(
                search_results
            )

            print(
                f"\nCandidates found: "
                f"{candidates_found}"
            )

            if not search_results:

                return self._failure_result(
                    article_id=article_id,
                    query=title,
                    error=(
                        "No image search "
                        "results were found."
                    ),
                )

            # ========================================================
            # QUERY METADATA
            # ========================================================

            queries = (
                self.searcher.build_queries(
                    title=title,
                    content=article.get(
                        "content",
                        "",
                    ),
                    category=article.get(
                        "category"
                    ),
                    source=article.get(
                        "source"
                    ),
                )
            )

            search_query = (
                queries[0]
                if queries
                else title
            )

            # ========================================================
            # STEP 2 — SOURCE FILTER
            # ========================================================

            print(
                "\n[2/5] "
                "SOURCE QUALITY FILTER"
            )

            filtered_results = (
                self.filter_search_results(
                    search_results
                )
            )

            candidates_after_filter = len(
                filtered_results
            )

            print(
                f"\nCandidates after filtering: "
                f"{candidates_after_filter}"
            )

            if not filtered_results:

                return self._failure_result(
                    article_id=article_id,
                    query=search_query,
                    candidates_found=(
                        candidates_found
                    ),
                    error=(
                        "All image candidates "
                        "were rejected by "
                        "source quality filtering."
                    ),
                )

            # ========================================================
            # STEP 3 — DOWNLOAD
            # ========================================================

            print(
                "\n[3/5] IMAGE DOWNLOAD"
            )

            downloaded = (
                self.downloader.download_for_article(
                    article=article,
                    results=filtered_results,
                    max_images=self.max_downloads,
                )
            )

            images_downloaded = len(
                downloaded
            )

            print(
                f"\nImages downloaded: "
                f"{images_downloaded}"
            )

            if not downloaded:

                return self._failure_result(
                    article_id=article_id,
                    query=search_query,
                    candidates_found=(
                        candidates_found
                    ),
                    candidates_after_filter=(
                        candidates_after_filter
                    ),
                    error=(
                        "No valid images "
                        "could be downloaded."
                    ),
                )

            # ========================================================
            # STEP 4 — DEDUPLICATION
            # ========================================================

            print(
                "\n[4/5] IMAGE DEDUPLICATION"
            )

            image_paths = [
                Path(image.file_path)
                for image in downloaded
            ]

            article_deduplicator = (
                ImageDeduplicator()
            )

            unique_paths = (
                article_deduplicator.deduplicate(
                    image_paths
                )
            )

            unique_images = len(
                unique_paths
            )

            print(
                f"Unique images: "
                f"{unique_images}"
            )

            if not unique_paths:

                return self._failure_result(
                    article_id=article_id,
                    query=search_query,
                    candidates_found=(
                        candidates_found
                    ),
                    candidates_after_filter=(
                        candidates_after_filter
                    ),
                    images_downloaded=(
                        images_downloaded
                    ),
                    error=(
                        "No unique images "
                        "remain after "
                        "deduplication."
                    ),
                )

            # ========================================================
            # STEP 5 — CLIP RELEVANCE
            # ========================================================

            print(
                "\n[5/5] IMAGE RELEVANCE"
            )

            relevance_results = (
                self.relevance.score_article_images(
                    article=article,
                    image_paths=unique_paths,
                )
            )

            relevant_results = [
                result
                for result in relevance_results
                if (
                    result.score
                    >= self.relevance_threshold
                )
            ]

            relevant_images = len(
                relevant_results
            )

            # ========================================================
            # PRINT RANKING
            # ========================================================

            print("\n")
            print("=" * 70)
            print("IMAGE RANKING")
            print("=" * 70)

            for result in relevance_results:

                print(
                    f"\nRank       : "
                    f"{result.rank}"
                )

                print(
                    f"Image      : "
                    f"{Path(result.image_path).name}"
                )

                print(
                    f"CLIP score : "
                    f"{result.score:.4f}"
                )

                print(
                    f"Relevant   : "
                    f"{result.score >= self.relevance_threshold}"
                )

            # ========================================================
            # BEST IMAGE
            # ========================================================

            best_image = (
                self.relevance.get_best_image(
                    relevance_results
                )
            )

            if best_image is None:

                print(
                    "\nNo image passed "
                    "the relevance threshold."
                )

                return ImagePipelineResult(
                    article_id=article_id,
                    search_query=search_query,
                    candidates_found=(
                        candidates_found
                    ),
                    candidates_after_filter=(
                        candidates_after_filter
                    ),
                    images_downloaded=(
                        images_downloaded
                    ),
                    unique_images=(
                        unique_images
                    ),
                    relevant_images=(
                        relevant_images
                    ),
                    selected_image=None,
                    selected_score=None,
                    selected_rank=None,
                    downloaded_images=[
                        asdict(image)
                        for image in downloaded
                    ],
                    relevance_results=[
                        asdict(result)
                        for result in relevance_results
                    ],
                    success=False,
                    error=(
                        "No image passed "
                        "the relevance threshold."
                    ),
                )

            # ========================================================
            # FINAL OUTPUT
            # ========================================================

            print("\n")
            print("=" * 70)
            print("SELECTED IMAGE")
            print("=" * 70)

            print(
                f"Image : "
                f"{best_image.image_path}"
            )

            print(
                f"Score : "
                f"{best_image.score:.4f}"
            )

            print(
                f"Rank  : "
                f"{best_image.rank}"
            )

            print(
                "=" * 70
            )

            return ImagePipelineResult(
                article_id=article_id,
                search_query=search_query,
                candidates_found=(
                    candidates_found
                ),
                candidates_after_filter=(
                    candidates_after_filter
                ),
                images_downloaded=(
                    images_downloaded
                ),
                unique_images=(
                    unique_images
                ),
                relevant_images=(
                    relevant_images
                ),
                selected_image=(
                    best_image.image_path
                ),
                selected_score=(
                    best_image.score
                ),
                selected_rank=(
                    best_image.rank
                ),
                downloaded_images=[
                    asdict(image)
                    for image in downloaded
                ],
                relevance_results=[
                    asdict(result)
                    for result in relevance_results
                ],
                success=True,
                error=None,
            )

        except Exception as e:

            print(
                "\nIMAGE PIPELINE FAILED"
            )

            print(
                f"Error: {e}"
            )

            return self._failure_result(
                article_id=article_id,
                query=title,
                error=str(e),
            )

    # ================================================================
    # PROCESS MULTIPLE ARTICLES
    # ================================================================

    def process_articles(
        self,
        articles: list[dict],
    ) -> list[ImagePipelineResult]:

        results = []

        total = len(
            articles
        )

        print("\n")
        print("=" * 70)
        print("BATCH IMAGE PIPELINE")
        print("=" * 70)

        print(
            f"Articles to process: "
            f"{total}"
        )

        for index, article in enumerate(
            articles,
            start=1,
        ):

            print("\n")

            print(
                f"ARTICLE "
                f"{index}/{total}"
            )

            result = (
                self.process_article(
                    article
                )
            )

            results.append(
                result
            )

        self._print_batch_summary(
            results
        )

        return results

    # ================================================================
    # FAILURE RESULT
    # ================================================================

    @staticmethod
    def _failure_result(
        article_id: int,
        query: str,
        candidates_found: int = 0,
        candidates_after_filter: int = 0,
        images_downloaded: int = 0,
        unique_images: int = 0,
        error: str = "",
    ) -> ImagePipelineResult:

        return ImagePipelineResult(
            article_id=article_id,
            search_query=query,
            candidates_found=(
                candidates_found
            ),
            candidates_after_filter=(
                candidates_after_filter
            ),
            images_downloaded=(
                images_downloaded
            ),
            unique_images=(
                unique_images
            ),
            relevant_images=0,
            selected_image=None,
            selected_score=None,
            selected_rank=None,
            downloaded_images=[],
            relevance_results=[],
            success=False,
            error=error,
        )

    # ================================================================
    # BATCH SUMMARY
    # ================================================================

    @staticmethod
    def _print_batch_summary(
        results: list[ImagePipelineResult],
    ):

        print("\n")
        print("=" * 70)
        print("IMAGE PIPELINE SUMMARY")
        print("=" * 70)

        total = len(
            results
        )

        successful = sum(
            result.success
            for result in results
        )

        failed = (
            total - successful
        )

        total_candidates = sum(
            result.candidates_found
            for result in results
        )

        total_filtered = sum(
            result.candidates_after_filter
            for result in results
        )

        total_downloaded = sum(
            result.images_downloaded
            for result in results
        )

        total_unique = sum(
            result.unique_images
            for result in results
        )

        total_relevant = sum(
            result.relevant_images
            for result in results
        )

        print(
            f"Articles processed : "
            f"{total}"
        )

        print(
            f"Successful         : "
            f"{successful}"
        )

        print(
            f"Failed             : "
            f"{failed}"
        )

        print(
            f"Candidates found   : "
            f"{total_candidates}"
        )

        print(
            f"After filtering    : "
            f"{total_filtered}"
        )

        print(
            f"Images downloaded  : "
            f"{total_downloaded}"
        )

        print(
            f"Unique images      : "
            f"{total_unique}"
        )

        print(
            f"Relevant images    : "
            f"{total_relevant}"
        )

        print(
            "=" * 70
        )

    # ================================================================
    # RESULT → DICTIONARY
    # ================================================================

    @staticmethod
    def result_to_dict(
        result: ImagePipelineResult,
    ) -> dict:

        return asdict(
            result
        )


# =============================================================
# DATABASE BATCH RUNNER
# =============================================================

def load_relevant_articles_from_database() -> list[dict]:
    """
    Load all articles that have been classified as relevant
    for the Northeast Sentinel magazine.

    Articles are selected by having a non-null category belonging
    to one of the magazine's five editorial categories.
    """

    from app.database.database import SessionLocal
    from app.database.models import Article

    categories = [
        "Sports & Achievements",
        "Regional News",
        "Development",
        "Security & Strategic Affairs",
        "Society & Youth",
    ]

    session = SessionLocal()

    try:
        records = (
            session.query(Article)
            .filter(
                Article.category.in_(categories)
            )
            .order_by(
                Article.article_score.desc(),
                Article.id.asc(),
            )
            .all()
        )

        articles = []

        for record in records:
            articles.append(
                {
                    "id": record.id,
                    "title": record.title,
                    "url": record.url,
                    "source": record.source,
                    "category": record.category,
                    "content": record.content,
                }
            )

        return articles

    finally:
        session.close()


def print_article_list(
    articles: list[dict],
) -> None:
    """
    Print the articles that will be processed.
    """

    print()
    print("=" * 70)
    print("ARTICLES LOADED FROM DATABASE")
    print("=" * 70)

    print(
        f"Total relevant articles: "
        f"{len(articles)}"
    )

    for index, article in enumerate(
        articles,
        start=1,
    ):
        print()
        print(
            f"{index}. "
            f"Article ID : {article['id']}"
        )

        print(
            f"   Category  : "
            f"{article.get('category')}"
        )

        print(
            f"   Title     : "
            f"{article.get('title')}"
        )

        print(
            f"   Source    : "
            f"{article.get('source')}"
        )

        print(
            f"   URL       : "
            f"{article.get('url')}"
        )


def print_detailed_batch_results(
    results: list[ImagePipelineResult],
) -> None:
    """
    Print one compact result row for every article.
    """

    print()
    print("=" * 70)
    print("ARTICLE IMAGE RESULTS")
    print("=" * 70)

    for result in results:
        print()
        print(
            f"Article ID : "
            f"{result.article_id}"
        )

        print(
            f"Success    : "
            f"{result.success}"
        )

        print(
            f"Candidates : "
            f"{result.candidates_found}"
        )

        print(
            f"Filtered   : "
            f"{result.candidates_after_filter}"
        )

        print(
            f"Downloaded : "
            f"{result.images_downloaded}"
        )

        print(
            f"Unique     : "
            f"{result.unique_images}"
        )

        print(
            f"Relevant   : "
            f"{result.relevant_images}"
        )

        print(
            f"Image      : "
            f"{result.selected_image}"
        )

        print(
            f"CLIP score : "
            f"{result.selected_score}"
        )

        if result.error:
            print(
                f"Error      : "
                f"{result.error}"
            )


if __name__ == "__main__":

    print()
    print("=" * 70)
    print("NORTHEAST SENTINEL")
    print("AUTOMATED IMAGE PIPELINE")
    print("=" * 70)

    # ---------------------------------------------------------
    # LOAD ARTICLES FROM SQLITE
    # ---------------------------------------------------------

    articles = load_relevant_articles_from_database()

    if not articles:
        raise RuntimeError(
            "No relevant articles were found in the database."
        )

    print_article_list(articles)

    # ---------------------------------------------------------
    # CREATE ONE PIPELINE INSTANCE
    # ---------------------------------------------------------
    #
    # Important:
    # ImageRelevance loads CLIP onto the GPU.
    # We therefore create ONE pipeline and reuse it
    # for all articles.

    pipeline = ImagePipeline(
        max_search_results=10,
        max_downloads=5,
        relevance_threshold=0.20,
    )

    # ---------------------------------------------------------
    # PROCESS ALL ARTICLES
    # ---------------------------------------------------------

    results = pipeline.process_articles(
        articles
    )

    # ---------------------------------------------------------
    # DETAILED RESULTS
    # ---------------------------------------------------------

    print_detailed_batch_results(
        results
    )

    # ---------------------------------------------------------
    # FINAL SUMMARY
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL IMAGE PIPELINE RESULT")
    print("=" * 70)

    total = len(results)

    successful = sum(
        1
        for result in results
        if result.success
    )

    failed = total - successful

    selected_images = sum(
        1
        for result in results
        if result.selected_image
    )

    print(
        f"Articles processed : {total}"
    )

    print(
        f"Successful         : {successful}"
    )

    print(
        f"Failed             : {failed}"
    )

    print(
        f"Images selected    : {selected_images}"
    )

    print("=" * 70)