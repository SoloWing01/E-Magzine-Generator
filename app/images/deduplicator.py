from dataclasses import dataclass
from pathlib import Path

from PIL import Image
import imagehash


@dataclass
class ImageDuplicateResult:
    """
    Result of comparing an image against previously seen images.
    """

    is_duplicate: bool
    duplicate_of: str | None
    similarity: float
    hash_distance: int


class ImageDeduplicator:
    """
    Detects duplicate and near-duplicate images.

    Uses:
        - SHA-256 for exact duplicates
        - perceptual hash for visually similar images
    """

    # Lower distance = more visually similar.
    DEFAULT_HASH_DISTANCE = 6

    def __init__(
        self,
        hash_distance: int = DEFAULT_HASH_DISTANCE,
    ):
        self.hash_distance = hash_distance

        # image_path -> perceptual hash
        self.hashes: dict[str, imagehash.ImageHash] = {}

    # ---------------------------------------------------------
    # IMAGE HASH
    # ---------------------------------------------------------

    @staticmethod
    def calculate_hash(
        image_path: str | Path,
    ) -> imagehash.ImageHash:
        """
        Calculate perceptual hash for an image.
        """

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        try:
            with Image.open(image_path) as image:

                # Convert to RGB so all supported image
                # formats are handled consistently.
                image = image.convert("RGB")

                return imagehash.phash(image)

        except Exception as e:
            raise ValueError(
                f"Could not calculate image hash "
                f"for {image_path}: {e}"
            ) from e

    # ---------------------------------------------------------
    # SIMILARITY
    # ---------------------------------------------------------

    @staticmethod
    def hash_distance_to_similarity(
        distance: int,
        hash_size: int = 8,
    ) -> float:
        """
        Convert Hamming distance to an approximate
        similarity score between 0 and 1.

        pHash with size 8 produces 64 bits.
        """

        max_distance = hash_size * hash_size

        similarity = 1.0 - (
            distance / max_distance
        )

        return max(
            0.0,
            min(1.0, similarity),
        )

    # ---------------------------------------------------------
    # FIND DUPLICATE
    # ---------------------------------------------------------

    def find_duplicate(
        self,
        image_path: str | Path,
    ) -> ImageDuplicateResult:
        """
        Compare an image against all previously registered
        images.
        """

        image_path = Path(image_path)

        current_hash = self.calculate_hash(
            image_path
        )

        # No previous images.
        if not self.hashes:

            self.hashes[str(image_path)] = current_hash

            return ImageDuplicateResult(
                is_duplicate=False,
                duplicate_of=None,
                similarity=0.0,
                hash_distance=64,
            )

        best_match = None
        best_distance = 64

        for existing_path, existing_hash in self.hashes.items():

            distance = current_hash - existing_hash

            if distance < best_distance:
                best_distance = distance
                best_match = existing_path

        similarity = self.hash_distance_to_similarity(
            best_distance
        )

        is_duplicate = (
            best_distance <= self.hash_distance
        )

        if not is_duplicate:
            self.hashes[str(image_path)] = current_hash

        return ImageDuplicateResult(
            is_duplicate=is_duplicate,
            duplicate_of=best_match if is_duplicate else None,
            similarity=similarity,
            hash_distance=best_distance,
        )

    # ---------------------------------------------------------
    # DEDUPLICATE LIST
    # ---------------------------------------------------------

    def deduplicate(
        self,
        image_paths: list[str | Path],
    ) -> list[Path]:
        """
        Remove duplicate images from a list.

        Returns only unique images.
        """

        unique_images = []

        for image_path in image_paths:

            result = self.find_duplicate(
                image_path
            )

            if result.is_duplicate:

                print(
                    f"DUPLICATE: {image_path}"
                )

                print(
                    f"  Duplicate of : "
                    f"{result.duplicate_of}"
                )

                print(
                    f"  Similarity   : "
                    f"{result.similarity:.4f}"
                )

                print(
                    f"  Hash distance: "
                    f"{result.hash_distance}"
                )

                continue

            unique_images.append(
                Path(image_path)
            )

        return unique_images

    # ---------------------------------------------------------
    # ARTICLE DIRECTORY
    # ---------------------------------------------------------

    def deduplicate_article(
        self,
        article_id: int,
        image_directory: str | Path,
    ) -> list[Path]:
        """
        Deduplicate all images belonging to one article.
        """

        image_directory = Path(
            image_directory
        )

        if not image_directory.exists():
            print(
                f"Image directory does not exist: "
                f"{image_directory}"
            )
            return []

        image_paths = []

        supported_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".gif",
            ".bmp",
            ".tiff",
        }

        for path in sorted(
            image_directory.iterdir()
        ):

            if not path.is_file():
                continue

            if path.suffix.lower() not in supported_extensions:
                continue

            image_paths.append(path)

        print("=" * 70)
        print("IMAGE DEDUPLICATION")
        print("=" * 70)

        print(
            f"Article ID       : {article_id}"
        )

        print(
            f"Images discovered: {len(image_paths)}"
        )

        unique_images = self.deduplicate(
            image_paths
        )

        print(
            f"Unique images    : "
            f"{len(unique_images)}"
        )

        print(
            f"Duplicates       : "
            f"{len(image_paths) - len(unique_images)}"
        )

        return unique_images


# -------------------------------------------------------------
# TEST
# -------------------------------------------------------------

if __name__ == "__main__":

    article_id = 29

    image_directory = (
        Path("data")
        / "images"
        / f"article_{article_id}"
    )

    deduplicator = ImageDeduplicator(
        hash_distance=6
    )

    unique_images = (
        deduplicator.deduplicate_article(
            article_id=article_id,
            image_directory=image_directory,
        )
    )

    print("\n" + "=" * 70)
    print("UNIQUE IMAGES")
    print("=" * 70)

    for index, image_path in enumerate(
        unique_images,
        start=1,
    ):

        print(
            f"{index}. {image_path}"
        )