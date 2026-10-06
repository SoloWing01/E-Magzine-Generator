import chromadb

from app.config.settings import settings
from app.database.database import SessionLocal
from app.database.models import Article
from app.embeddings.embedder import ArticleEmbedder


COLLECTION_NAME = "northeast_articles"


class ChromaArticleStore:
    """
    Phase 9 — Chroma Vector Store

    Responsibilities:

    1. Load the final relevant articles from SQLite.
    2. Build documents for vector indexing.
    3. Generate embeddings using Sentence Transformers.
    4. Store embeddings in ChromaDB.
    5. Store article metadata for RAG citations.
    6. Provide semantic search.

    Embedding model:

        sentence-transformers/all-MiniLM-L6-v2

    Expected embedding dimension:

        384
    """

    # ==========================================================
    # INITIALIZATION
    # ==========================================================

    def __init__(self):

        print("=" * 70)
        print("CHROMA VECTOR STORE")
        print("=" * 70)

        print(
            f"Chroma path     : "
            f"{settings.CHROMA_PATH}"
        )

        print(
            f"Collection      : "
            f"{COLLECTION_NAME}"
        )

        # ------------------------------------------------------
        # Persistent Chroma client
        # ------------------------------------------------------

        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH
        )

        # ------------------------------------------------------
        # Load existing collection
        # ------------------------------------------------------

        self.collection = (
            self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": (
                        "Northeast India news articles "
                        "for RAG retrieval"
                    )
                },
            )
        )

        # ------------------------------------------------------
        # Load embedding model ONCE
        # ------------------------------------------------------

        self.embedder = ArticleEmbedder()

        print(
            f"Existing vectors: "
            f"{self.collection.count()}"
        )

    # ==========================================================
    # LOAD ARTICLES FROM SQLITE
    # ==========================================================

    def load_articles(self):
        """
        Load the final relevant article corpus from SQLite.

        The editorial gate used by the earlier phases is applied:

            category IS NOT NULL
            category != 'Not Relevant'

        Articles are ordered by article score.
        """

        db = SessionLocal()

        try:

            articles = (
                db.query(Article)
                .filter(
                    Article.category.isnot(None),
                    Article.category != "Not Relevant",
                )
                .order_by(
                    Article.article_score.desc()
                )
                .all()
            )

            return articles

        finally:

            db.close()

    # ==========================================================
    # BUILD DOCUMENT
    # ==========================================================

    @staticmethod
    def build_document(article):
        """
        Build the text that will be embedded and stored
        in Chroma.
        """

        return (
            f"Title: {article.title}\n\n"

            f"Source: {article.source}\n"

            f"Published: "
            f"{article.published_date}\n"

            f"Category: "
            f"{article.category}\n\n"

            f"Content:\n"
            f"{article.content}"
        )

    # ==========================================================
    # BUILD METADATA
    # ==========================================================

    @staticmethod
    def build_metadata(article):
        """
        Build metadata used by retrieval and citation.
        """

        return {
            "article_id": str(
                article.id
            ),

            "title": (
                article.title
                or ""
            ),

            "url": (
                article.url
                or ""
            ),

            "source": (
                article.source
                or ""
            ),

            "category": (
                article.category
                or ""
            ),

            "published_date": (
                article.published_date.isoformat()
                if article.published_date
                else ""
            ),

            "article_score": int(
                article.article_score or 0
            ),

            "rank": int(
                article.rank or 0
            ),

            "northeast_score": int(
                article.northeast_score or 0
            ),

            "security_score": int(
                article.security_score or 0
            ),
        }

    # ==========================================================
    # RESET COLLECTION
    # ==========================================================

    def reset_collection(self):
        """
        Delete the existing Chroma collection and create
        a completely fresh collection.

        This prevents vectors from previous runs from
        remaining in the RAG knowledge base.
        """

        print(
            "\nResetting Chroma collection..."
        )

        try:

            self.client.delete_collection(
                name=COLLECTION_NAME
            )

            print(
                "Old collection deleted."
            )

        except Exception as exc:

            print(
                "No existing collection "
                "needed to be deleted."
            )

            print(
                f"Details: {exc}"
            )

        # ------------------------------------------------------
        # Create a fresh collection
        # ------------------------------------------------------

        self.collection = (
            self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={
                    "description": (
                        "Northeast India news articles "
                        "for RAG retrieval"
                    )
                },
            )
        )

        print(
            "Fresh Chroma collection created."
        )

        print(
            f"Current vectors: "
            f"{self.collection.count()}"
        )

    # ==========================================================
    # ADD ARTICLES
    # ==========================================================

    def add_articles(
        self,
        articles,
        batch_size: int = 16,
    ):
        """
        Generate embeddings and store articles in Chroma.
        """

        if not articles:

            print(
                "No articles found."
            )

            return

        print(
            f"\nArticles to index: "
            f"{len(articles)}"
        )

        # ======================================================
        # PREPARE DOCUMENTS
        # ======================================================

        documents = [
            self.build_document(article)
            for article in articles
        ]

        # ======================================================
        # PREPARE IDS
        # ======================================================

        ids = [
            f"article_{article.id}"
            for article in articles
        ]

        # ======================================================
        # PREPARE METADATA
        # ======================================================

        metadatas = [
            self.build_metadata(article)
            for article in articles
        ]

        # ======================================================
        # GENERATE EMBEDDINGS
        # ======================================================

        print(
            "\nGenerating embeddings..."
        )

        # IMPORTANT:
        #
        # Do NOT create another ArticleEmbedder here.
        #
        # self.embedder was already created in __init__().
        #

        embeddings = (
            self.embedder.embed_texts(
                documents,
                batch_size=batch_size,
            )
        )

        # ======================================================
        # VALIDATE EMBEDDINGS
        # ======================================================

        if not embeddings:

            raise RuntimeError(
                "Embedding generation returned "
                "no vectors."
            )

        print(
            f"\nGenerated "
            f"{len(embeddings)} embeddings."
        )

        embedding_dimension = len(
            embeddings[0]
        )

        print(
            f"Embedding dimension: "
            f"{embedding_dimension}"
        )

        # ------------------------------------------------------
        # Check expected dimension
        # ------------------------------------------------------

        expected_dimension = (
            self.embedder.model
            .get_embedding_dimension()
        )

        if (
            embedding_dimension
            != expected_dimension
        ):

            raise ValueError(
                "Embedding dimension mismatch. "
                f"Expected {expected_dimension}, "
                f"got {embedding_dimension}."
            )

        # ------------------------------------------------------
        # Check number of embeddings
        # ------------------------------------------------------

        if len(embeddings) != len(
            articles
        ):

            raise ValueError(
                "Number of embeddings does not "
                "match number of articles."
            )

        # ======================================================
        # STORE VECTORS
        # ======================================================

        print(
            "\nStoring vectors in Chroma..."
        )

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        print(
            f"Chroma collection now contains "
            f"{self.collection.count()} vectors."
        )

    # ==========================================================
    # COLLECTION INFORMATION
    # ==========================================================

    def get_collection_info(self):
        """
        Return basic collection information.
        """

        return {
            "name": (
                self.collection.name
            ),

            "count": (
                self.collection.count()
            ),
        }

    # ==========================================================
    # SEMANTIC SEARCH
    # ==========================================================

    def search(
        self,
        query: str,
        top_k: int = 3,
    ):
        """
        Search Chroma using the same embedding model
        used for indexing.
        """

        if not query or not query.strip():

            raise ValueError(
                "Query cannot be empty."
            )

        # ------------------------------------------------------
        # Generate query embedding
        # ------------------------------------------------------

        query_embedding = (
            self.embedder.embed_text(
                query
            )
        )

        # ------------------------------------------------------
        # Query Chroma
        # ------------------------------------------------------

        results = self.collection.query(
            query_embeddings=[
                query_embedding
            ],

            n_results=top_k,

            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        return results

    # ==========================================================
    # TEST SEARCH
    # ==========================================================

    def test_search(
        self,
        query: str,
        top_k: int = 3,
    ):
        """
        Run a semantic search and print readable results.

        This is useful for verifying Phase 9 before moving
        to the RAG generation phase.
        """

        print()
        print("=" * 70)
        print("CHROMA SEMANTIC SEARCH TEST")
        print("=" * 70)

        print(
            f"\nQuery: {query}"
        )

        results = self.search(
            query=query,
            top_k=top_k,
        )

        documents = (
            results.get(
                "documents",
                [[]]
            )[0]
        )

        metadatas = (
            results.get(
                "metadatas",
                [[]]
            )[0]
        )

        distances = (
            results.get(
                "distances",
                [[]]
            )[0]
        )

        if not documents:

            print(
                "\nNo results found."
            )

            return

        for index, document in enumerate(
            documents,
            start=1,
        ):

            metadata = (
                metadatas[index - 1]
                if index - 1 < len(
                    metadatas
                )
                else {}
            )

            distance = (
                distances[index - 1]
                if index - 1 < len(
                    distances
                )
                else None
            )

            print()

            print(
                f"[Result {index}]"
            )

            print(
                f"Article ID : "
                f"{metadata.get('article_id')}"
            )

            print(
                f"Title      : "
                f"{metadata.get('title')}"
            )

            print(
                f"Category   : "
                f"{metadata.get('category')}"
            )

            print(
                f"Source     : "
                f"{metadata.get('source')}"
            )

            print(
                f"Distance   : "
                f"{distance}"
            )

            print(
                "-" * 70
            )

            # Print only the first part of the document
            # for readability.

            preview = document[:500]

            print(
                preview
            )

            if len(document) > 500:

                print(
                    "..."
                )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print()

    print("=" * 70)
    print("PHASE 9 - CHROMA VECTOR INDEXING")
    print("=" * 70)

    # ==========================================================
    # STEP 1 — CREATE VECTOR STORE
    # ==========================================================

    store = ChromaArticleStore()

    # ==========================================================
    # STEP 2 — LOAD ARTICLES
    # ==========================================================

    articles = store.load_articles()

    print(
        f"\nRelevant articles loaded from SQLite: "
        f"{len(articles)}"
    )

    # ==========================================================
    # STEP 3 — VALIDATE ARTICLE CORPUS
    # ==========================================================

    if not articles:

        print(
            "\nNo relevant articles available."
        )

        return

    # ----------------------------------------------------------
    # Display selected articles
    # ----------------------------------------------------------

    print()

    print(
        "Articles selected for vector indexing:"
    )

    print(
        "-" * 70
    )

    for index, article in enumerate(
        articles,
        start=1,
    ):

        print(
            f"{index:02d}. "
            f"ID {article.id} | "
            f"Score {article.article_score} | "
            f"{article.category} | "
            f"{article.title}"
        )

    # ==========================================================
    # STEP 4 — RESET CHROMA
    # ==========================================================

    store.reset_collection()

    # ==========================================================
    # STEP 5 — GENERATE AND STORE EMBEDDINGS
    # ==========================================================

    store.add_articles(
        articles,
        batch_size=16,
    )

    # ==========================================================
    # STEP 6 — FINAL COLLECTION INFO
    # ==========================================================

    print()

    print("=" * 70)
    print("CHROMA INDEXING COMPLETE")
    print("=" * 70)

    info = (
        store.get_collection_info()
    )

    print(
        f"Collection : "
        f"{info['name']}"
    )

    print(
        f"Vectors    : "
        f"{info['count']}"
    )

    # ==========================================================
    # STEP 7 — VECTOR COUNT VALIDATION
    # ==========================================================

    if (
        info["count"]
        != len(articles)
    ):

        raise RuntimeError(
            "Chroma vector count does not "
            "match the number of indexed "
            "articles."
        )

    print(
        "\nVector count validation: PASSED"
    )

    print(
        "SQLite database was NOT modified."
    )

    print(
        "\nPhase 9 completed successfully."
    )


# ==============================================================
# ENTRY POINT
# ==============================================================

if __name__ == "__main__":
    main()