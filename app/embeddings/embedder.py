from sentence_transformers import SentenceTransformer
import torch


class ArticleEmbedder:
    """
    Generates semantic embeddings for news articles
    using Sentence Transformers.
    """

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self):
        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        print("=" * 70)
        print("ARTICLE EMBEDDER")
        print("=" * 70)

        print(f"Model  : {self.MODEL_NAME}")
        print(f"Device : {self.device}")

        if self.device == "cuda":
            print(
                f"GPU    : "
                f"{torch.cuda.get_device_name(0)}"
            )

            print(
                f"CUDA   : "
                f"{torch.version.cuda}"
            )

        self.model = SentenceTransformer(
            self.MODEL_NAME,
            device=self.device,
        )

        print(
            f"Embedding dimension: "
            f"{self.model.get_embedding_dimension()}"
        )

        print("Model loaded successfully.")

    # ==========================================================
    # Single text embedding
    # ==========================================================

    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate an embedding for a single text.
        """

        if not text or not text.strip():
            raise ValueError(
                "Cannot generate embedding for empty text."
            )

        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    # ==========================================================
    # Batch embedding
    # ==========================================================

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = 16,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Batch processing allows Sentence Transformers to
        efficiently use the GPU.
        """

        if not texts:
            return []

        # ------------------------------------------------------
        # Validate input
        # ------------------------------------------------------

        if any(
            not text or not text.strip()
            for text in texts
        ):
            raise ValueError(
                "Text list contains an empty value."
            )

        print(
            f"\nGenerating embeddings for "
            f"{len(texts)} texts..."
        )

        print(
            f"Batch size: {batch_size}"
        )

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=True,
        )

        return embeddings.tolist()

    # ==========================================================
    # Article embedding
    # ==========================================================

    def embed_article(
        self,
        title: str,
        content: str,
    ) -> list[float]:
        """
        Generate an embedding using both title and content.

        The title is included because it contains important
        information about the article's main event.
        """

        combined_text = (
            f"Title: {title}\n\n"
            f"Content: {content}"
        )

        return self.embed_text(
            combined_text
        )


# ==============================================================
# TEST
# ==============================================================

if __name__ == "__main__":

    embedder = ArticleEmbedder()

    test_text = """
    Assam Rifles seized heroin worth Rs 5.07 crore
    in Mizoram and arrested two Myanmar nationals.
    """

    embedding = embedder.embed_text(
        test_text
    )

    print("\nEmbedding test successful.")

    print(
        f"Vector length: "
        f"{len(embedding)}"
    )

    print(
        f"First 5 values: "
        f"{embedding[:5]}"
    )