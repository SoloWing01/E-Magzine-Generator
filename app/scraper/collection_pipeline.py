from app.database.article_repository import save_article
from app.preprocessing.date_filter import is_valid_date
from app.preprocessing.validator import ArticleValidator
from app.scraper.article_discovery import ArticleDiscovery
from app.scraper.news_scraper import NewsScraper


class CollectionPipeline:
    """
    Complete news collection pipeline.

    Discovery
        ↓
    Scraping
        ↓
    Validation
        ↓
    Date filtering
        ↓
    Duplicate checking
        ↓
    SQLite
    """

    def __init__(self):

        self.discovery = ArticleDiscovery()
        self.scraper = NewsScraper()

        self.stats = {
            "discovered": 0,
            "scraped": 0,
            "invalid": 0,
            "outside_date_range": 0,
            "duplicates": 0,
            "saved": 0,
            "failed": 0,
        }

    def collect(self, listing_url: str):

        print("=" * 70)
        print("NORTHEAST SENTINEL - COLLECTION PIPELINE")
        print("=" * 70)

        # --------------------------------------------------
        # 1. DISCOVER ARTICLE URLS
        # --------------------------------------------------

        print("\n[1] Discovering article URLs...")

        urls = self.discovery.discover_articles(
            listing_url
        )

        self.stats["discovered"] = len(urls)

        print(
            f"Discovered {len(urls)} candidate URLs."
        )

        # --------------------------------------------------
        # 2. PROCESS EACH ARTICLE
        # --------------------------------------------------

        for index, url in enumerate(urls, start=1):

            print("\n" + "-" * 70)
            print(
                f"[{index}/{len(urls)}] Processing:"
            )
            print(url)

            # ----------------------------------------------
            # SCRAPE
            # ----------------------------------------------

            try:

                article = self.scraper.scrape_article(
                    url
                )

            except Exception as e:

                print(f"Scraping error: {e}")

                self.stats["failed"] += 1
                continue

            if article is None:

                print("Could not scrape article.")

                self.stats["failed"] += 1
                continue

            self.stats["scraped"] += 1

            # ----------------------------------------------
            # VALIDATE ARTICLE STRUCTURE
            # ----------------------------------------------

            is_valid, errors = ArticleValidator.validate(
                article
            )

            if not is_valid:

                print("Article validation failed:")

                for error in errors:
                    print(f"  - {error}")

                self.stats["invalid"] += 1
                continue

            # ----------------------------------------------
            # DATE VALIDATION
            # ----------------------------------------------

            published_date = article[
                "published_date"
            ]

            print(
                f"Published: {published_date}"
            )

            if not is_valid_date(
                published_date
            ):

                print(
                    "Outside required date range."
                )

                self.stats[
                    "outside_date_range"
                ] += 1

                continue

            # ----------------------------------------------
            # SAVE TO DATABASE
            # ----------------------------------------------

            try:

                saved_article = save_article(
                    article
                )

                if saved_article is None:

                    self.stats[
                        "duplicates"
                    ] += 1

                else:

                    self.stats[
                        "saved"
                    ] += 1

            except Exception as e:

                print(
                    f"Database error: {e}"
                )

                self.stats["failed"] += 1

        # --------------------------------------------------
        # 3. PRINT SUMMARY
        # --------------------------------------------------

        self.print_summary()

        return self.stats

    def print_summary(self):

        print("\n")
        print("=" * 70)
        print("COLLECTION SUMMARY")
        print("=" * 70)

        print(
            f"URLs discovered       : "
            f"{self.stats['discovered']}"
        )

        print(
            f"Successfully scraped  : "
            f"{self.stats['scraped']}"
        )

        print(
            f"Invalid articles      : "
            f"{self.stats['invalid']}"
        )

        print(
            f"Outside date range    : "
            f"{self.stats['outside_date_range']}"
        )

        print(
            f"Duplicates            : "
            f"{self.stats['duplicates']}"
        )

        print(
            f"Failed                : "
            f"{self.stats['failed']}"
        )

        print(
            f"Saved to database     : "
            f"{self.stats['saved']}"
        )

        print("=" * 70)