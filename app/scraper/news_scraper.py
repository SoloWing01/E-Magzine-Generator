from datetime import datetime

from app.scraper.base_scraper import BaseScraper


class NewsScraper(BaseScraper):

    SOURCE_NAME = "The Assam Tribune"

    def scrape_article(self, url: str):

        page = self.fetch_page(url)

        if page is None:
            return None

        try:
            # -----------------------------
            # TITLE
            # -----------------------------
            title = page.css("h1::text").get()

            if not title:
                print(f"Could not find title: {url}")
                return None

            title = title.strip()

            # -----------------------------
            # AUTHOR
            # -----------------------------
            author = page.css(
                ".hocal-feature-time-date-below-img "
                ".author::text"
            ).get()

            if author:
                author = author.strip()

            # -----------------------------
            # PUBLICATION DATE
            # -----------------------------
            date_string = page.css(
                "time.hocal-date "
                "span.convert-to-localtime::attr(data-datestring)"
            ).get()

            published_date = None

            if date_string:
                try:
                    published_date = datetime.strptime(
                        date_string.strip(),
                        "%Y-%m-%d %H:%M:%S"
                    )

                except ValueError:
                    print(
                        f"Could not parse date: {date_string}"
                    )

            # -----------------------------
            # CONTENT
            # -----------------------------
            paragraphs = page.css("article p::text").getall()

            content = "\n".join(
                p.strip()
                for p in paragraphs
                if p.strip()
            )

            # Fallback if article selector fails
            if not content:

                paragraphs = page.css("p::text").getall()

                content = "\n".join(
                    p.strip()
                    for p in paragraphs
                    if p.strip()
                )

            if not content:
                print(f"Could not extract content: {url}")
                return None

            # -----------------------------
            # RETURN ARTICLE
            # -----------------------------
            return {
                "title": title,
                "url": url,
                "source": self.SOURCE_NAME,
                "author": author,
                "published_date": published_date,
                "content": content,
            }

        except Exception as e:

            print(f"Failed to parse article: {url}")
            print(f"Error: {e}")

            return None