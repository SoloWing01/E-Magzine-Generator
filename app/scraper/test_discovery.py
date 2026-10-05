from app.scraper.article_discovery import ArticleDiscovery


def main():

    discovery = ArticleDiscovery()

    homepage = "https://assamtribune.com/"

    print("=" * 70)
    print("ARTICLE DISCOVERY TEST")
    print("=" * 70)

    urls = discovery.discover_articles(homepage)

    print(f"\nDiscovered URLs: {len(urls)}")

    for i, url in enumerate(urls[:30], start=1):
        print(f"{i:02d}. {url}")


if __name__ == "__main__":
    main()