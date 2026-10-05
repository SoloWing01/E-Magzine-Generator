from app.scraper.news_scraper import NewsScraper


ARTICLE_URL = (
    "https://assamtribune.com/assam/"
    "land-crunch-hindering-assam-industry-says-cm-govt-plans-land-banks-estates-1616912"
)


def main():

    scraper = NewsScraper()

    article = scraper.scrape_article(ARTICLE_URL)

    if article is None:
        print("Scraping failed.")
        return

    print("\n" + "=" * 70)
    print("SCRAPING SUCCESSFUL")
    print("=" * 70)

    print(f"\nTitle:")
    print(article["title"])

    print(f"\nSource:")
    print(article["source"])

    print(f"\nAuthor:")
    print(article["author"])

    print(f"\nPublished date:")
    print(article["published_date"])

    print(f"\nURL:")
    print(article["url"])

    print("\nContent preview:")
    print("-" * 70)
    print(article["content"][:2000])
    print("-" * 70)


if __name__ == "__main__":
    main()