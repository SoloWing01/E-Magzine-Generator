from urllib.parse import urljoin, urlparse

from app.scraper.base_scraper import BaseScraper


class ArticleDiscovery(BaseScraper):

    BASE_URL = "https://assamtribune.com"

    def discover_articles(self, page_url: str) -> list[str]:
        """
        Discover article URLs from a listing/homepage.
        """

        page = self.fetch_page(page_url)

        if page is None:
            return []

        links = page.css("a::attr(href)").getall()

        article_urls = set()

        for link in links:

            if not link:
                continue

            link = link.strip()

            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(
                self.BASE_URL,
                link
            )

            parsed = urlparse(absolute_url)

            # Only keep Assam Tribune URLs
            if parsed.netloc != "assamtribune.com":
                continue

            # Remove query strings/fragments
            clean_url = (
                f"{parsed.scheme}://"
                f"{parsed.netloc}"
                f"{parsed.path}"
            )

            # Basic article URL filtering
            if self.is_article_url(clean_url):
                article_urls.add(clean_url)

        return sorted(article_urls)

    @staticmethod
    def is_article_url(url: str) -> bool:
        """
        Basic filter for Assam Tribune article URLs.
        """

        path = urlparse(url).path.lower()

        # Ignore homepage
        if path in ("", "/"):
            return False

        # Ignore obvious non-article pages
        excluded = [
            "/category/",
            "/author/",
            "/tag/",
            "/search",
            "/epaper/",
            "/videos/",
            "/photos/",
        ]

        if any(path.startswith(item) for item in excluded):
            return False

        # Assam Tribune article URLs generally have
        # multiple path components or a long slug.
        if len(path.strip("/").split("/")) < 2:
            return False

        return True