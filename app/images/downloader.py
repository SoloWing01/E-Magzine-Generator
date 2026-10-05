from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import io
import re

import requests
from PIL import Image, UnidentifiedImageError

from app.config.settings import settings
from app.images.search import ImageSearchResult


@dataclass
class DownloadedImage:
    """
    Metadata for a successfully downloaded image.
    """

    article_id: int
    image_url: str
    source_url: str
    source: str

    file_path: str

    width: int
    height: int
    file_size: int

    content_type: str
    file_hash: str

    title: str = ""


class ImageDownloader:
    """
    Downloads and validates images for magazine articles.
    """

    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    )

    ALLOWED_CONTENT_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/bmp",
        "image/tiff",
    }

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    MIN_WIDTH = 300
    MIN_HEIGHT = 200

    def __init__(
        self,
        output_dir: str | None = None,
        timeout: int = 20,
    ):
        self.output_dir = Path(
            output_dir or settings.IMAGE_DIR
        )

        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": (
                    "image/avif,image/webp,image/apng,"
                    "image/svg+xml,image/*,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    # ---------------------------------------------------------
    # ARTICLE DIRECTORY
    # ---------------------------------------------------------

    def get_article_directory(
        self,
        article_id: int,
    ) -> Path:
        """
        Create and return the directory for one article.
        """

        article_dir = (
            self.output_dir /
            f"article_{article_id}"
        )

        article_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        return article_dir

    # ---------------------------------------------------------
    # DOWNLOAD
    # ---------------------------------------------------------

    def download(
        self,
        result: ImageSearchResult,
        article_id: int,
        image_number: int,
    ) -> DownloadedImage | None:
        """
        Download one image-search result.
        """

        if not result.image_url:
            print("Skipping image: empty image URL")
            return None

        article_dir = self.get_article_directory(
            article_id
        )

        print(
            f"Downloading image {image_number} "
            f"for article {article_id}"
        )

        print(f"URL: {result.image_url}")

        try:
            response = self.session.get(
                result.image_url,
                timeout=self.timeout,
                stream=True,
            )

            response.raise_for_status()

        except requests.RequestException as e:
            print(
                f"Download failed: "
                f"{result.image_url}"
            )
            print(f"Error: {e}")
            return None

        # -----------------------------------------------------
        # CONTENT TYPE
        # -----------------------------------------------------

        content_type = (
            response.headers
            .get("Content-Type", "")
            .split(";")[0]
            .lower()
            .strip()
        )

        if content_type not in self.ALLOWED_CONTENT_TYPES:
            print(
                f"Skipping unsupported content type: "
                f"{content_type}"
            )
            return None

        # -----------------------------------------------------
        # DOWNLOAD BYTES
        # -----------------------------------------------------

        try:
            data = response.content

        except Exception as e:
            print(f"Failed reading image data: {e}")
            return None

        if not data:
            print("Skipping empty image")
            return None

        if len(data) > self.MAX_FILE_SIZE:
            print(
                f"Skipping image larger than "
                f"{self.MAX_FILE_SIZE / (1024 * 1024):.1f} MB"
            )
            return None

        # -----------------------------------------------------
        # VALIDATE IMAGE
        # -----------------------------------------------------

        try:
            image = Image.open(
                io.BytesIO(data)
            )

            image.verify()

            # Re-open because verify() invalidates
            # the image object.
            image = Image.open(
                io.BytesIO(data)
            )

        except (
            UnidentifiedImageError,
            OSError,
        ) as e:

            print(
                f"Invalid image: {result.image_url}"
            )
            print(f"Error: {e}")

            return None

        width, height = image.size

        # -----------------------------------------------------
        # DIMENSION CHECK
        # -----------------------------------------------------

        if (
            width < self.MIN_WIDTH
            or height < self.MIN_HEIGHT
        ):
            print(
                f"Skipping low-resolution image: "
                f"{width}x{height}"
            )
            return None

        # -----------------------------------------------------
        # HASH
        # -----------------------------------------------------

        file_hash = hashlib.sha256(
            data
        ).hexdigest()

        # -----------------------------------------------------
        # FILE EXTENSION
        # -----------------------------------------------------

        extension = self._get_extension(
            image,
            content_type,
        )

        filename = (
            f"image_{image_number:02d}"
            f"_{file_hash[:12]}"
            f".{extension}"
        )

        file_path = article_dir / filename

        # -----------------------------------------------------
        # SAVE
        # -----------------------------------------------------

        try:
            with open(
                file_path,
                "wb",
            ) as file:

                file.write(data)

        except OSError as e:
            print(
                f"Failed saving image: {e}"
            )
            return None

        file_size = file_path.stat().st_size

        print(
            f"Downloaded successfully: "
            f"{width}x{height}, "
            f"{file_size / 1024:.1f} KB"
        )

        return DownloadedImage(
            article_id=article_id,
            image_url=result.image_url,
            source_url=result.source_url,
            source=result.source,
            file_path=str(file_path),
            width=width,
            height=height,
            file_size=file_size,
            content_type=content_type,
            file_hash=file_hash,
            title=result.title,
        )

    # ---------------------------------------------------------
    # DOWNLOAD MULTIPLE
    # ---------------------------------------------------------

    def download_results(
        self,
        results: list[ImageSearchResult],
        article_id: int,
        max_images: int = 5,
    ) -> list[DownloadedImage]:
        """
        Download multiple candidate images.
        """

        downloaded = []

        seen_urls = set()

        image_number = 1

        for result in results:

            if len(downloaded) >= max_images:
                break

            if not result.image_url:
                continue

            # Avoid duplicate URLs.
            if result.image_url in seen_urls:
                continue

            seen_urls.add(result.image_url)

            image = self.download(
                result=result,
                article_id=article_id,
                image_number=image_number,
            )

            if image is None:
                continue

            downloaded.append(image)

            image_number += 1

        print(
            f"\nDownloaded "
            f"{len(downloaded)}/{min(len(results), max_images)} "
            f"candidate images."
        )

        return downloaded

    # ---------------------------------------------------------
    # ARTICLE DOWNLOAD
    # ---------------------------------------------------------

    def download_for_article(
        self,
        article: dict,
        results: list[ImageSearchResult],
        max_images: int = 5,
    ) -> list[DownloadedImage]:
        """
        Download images for an article dictionary.
        """

        article_id = article.get("id")

        if article_id is None:
            raise ValueError(
                "Article must contain an 'id'."
            )

        return self.download_results(
            results=results,
            article_id=article_id,
            max_images=max_images,
        )

    # ---------------------------------------------------------
    # EXTENSION
    # ---------------------------------------------------------

    @staticmethod
    def _get_extension(
        image: Image.Image,
        content_type: str,
    ) -> str:
        """
        Determine a safe file extension.
        """

        format_map = {
            "JPEG": "jpg",
            "PNG": "png",
            "WEBP": "webp",
            "GIF": "gif",
            "BMP": "bmp",
            "TIFF": "tiff",
        }

        if image.format in format_map:
            return format_map[image.format]

        content_type_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
            "image/bmp": "bmp",
            "image/tiff": "tiff",
        }

        return content_type_map.get(
            content_type,
            "img",
        )

    # ---------------------------------------------------------
    # EXISTING HASH CHECK
    # ---------------------------------------------------------

    def image_hash_exists(
        self,
        article_id: int,
        file_hash: str,
    ) -> bool:
        """
        Check whether an image with the same SHA-256 hash
        already exists for an article.
        """

        article_dir = self.get_article_directory(
            article_id
        )

        for file_path in article_dir.iterdir():

            if not file_path.is_file():
                continue

            if file_hash in file_path.name:
                return True

        return False

    # ---------------------------------------------------------
    # METADATA EXPORT
    # ---------------------------------------------------------

    @staticmethod
    def to_dict(
        image: DownloadedImage,
    ) -> dict:
        """
        Convert DownloadedImage to a dictionary.
        """

        return asdict(image)


# -------------------------------------------------------------
# SIMPLE TEST
# -------------------------------------------------------------

if __name__ == "__main__":

    from app.images.search import ImageSearch

    searcher = ImageSearch()

    downloader = ImageDownloader()

    test_article = {
        "id": 29,
        "title": (
            "Assam Rifles seize heroin worth Rs 5.07 cr "
            "in Mizoram, nab two Myanmar nationals"
        ),
        "category": "Security & Strategic Affairs",
        "source": "The Assam Tribune",
    }

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    results = searcher.search_for_article(
        test_article,
        max_results=5,
    )

    # ---------------------------------------------------------
    # DOWNLOAD
    # ---------------------------------------------------------

    downloaded = downloader.download_for_article(
        article=test_article,
        results=results,
        max_images=5,
    )

    # ---------------------------------------------------------
    # PRINT RESULTS
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("DOWNLOADED IMAGES")
    print("=" * 70)

    for image in downloaded:

        print("\n" + "-" * 70)

        print(
            f"Article ID : {image.article_id}"
        )

        print(
            f"File       : {image.file_path}"
        )

        print(
            f"Dimensions : "
            f"{image.width}x{image.height}"
        )

        print(
            f"Size       : "
            f"{image.file_size / 1024:.1f} KB"
        )

        print(
            f"Hash       : "
            f"{image.file_hash}"
        )

        print(
            f"Image URL  : "
            f"{image.image_url}"
        )

        print(
            f"Source URL : "
            f"{image.source_url}"
        )