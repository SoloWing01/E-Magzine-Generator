from dataclasses import dataclass
from pathlib import Path

import torch
import torch.nn.functional as F
from PIL import Image
from transformers import CLIPModel, CLIPProcessor


@dataclass
class ImageRelevanceResult:
    """
    Relevance result for one image against an article.
    """

    image_path: str
    score: float
    rank: int = 0
    is_relevant: bool = False


class ImageRelevance:
    """
    Calculates article-image semantic relevance using CLIP.

    Text:
        Article title + article content

    Image:
        Candidate image

    Output:
        Cosine similarity score between text and image embeddings.
    """

    MODEL_NAME = "openai/clip-vit-base-patch32"

    # Initial threshold.
    # We will calibrate this after testing real images.
    DEFAULT_THRESHOLD = 0.20

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        self.model_name = model_name
        self.threshold = threshold

        # -----------------------------------------------------
        # DEVICE
        # -----------------------------------------------------

        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print("=" * 70)
        print("IMAGE RELEVANCE MODEL")
        print("=" * 70)

        print(f"Model  : {self.model_name}")
        print(f"Device : {self.device}")

        if self.device == "cuda":
            print(
                f"GPU    : "
                f"{torch.cuda.get_device_name(0)}"
            )

        # -----------------------------------------------------
        # PROCESSOR
        # -----------------------------------------------------

        self.processor = CLIPProcessor.from_pretrained(
            self.model_name
        )

        # -----------------------------------------------------
        # MODEL
        # -----------------------------------------------------

        self.model = CLIPModel.from_pretrained(
            self.model_name
        )

        self.model.to(self.device)

        self.model.eval()

        print("Model loaded successfully.")

    # ---------------------------------------------------------
    # TEXT EMBEDDING
    # ---------------------------------------------------------

    @torch.no_grad()
    def encode_text(
        self,
        text: str,
    ) -> torch.Tensor:
        """
        Generate normalized CLIP text embedding.
        """

        if not text or not text.strip():
            raise ValueError("Text cannot be empty.")

        inputs = self.processor(
            text=[text],
            return_tensors="pt",
            padding=True,
            truncation=True,
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        # Use the CLIP text model directly.
        text_outputs = self.model.text_model(
            input_ids=inputs["input_ids"],
            attention_mask=inputs.get("attention_mask"),
        )

        # CLIP uses the pooled representation.
        pooled_output = text_outputs.pooler_output

        # Project into the shared CLIP embedding space.
        text_features = self.model.text_projection(
            pooled_output
        )

        text_features = F.normalize(
            text_features,
            p=2,
            dim=-1,
        )

        return text_features

    # ---------------------------------------------------------
    # IMAGE EMBEDDING
    # ---------------------------------------------------------

    @torch.no_grad()
    def encode_image(
        self,
        image_path: str | Path,
    ) -> torch.Tensor:
        """
        Generate normalized CLIP image embedding.
        """

        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        try:
            image = Image.open(
                image_path
            ).convert("RGB")

        except Exception as e:
            raise ValueError(
                f"Could not open image "
                f"{image_path}: {e}"
            ) from e

        inputs = self.processor(
            images=image,
            return_tensors="pt",
        )

        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }

        # Use CLIP vision model directly.
        vision_outputs = self.model.vision_model(
            pixel_values=inputs["pixel_values"]
        )

        pooled_output = vision_outputs.pooler_output

        # Project into the shared CLIP embedding space.
        image_features = self.model.visual_projection(
            pooled_output
        )

        image_features = F.normalize(
            image_features,
            p=2,
            dim=-1,
        )

        return image_features

    # ---------------------------------------------------------
    # SINGLE IMAGE SCORE
    # ---------------------------------------------------------

    @torch.no_grad()
    def score_image(
        self,
        article_text: str,
        image_path: str | Path,
    ) -> float:
        """
        Calculate semantic similarity between
        article text and image.
        """

        text_embedding = self.encode_text(
            article_text
        )

        image_embedding = self.encode_image(
            image_path
        )

        similarity = F.cosine_similarity(
            text_embedding,
            image_embedding,
            dim=-1,
        )

        return float(
            similarity.item()
        )

    # ---------------------------------------------------------
    # BATCH IMAGE SCORING
    # ---------------------------------------------------------

    @torch.no_grad()
    def score_images(
        self,
        article_text: str,
        image_paths: list[str | Path],
    ) -> list[ImageRelevanceResult]:
        """
        Score multiple images against one article.

        Text embedding is calculated only once.
        """

        if not article_text or not article_text.strip():
            raise ValueError(
                "Article text cannot be empty."
            )

        if not image_paths:
            return []

        # -----------------------------------------------------
        # TEXT EMBEDDING
        # -----------------------------------------------------

        text_embedding = self.encode_text(
            article_text
        )

        results = []

        # -----------------------------------------------------
        # IMAGE EMBEDDINGS
        # -----------------------------------------------------

        for image_path in image_paths:

            image_path = Path(image_path)

            try:

                image_embedding = (
                    self.encode_image(
                        image_path
                    )
                )

                similarity = (
                    F.cosine_similarity(
                        text_embedding,
                        image_embedding,
                        dim=-1,
                    )
                )

                score = float(
                    similarity.item()
                )

                results.append(
                    ImageRelevanceResult(
                        image_path=str(
                            image_path
                        ),
                        score=score,
                        is_relevant=(
                            score >= self.threshold
                        ),
                    )
                )

            except Exception as e:

                print(
                    f"Failed to score image: "
                    f"{image_path}"
                )

                print(
                    f"Error: {e}"
                )

        # -----------------------------------------------------
        # SORT
        # -----------------------------------------------------

        results.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        # -----------------------------------------------------
        # RANK
        # -----------------------------------------------------

        for rank, result in enumerate(
            results,
            start=1,
        ):
            result.rank = rank

        return results

    # ---------------------------------------------------------
    # ARTICLE
    # ---------------------------------------------------------

    def score_article_images(
        self,
        article: dict,
        image_paths: list[str | Path],
    ) -> list[ImageRelevanceResult]:
        """
        Score images against an article dictionary.
        """

        title = article.get(
            "title",
            "",
        )

        content = article.get(
            "content",
            "",
        )

        # Keep the title highly visible to CLIP.
        article_text = (
            f"News article: {title}\n\n"
            f"{content}"
        )

        return self.score_images(
            article_text=article_text,
            image_paths=image_paths,
        )

    # ---------------------------------------------------------
    # BEST IMAGE
    # ---------------------------------------------------------

    def get_best_image(
        self,
        results: list[ImageRelevanceResult],
    ) -> ImageRelevanceResult | None:
        """
        Return the highest-scoring relevant image.

        Returns None if no image passes the threshold.
        """

        if not results:
            return None

        for result in results:

            if result.is_relevant:
                return result

        return None


# -------------------------------------------------------------
# TEST
# -------------------------------------------------------------

if __name__ == "__main__":

    article = {
        "id": 29,

        "title": (
            "Assam Rifles seize heroin worth Rs 5.07 cr "
            "in Mizoram, nab two Myanmar nationals"
        ),

        "content": (
            "Assam Rifles personnel seized heroin worth "
            "Rs 5.07 crore in Mizoram during an operation "
            "along the India-Myanmar border. Two Myanmar "
            "nationals were apprehended in connection "
            "with the drug trafficking operation."
        ),

        "category": (
            "Security & Strategic Affairs"
        ),
    }

    image_directory = (
        Path("data")
        / "images"
        / "article_29"
    )

    supported_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tiff",
    }

    image_paths = [
        path
        for path in sorted(
            image_directory.iterdir()
        )
        if (
            path.is_file()
            and path.suffix.lower()
            in supported_extensions
        )
    ]

    print(
        f"\nFound {len(image_paths)} images."
    )

    # ---------------------------------------------------------
    # MODEL
    # ---------------------------------------------------------

    relevance = ImageRelevance(
        threshold=0.20
    )

    # ---------------------------------------------------------
    # SCORE
    # ---------------------------------------------------------

    results = relevance.score_article_images(
        article=article,
        image_paths=image_paths,
    )

    # ---------------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------------

    print("\n" + "=" * 70)
    print("IMAGE RELEVANCE RESULTS")
    print("=" * 70)

    for result in results:

        print(
            f"\nRank       : {result.rank}"
        )

        print(
            f"Image      : {result.image_path}"
        )

        print(
            f"Score      : {result.score:.4f}"
        )

        print(
            f"Relevant   : "
            f"{result.is_relevant}"
        )

    # ---------------------------------------------------------
    # BEST IMAGE
    # ---------------------------------------------------------

    best_image = relevance.get_best_image(
        results
    )

    print("\n" + "=" * 70)
    print("BEST IMAGE")
    print("=" * 70)

    if best_image:

        print(
            f"Image : {best_image.image_path}"
        )

        print(
            f"Score : {best_image.score:.4f}"
        )

    else:

        print(
            "No image passed the relevance threshold."
        )