from scrapling.fetchers import Fetcher


class BaseScraper:
    """
    Base scraper using Scrapling.

    Provides a common method for fetching web pages.
    """

    def fetch_page(self, url: str):
        """
        Fetch a webpage using Scrapling.
        """

        try:
            page = Fetcher.get(
                url,
                stealthy_headers=True,
                timeout=30,
            )

            return page

        except Exception as e:
            print(f"Failed to fetch {url}")
            print(f"Error: {e}")
            return None