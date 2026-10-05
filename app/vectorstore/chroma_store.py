import chromadb

from app.config.settings import settings
from app.database.database import SessionLocal
from app.database.models import Article
from app.embeddings.embedder import ArticleEmbedder


COLLECTION_NAME = "northeast_articles"


class ChromaArticleStore:
    

    def __init__(self):

        print("=" * 70)
        print("CHROMA VECTOR STORE")
        print("=" * 70)

        print(f"Chroma path     : {settings.CHROMA_PATH}")
        print(f"Collection      : {COLLECTION_NAME}")

        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH
        )

        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={
                "description": (
                    "Northeast India news articles "
                    "for RAG retrieval"
                )
            },
        )

        self.embedder = ArticleEmbedder()

        print(
            f"Existing vectors: "
            f"{self.collection.count()}"
        )


    def load_articles(self):
        """Load relevant articles from SQLite."""

        db = SessionLocal()

        try:
            articles = (
                db.query(Article)
                .filter(Article.relevance_score > 0)
                .order_by(Article.rank.asc())
                .all()
            )

            return articles

        finally:
            db.close()

    @staticmethod
    def build_document(article):
        """Create the text that will be stored in Chroma."""

        return (
            f"Title: {article.title}\n\n"
            f"Source: {article.source}\n"
            f"Published: {article.published_date}\n"
            f"Category: {article.category}\n\n"
            f"Content:\n{article.content}"
        )

    @staticmethod
    def build_metadata(article):
        """Create metadata for filtering and citation."""

        return {
            "article_id": str(article.id),
            "title": article.title,
            "url": article.url,
            "source": article.source,
            "category": article.category or "",
            "published_date": (
                article.published_date.isoformat()
                if article.published_date
                else ""
            ),
            "article_score": int(article.article_score or 0),
            "rank": int(article.rank or 0),
            "northeast_score": int(
                article.northeast_score or 0
            ),
            "security_score": int(
                article.security_score or 0
            ),
        }
    

    
    def add_articles(self, articles):
        """Generate embeddings and store articles in Chroma."""

        if not articles:
            print("No articles found.")
            return

        print(
            f"\nArticles to index: {len(articles)}"
        )

        # -----------------------------------------------------
        # Prepare documents
        # -----------------------------------------------------

        documents = [
            self.build_document(article)
            for article in articles
        ]

        ids = [
            f"article_{article.id}"
            for article in articles
        ]

        metadatas = [
            self.build_metadata(article)
            for article in articles
        ]

        # -----------------------------------------------------
        # Generate embeddings
        # -----------------------------------------------------

        print("\nGenerating embeddings...")

        embedder = ArticleEmbedder()

        embeddings = self.embedder.embed_texts(documents,batch_size=16,)

        print(
            f"Generated {len(embeddings)} embeddings."
        )

        print(
            f"Embedding dimension: "
            f"{len(embeddings[0])}"
        )

        # -----------------------------------------------------
        # Store in Chroma
        # -----------------------------------------------------

        print("\nStoring vectors in Chroma...")

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

    def get_collection_info(self):
        """Return basic collection information."""

        return {
            "name": self.collection.name,
            "count": self.collection.count(),
        }
    
    def search(self, query: str, top_k: int = 3):
        """Search Chroma using the same embedding model used for indexing."""

        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")

        query_embedding = self.embedder.embed_text(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        return results
    


def main():

    store = ChromaArticleStore()

    articles = store.load_articles()

    print(
        f"\nRelevant articles loaded from SQLite: "
        f"{len(articles)}"
    )

    if not articles:
        print("No relevant articles available.")
        return

    store.add_articles(articles)

    print("\n" + "=" * 70)
    print("CHROMA INDEXING COMPLETE")
    print("=" * 70)

    info = store.get_collection_info()

    print(f"Collection : {info['name']}")
    print(f"Vectors    : {info['count']}")

    print("\nSQLite database was NOT modified.")


if __name__ == "__main__":
    main()