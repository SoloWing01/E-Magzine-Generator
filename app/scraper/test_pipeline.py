from app.scraper.news_scraper import NewsScraper
from app.preprocessing.date_filter import is_valid_date
from app.database.article_repository import save_article


ARTICLE_URL = (
    "https://assamtribune.com/assam/"
    "land-crunch-hindering-assam-industry-says-cm-govt-plans-land-banks-estates-1616912"
)


def main():

    print("=" * 70)
    print("NORTHEAST SENTINEL - ARTICLE PIPELINE")
    print("=" * 70)

    scraper = NewsScraper()

    # ------------------------------------------------
    # 1. SCRAPE
    # ------------------------------------------------

    print("\n[1] Scraping article...")

    article = scraper.scrape_article(ARTICLE_URL)

    if article is None:
        print("Scraping failed.")
        return

    print("Scraping successful.")

    # ------------------------------------------------
    # 2. DATE VALIDATION
    # ------------------------------------------------

    print("\n[2] Validating publication date...")

    published_date = article["published_date"]

    print(f"Published: {published_date}")

    if not is_valid_date(published_date):

        print("Article is outside the required date range.")
        return

    print("Article date is valid.")

    # ------------------------------------------------
    # 3. SAVE TO DATABASE
    # ------------------------------------------------

    print("\n[3] Saving article to SQLite...")

    saved_article = save_article(article)

    if saved_article is None:

        print("Article was already present in database.")

    else:

        print(
            f"Saved article ID: "
            f"{saved_article.id}"
        )

    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()