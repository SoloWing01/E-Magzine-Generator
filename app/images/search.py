from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse
import json
import re

import requests
from bs4 import BeautifulSoup


@dataclass
class ImageSearchResult:
    image_url: str
    source_url: str
    title: str
    source: str
    thumbnail_url: str | None = None
    query: str = ""
    source_domain: str = ""


class ImageSearch:
    """
    Article-aware image discovery.

    Priority:

        1. Original article image
        2. Article metadata image
        3. Article-body editorial images
        4. External image search, if configured

    The search layer is intentionally conservative.

    CLIP in relevance.py remains the final semantic validator.
    """

    # ------------------------------------------------------------------
    # TEXT FILTERS
    # ------------------------------------------------------------------

    STOPWORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "for",
        "with",
        "from",
        "by",
        "at",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "this",
        "that",
        "these",
        "those",
        "over",
        "under",
        "after",
        "before",
        "into",
        "amid",
        "says",
        "said",
        "worth",
        "nab",
        "two",
        "three",
        "new",
        "news",
    }

    GENERIC_TERMS = {
        "assam",
        "northeast",
        "northeastern",
        "india",
        "indian",
        "state",
        "states",
        "district",
        "city",
        "region",
        "government",
        "centre",
        "central",
        "official",
        "officials",
        "people",
        "person",
        "report",
        "reports",
    }

    EVENT_TERMS = {
        "army",
        "assam rifles",
        "military",
        "defence",
        "defense",
        "border",
        "security",
        "heroin",
        "narcotics",
        "drug",
        "drugs",
        "trafficking",
        "smuggling",
        "operation",
        "operations",
        "raid",
        "seized",
        "seizure",
        "arrested",
        "arrest",
        "election",
        "bypoll",
        "poll",
        "cricket",
        "football",
        "marathon",
        "coffee",
        "farmers",
        "infrastructure",
        "railway",
        "station",
        "industry",
        "industrial",
        "development",
        "funding",
        "protest",
        "protests",
        "school",
        "students",
        "youth",
        "cattle",
        "garbage",
        "civic",
        "missing",
        "kuki",
        "manipur",
        "mizoram",
        "nagaland",
        "meghalaya",
        "tripura",
        "sikkim",
        "arunachal",
    }

    NORTHEAST_LOCATIONS = {
        "assam",
        "mizoram",
        "manipur",
        "nagaland",
        "meghalaya",
        "tripura",
        "sikkim",
        "arunachal",
        "arunachal pradesh",
        "guwahati",
        "nagaon",
        "lumding",
        "aizawl",
        "kohima",
        "imphal",
        "shillong",
        "agartala",
        "gangtok",
        "itanagar",
        "kangpokpi",
    }

    # ------------------------------------------------------------------
    # BLOCKED DOMAINS
    # ------------------------------------------------------------------

    BLOCKED_DOMAIN_PATTERNS = [
        "pinterest.",
        "pinimg.",
        "pngtree.",
        "stock.adobe.",
        "shutterstock.",
        "istockphoto.",
        "gettyimages.",
        "alamy.",
        "dreamstime.",
        "freepik.",
        "depositphotos.",
        "vecteezy.",
        "canva.",
        "unsplash.",
        "pexels.",
        "pixabay.",
        "wallpaper.",
        "clipart.",
        "mapnations.",
        "tourmyodisha.",
        "sandpebblestours.",
        "assamtourism.",
        "incredible-northeastindia.",
    ]

    # ------------------------------------------------------------------
    # PUBLISHER / NEWS DOMAINS
    # ------------------------------------------------------------------

    HIGH_QUALITY_DOMAINS = {
        "assamtribune.com",
        "pib.gov.in",
        "mea.gov.in",
        "mod.gov.in",
        "mha.gov.in",
        "indianarmy.nic.in",
        "airnewsalerts.com",
        "thehindu.com",
        "indianexpress.com",
        "hindustantimes.com",
        "timesofindia.indiatimes.com",
        "telegraphindia.com",
        "theprint.in",
        "deccanherald.com",
        "news18.com",
        "ndtv.com",
    }

    MEDIUM_QUALITY_DOMAINS = {
        "eastmojo.com",
        "nenow.in",
        "northeasttoday.in",
        "sentinelassam.com",
        "pratidintime.com",
        "assamlive.com",
        "guwahatiplus.com",
    }

    # ------------------------------------------------------------------
    # IMAGE ASSET FILTERS
    # ------------------------------------------------------------------

    BLOCKED_IMAGE_EXTENSIONS = {
        ".svg",
        ".ico",
        ".gif",
    }

    UI_IMAGE_TERMS = {
        "logo",
        "icon",
        "favicon",
        "search",
        "clear",
        "close",
        "menu",
        "arrow",
        "facebook",
        "twitter",
        "instagram",
        "youtube",
        "linkedin",
        "whatsapp",
        "share",
        "print",
        "placeholder",
        "authorplaceholder",
        "avatar",
        "profile",
        "default",
        "loading",
        "loader",
        "spinner",
        "banner-ad",
        "advertisement",
        "advert",
        "cookie",
    }

    # Known generic UI/image paths.
    BLOCKED_IMAGE_PATHS = {
        "/images/logo.svg",
        "/images/search.png",
        "/images/clear-button-white.png",
        "/images/placeholder.jpg",
        "/images/authorplaceholder.jpg",
    }

    # ------------------------------------------------------------------
    # INITIALIZATION
    # ------------------------------------------------------------------

    def __init__(
        self,
        bing_api_url: str | None = None,
        bing_api_key: str | None = None,
        timeout: int = 15,
    ):
        self.bing_api_url = bing_api_url
        self.bing_api_key = bing_api_key
        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/154.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,image/avif,image/webp,"
                    "*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    # ==================================================================
    # DOMAIN HELPERS
    # ==================================================================

    @staticmethod
    def normalize_domain(url: str) -> str:
        try:
            domain = urlparse(url).netloc.lower()

            if domain.startswith("www."):
                domain = domain[4:]

            return domain

        except Exception:
            return ""

    @staticmethod
    def same_domain(url1: str, url2: str) -> bool:
        domain1 = ImageSearch.normalize_domain(url1)
        domain2 = ImageSearch.normalize_domain(url2)

        if not domain1 or not domain2:
            return False

        return (
            domain1 == domain2
            or domain1.endswith("." + domain2)
            or domain2.endswith("." + domain1)
        )

    def is_blocked_domain(self, url: str) -> bool:
        domain = self.normalize_domain(url)

        if not domain:
            return True

        return any(
            pattern in domain
            for pattern in self.BLOCKED_DOMAIN_PATTERNS
        )

    def source_priority(self, url: str) -> int:
        domain = self.normalize_domain(url)

        if self.is_blocked_domain(url):
            return 0

        if domain in self.HIGH_QUALITY_DOMAINS:
            return 3

        if domain in self.MEDIUM_QUALITY_DOMAINS:
            return 2

        return 1

    # ==================================================================
    # URL HELPERS
    # ==================================================================

    @staticmethod
    def clean_image_url(url: str) -> str:
        """
        Normalize image URL.

        Removes fragments while preserving query parameters because
        some image CDNs require them.
        """

        if not url:
            return ""

        url = url.strip()

        if url.startswith("//"):
            url = "https:" + url

        parsed = urlparse(url)

        parsed = parsed._replace(fragment="")

        return urlunparse(parsed)

    @staticmethod
    def image_extension(url: str) -> str:
        path = urlparse(url).path.lower()

        match = re.search(
            r"\.(jpg|jpeg|png|webp|bmp|tiff|tif|gif|svg|ico)$",
            path,
        )

        if not match:
            return ""

        return "." + match.group(1)

    def is_probable_image_url(self, url: str) -> bool:
        """
        Determine whether a URL looks like a real image rather than
        a webpage/UI resource.
        """

        if not url:
            return False

        url = self.clean_image_url(url)

        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        domain = self.normalize_domain(url)

        if not domain:
            return False

        if self.is_blocked_domain(url):
            return False

        path = parsed.path.lower()

        # Explicitly blocked image paths.
        if path in self.BLOCKED_IMAGE_PATHS:
            return False

        # Reject known UI words.
        filename = path.rsplit("/", 1)[-1]

        filename_without_ext = re.sub(
            r"\.(jpg|jpeg|png|webp|bmp|tiff|tif|gif|svg|ico)$",
            "",
            filename,
        )

        normalized_filename = re.sub(
            r"[^a-z0-9]+",
            "",
            filename_without_ext,
        )

        for term in self.UI_IMAGE_TERMS:
            normalized_term = re.sub(
                r"[^a-z0-9]+",
                "",
                term,
            )

            if normalized_term and normalized_term in normalized_filename:
                return False

        # Reject UI directories.
        blocked_path_terms = {
            "/icons/",
            "/icon/",
            "/favicon/",
            "/avatars/",
            "/avatar/",
            "/profile/",
            "/profiles/",
            "/static/icons/",
            "/static/icon/",
            "/assets/icons/",
            "/assets/icon/",
        }

        if any(term in path for term in blocked_path_terms):
            return False

        # SVG / favicon files should never be article photographs.
        extension = self.image_extension(url)

        if extension in self.BLOCKED_IMAGE_EXTENSIONS:
            return False

        # Known image extensions.
        valid_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".bmp",
            ".tiff",
            ".tif",
        }

        if extension in valid_extensions:
            return True

        # Common image upload paths even when the URL does not end in
        # a conventional extension.
        upload_paths = (
            "/h-upload/",
            "/uploads/",
            "/upload/",
            "/images/",
            "/image/",
            "/media/",
            "/wp-content/uploads/",
            "/wp-content/",
        )

        if any(path.startswith(prefix) for prefix in upload_paths):
            return True

        return False

    # ==================================================================
    # IMAGE URL DEDUPLICATION
    # ==================================================================

    @staticmethod
    def image_identity(url: str) -> str:
        """
        Create a stable identity for image URLs.

        JPG and WEBP versions of the same image on Assam Tribune use
        the same base filename, so:

            photo.jpg
            photo.webp

        are treated as the same candidate.
        """

        url = ImageSearch.clean_image_url(url)

        parsed = urlparse(url)

        path = parsed.path.lower()

        # Remove extension.
        path = re.sub(
            r"\.(jpg|jpeg|png|webp|bmp|tiff|tif)$",
            "",
            path,
        )

        # Remove common resizing suffixes.
        path = re.sub(
            r"[-_](jpg|jpeg|png|webp)$",
            "",
            path,
        )

        # Remove common query strings used only for resizing.
        ignored_query_keys = {
            "width",
            "height",
            "w",
            "h",
            "resize",
            "format",
            "quality",
            "q",
            "fm",
        }

        query_pairs = []

        for pair in parsed.query.split("&"):
            if "=" not in pair:
                continue

            key, value = pair.split("=", 1)

            if key.lower() in ignored_query_keys:
                continue

            query_pairs.append(
                f"{key.lower()}={value}"
            )

        query = "&".join(sorted(query_pairs))

        return (
            f"{parsed.netloc.lower()}"
            f"{path}"
            f"{'?' + query if query else ''}"
        )

    def deduplicate_results(
        self,
        results: list[ImageSearchResult],
    ) -> list[ImageSearchResult]:
        """
        Remove duplicate URLs and JPG/WEBP variants.

        Keeps the first result because metadata order is intentional:
        og:image -> twitter:image -> JSON-LD -> article image.
        """

        unique = []
        seen = set()

        for result in results:
            identity = self.image_identity(
                result.image_url
            )

            if not identity:
                continue

            if identity in seen:
                continue

            seen.add(identity)
            unique.append(result)

        return unique

    # ==================================================================
    # QUERY GENERATION
    # ==================================================================

    def build_queries(
        self,
        title: str,
        content: str = "",
        category: str | None = None,
        source: str | None = None,
    ) -> list[str]:
        """
        Build article-aware image search queries.

        Generic terms are removed so the query remains focused on the
        actual event/topic.
        """

        title = title or ""
        content = content or ""
        category = category or ""
        source = source or ""

        title_lower = title.lower()

        words = re.findall(
            r"[a-zA-Z][a-zA-Z'-]+",
            title_lower,
        )

        useful_words = []

        for word in words:
            word = word.strip("'")

            if len(word) < 3:
                continue

            if word in self.STOPWORDS:
                continue

            if word in self.GENERIC_TERMS:
                continue

            if word not in useful_words:
                useful_words.append(word)

        # Event terms explicitly appearing in the title.
        event_terms = []

        for term in sorted(
            self.EVENT_TERMS,
            key=len,
            reverse=True,
        ):
            if term in title_lower:
                event_terms.append(term)

        # Locations explicitly appearing in the title.
        locations = []

        for location in sorted(
            self.NORTHEAST_LOCATIONS,
            key=len,
            reverse=True,
        ):
            if location in title_lower:
                locations.append(location)

        queries = []

        # --------------------------------------------------------------
        # Query 1: strongest event/location query
        # --------------------------------------------------------------

        if event_terms and locations:
            query = " ".join(
                event_terms[:3] + locations[:2]
            )

            queries.append(query)

        # --------------------------------------------------------------
        # Query 2: meaningful title terms
        # --------------------------------------------------------------

        title_terms = useful_words[:7]

        if title_terms:
            query = " ".join(title_terms)

            if locations:
                query += " " + " ".join(locations[:2])

            queries.append(query)

        # --------------------------------------------------------------
        # Query 3: editorial/news photo
        # --------------------------------------------------------------

        if title_terms:
            query = " ".join(title_terms[:6])

            if locations:
                query += " " + locations[0]

            query += " news photo"

            queries.append(query)

        # --------------------------------------------------------------
        # Query 4: category-specific query
        # --------------------------------------------------------------

        if title_terms and category:
            query = " ".join(title_terms[:5])

            if locations:
                query += " " + locations[0]

            query += f" {category.lower()} photo"

            queries.append(query)

        # Remove duplicates.
        final_queries = []

        for query in queries:
            query = re.sub(
                r"\s+",
                " ",
                query,
            ).strip()

            if query and query not in final_queries:
                final_queries.append(query)

        return final_queries[:4]

    def build_query(
        self,
        title: str,
        content: str = "",
    ) -> str:
        """
        Backward-compatible single-query method.
        """

        queries = self.build_queries(
            title=title,
            content=content,
        )

        return queries[0] if queries else title

    # ==================================================================
    # ARTICLE PAGE FETCH
    # ==================================================================

    def fetch_article_page(
        self,
        article_url: str,
    ):
        try:
            response = self.session.get(
                article_url,
                timeout=self.timeout,
                allow_redirects=True,
            )

            response.raise_for_status()

            return response

        except Exception as e:
            print(
                "Could not fetch article page "
                f"for image extraction: {e}"
            )

            return None

    # Backward-compatible alias.
    def search_article_page(
        self,
        article: dict,
        max_results: int = 5,
    ) -> list[ImageSearchResult]:
        return self.extract_article_images(
            article=article,
            max_results=max_results,
        )

    # ==================================================================
    # ARTICLE IMAGE EXTRACTION
    # ==================================================================

    def extract_article_images(
        self,
        article: dict,
        max_results: int = 5,
    ) -> list[ImageSearchResult]:
        """
        Extract only useful editorial images from the article.

        Priority:

            1. og:image
            2. twitter:image
            3. JSON-LD
            4. article-body images

        Site-wide UI assets are explicitly rejected.
        """

        article_url = article.get("url")

        if not article_url:
            return []

        response = self.fetch_article_page(
            article_url
        )

        if response is None:
            return []

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        article_title = (
            article.get("title", "") or ""
        ).strip()

        publisher_domain = self.normalize_domain(
            article_url
        )

        candidates: list[tuple[str, str]] = []

        # --------------------------------------------------------------
        # Helper
        # --------------------------------------------------------------

        def add_candidate(
            image_url: str | None,
            source_type: str,
            require_same_domain: bool = True,
        ):
            if not image_url:
                return

            image_url = image_url.strip()

            image_url = urljoin(
                article_url,
                image_url,
            )

            image_url = self.clean_image_url(
                image_url
            )

            if not image_url:
                return

            if not self.is_probable_image_url(
                image_url
            ):
                return

            if self.is_blocked_domain(
                image_url
            ):
                return

            image_domain = self.normalize_domain(
                image_url
            )

            if require_same_domain:
                if not self.same_domain(
                    image_url,
                    article_url,
                ):
                    return

            # Extra protection against obvious external
            # non-publisher image sources.
            if (
                publisher_domain
                and image_domain != publisher_domain
                and require_same_domain
            ):
                return

            candidates.append(
                (
                    image_url,
                    source_type,
                )
            )

        # --------------------------------------------------------------
        # 1. Open Graph
        # --------------------------------------------------------------

        for meta in soup.find_all(
            "meta",
            attrs={
                "property": "og:image"
            },
        ):
            add_candidate(
                meta.get("content"),
                "og:image",
                require_same_domain=True,
            )

        # --------------------------------------------------------------
        # 2. Twitter image
        # --------------------------------------------------------------

        for meta in soup.find_all(
            "meta",
            attrs={
                "name": "twitter:image"
            },
        ):
            add_candidate(
                meta.get("content"),
                "twitter:image",
                require_same_domain=True,
            )

        # Also support property="twitter:image".
        for meta in soup.find_all(
            "meta",
            attrs={
                "property": "twitter:image"
            },
        ):
            add_candidate(
                meta.get("content"),
                "twitter:image",
                require_same_domain=True,
            )

        # --------------------------------------------------------------
        # 3. JSON-LD
        # --------------------------------------------------------------

        def extract_jsonld_images(value):
            images = []

            if isinstance(value, dict):
                image = value.get("image")

                if image:
                    if isinstance(image, str):
                        images.append(image)

                    elif isinstance(image, dict):
                        url = (
                            image.get("url")
                            or image.get("contentUrl")
                        )

                        if url:
                            images.append(url)

                    elif isinstance(image, list):
                        for item in image:
                            if isinstance(item, str):
                                images.append(item)

                            elif isinstance(item, dict):
                                url = (
                                    item.get("url")
                                    or item.get("contentUrl")
                                )

                                if url:
                                    images.append(url)

                for key, item in value.items():
                    if key != "image":
                        images.extend(
                            extract_jsonld_images(item)
                        )

            elif isinstance(value, list):
                for item in value:
                    images.extend(
                        extract_jsonld_images(item)
                    )

            return images

        for script in soup.find_all(
            "script",
            type="application/ld+json",
        ):
            raw = script.string

            if not raw:
                continue

            try:
                data = json.loads(raw)

            except Exception:
                continue

            for image_url in extract_jsonld_images(
                data
            ):
                add_candidate(
                    image_url,
                    "json-ld",
                    require_same_domain=True,
                )

        # --------------------------------------------------------------
        # 4. Article body images
        # --------------------------------------------------------------

        article_nodes = []

        # Prefer semantic article tag.
        article_nodes.extend(
            soup.find_all("article")
        )

        # Common news article containers.
        if not article_nodes:
            for selector in [
                ".article-content",
                ".article-body",
                ".story-content",
                ".story-body",
                ".post-content",
                ".entry-content",
                ".content-body",
                "main",
            ]:
                article_nodes.extend(
                    soup.select(selector)
                )

        # Remove duplicate nodes.
        unique_nodes = []

        seen_node_ids = set()

        for node in article_nodes:
            node_id = id(node)

            if node_id in seen_node_ids:
                continue

            seen_node_ids.add(node_id)
            unique_nodes.append(node)

        for node in unique_nodes:
            for img in node.find_all("img"):
                # Prefer src, then lazy-loading attributes.
                image_url = (
                    img.get("src")
                    or img.get("data-src")
                    or img.get("data-original")
                    or img.get("data-lazy-src")
                )

                if not image_url:
                    srcset = (
                        img.get("srcset")
                        or img.get("data-srcset")
                    )

                    if srcset:
                        # Pick the last/highest-resolution candidate.
                        parts = [
                            p.strip()
                            for p in srcset.split(",")
                            if p.strip()
                        ]

                        if parts:
                            image_url = (
                                parts[-1]
                                .split(" ")[0]
                            )

                # Important:
                # Article body images must also be on the
                # publisher domain.
                add_candidate(
                    image_url,
                    "article-img",
                    require_same_domain=True,
                )

        # --------------------------------------------------------------
        # Convert candidates to ImageSearchResult
        # --------------------------------------------------------------

        results = []

        for image_url, source_type in candidates:
            results.append(
                ImageSearchResult(
                    image_url=image_url,
                    source_url=article_url,
                    title=article_title,
                    source=article.get(
                        "source",
                        self.normalize_domain(
                            article_url
                        ),
                    ),
                    thumbnail_url=None,
                    query="",
                    source_domain=self.normalize_domain(
                        image_url
                    ),
                )
            )

        # --------------------------------------------------------------
        # Deduplicate JPG/WEBP variants
        # --------------------------------------------------------------

        results = self.deduplicate_results(
            results
        )

        # --------------------------------------------------------------
        # Prefer metadata images over body images.
        # --------------------------------------------------------------

        priority = {
            "og:image": 0,
            "twitter:image": 1,
            "json-ld": 2,
            "article-img": 3,
        }

        # We need to recover source type from candidates.
        source_type_map = {}

        for image_url, source_type in candidates:
            source_type_map[
                self.image_identity(image_url)
            ] = source_type

        results.sort(
            key=lambda result: priority.get(
                source_type_map.get(
                    self.image_identity(
                        result.image_url
                    ),
                    "article-img",
                ),
                99,
            )
        )

        results = results[:max_results]

        print(
            "\nARTICLE IMAGE EXTRACTION"
        )

        for result in results:
            source_type = source_type_map.get(
                self.image_identity(
                    result.image_url
                ),
                "unknown",
            )

            print(
                f"  ORIGINAL [{source_type}]: "
                f"{result.image_url}"
            )

        print(
            f"Found {len(results)} usable "
            "editorial image(s) from original article."
        )

        return results

    # Backward-compatible alias.
    def get_article_images(
        self,
        article: dict,
        max_results: int = 5,
    ) -> list[ImageSearchResult]:
        return self.extract_article_images(
            article=article,
            max_results=max_results,
        )

    # ==================================================================
    # BING IMAGE SEARCH
    # ==================================================================

    def search_bing_images(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[ImageSearchResult]:
        """
        Optional Bing image search.

        This is only used when API credentials are supplied.

        It is intentionally secondary to original article images.
        """

        if not self.bing_api_url:
            return []

        if not self.bing_api_key:
            return []

        if not query:
            return []

        headers = {
            "Ocp-Apim-Subscription-Key": self.bing_api_key,
        }

        params = {
            "q": query,
            "count": max_results,
            "safeSearch": "Strict",
            "imageType": "Photo",
        }

        try:
            response = self.session.get(
                self.bing_api_url,
                headers=headers,
                params=params,
                timeout=self.timeout,
            )

            response.raise_for_status()

            data = response.json()

        except Exception as e:
            print(
                f"Bing image search failed: {e}"
            )

            return []

        results = []

        for item in data.get(
            "value",
            [],
        ):
            image_url = (
                item.get("contentUrl")
                or item.get("thumbnailUrl")
            )

            source_url = (
                item.get("hostPageUrl")
                or ""
            )

            if not image_url:
                continue

            if not self.is_probable_image_url(
                image_url
            ):
                continue

            if self.is_blocked_domain(
                image_url
            ):
                continue

            source_domain = self.normalize_domain(
                source_url or image_url
            )

            results.append(
                ImageSearchResult(
                    image_url=image_url,
                    source_url=source_url,
                    title=item.get(
                        "name",
                        query,
                    ),
                    source=source_domain,
                    thumbnail_url=item.get(
                        "thumbnailUrl"
                    ),
                    query=query,
                    source_domain=source_domain,
                )
            )

        return self.deduplicate_results(
            results
        )[:max_results]

    # ==================================================================
    # GENERAL SEARCH
    # ==================================================================

    def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[ImageSearchResult]:
        """
        External image search.

        If Bing is not configured, return no external results.

        This prevents generic uncontrolled web-image discovery from
        polluting the pipeline.
        """

        if not query:
            return []

        results = self.search_bing_images(
            query=query,
            max_results=max_results,
        )

        results = [
            result
            for result in results
            if not self.is_blocked_domain(
                result.image_url
            )
        ]

        results = self.deduplicate_results(
            results
        )

        # Prefer higher-quality source domains.
        results.sort(
            key=lambda result: (
                self.source_priority(
                    result.image_url
                ),
                result.source_domain,
            ),
            reverse=True,
        )

        return results[:max_results]

    # ==================================================================
    # ARTICLE-AWARE SEARCH
    # ==================================================================

    def search_for_article(
        self,
        article: dict,
        max_results: int = 5,
    ) -> list[ImageSearchResult]:
        """
        Main image-search method used by pipeline.py.

        Priority:

            1. Original article images
            2. External image search only if no article image exists
        """

        title = article.get(
            "title",
            "",
        )

        content = article.get(
            "content",
            "",
        )

        category = article.get(
            "category",
            None,
        )

        source = article.get(
            "source",
            None,
        )

        # --------------------------------------------------------------
        # FIRST: ORIGINAL ARTICLE
        # --------------------------------------------------------------

        article_results = self.extract_article_images(
            article=article,
            max_results=max_results,
        )

        if article_results:
            print(
                "\nUsing original article images."
            )

            return article_results[:max_results]

        # --------------------------------------------------------------
        # SECOND: EXTERNAL SEARCH
        # --------------------------------------------------------------

        queries = self.build_queries(
            title=title,
            content=content,
            category=category,
            source=source,
        )

        print(
            "\nNo usable original article image found."
        )

        print(
            "Generated image queries:"
        )

        for index, query in enumerate(
            queries,
            start=1,
        ):
            print(
                f"  {index}. {query}"
            )

        all_results = []

        for query in queries:
            results = self.search(
                query=query,
                max_results=max_results,
            )

            all_results.extend(results)

            if len(all_results) >= max_results:
                break

        all_results = self.deduplicate_results(
            all_results
        )

        return all_results[:max_results]


# ======================================================================
# LOCAL TEST
# ======================================================================

if __name__ == "__main__":

    searcher = ImageSearch()

    article = {
        "id": 29,
        "title": (
            "Assam Rifles seize heroin worth Rs 5.07 cr "
            "in Mizoram, nab two Myanmar nationals"
        ),
        "url": (
            "https://assamtribune.com/north-east/"
            "assam-rifles-seize-heroin-worth-rs-507-cr-"
            "in-mizoram-nab-two-myanmar-nationals-1619285"
        ),
        "source": "The Assam Tribune",
        "category": "Security & Strategic Affairs",
        "content": (
            "Assam Rifles seized heroin in Mizoram "
            "during an operation along the "
            "India-Myanmar border."
        ),
    }

    print(
        "=" * 70
    )
    print(
        "IMAGE SEARCH TEST"
    )
    print(
        "=" * 70
    )

    results = searcher.search_for_article(
        article,
        max_results=5,
    )

    print(
        "\n"
        + "=" * 70
    )
    print(
        "FINAL RESULTS"
    )
    print(
        "=" * 70
    )

    for index, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"\n{index}. {result.image_url}"
        )
        print(
            f"   Source: {result.source}"
        )
        print(
            f"   Domain: {result.source_domain}"
        )