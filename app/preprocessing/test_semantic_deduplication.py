from itertools import combinations

from sklearn.metrics.pairwise import cosine_similarity

from app.database.database import SessionLocal
from app.database.models import Article
from app.embeddings.embedder import ArticleEmbedder


# This is only a diagnostic threshold.
# We will decide the final duplicate threshold after seeing the results.
SIMILARITY_THRESHOLD = 0.70


def load_relevant_articles():
    """Load articles that passed the Northeast relevance/classification stage."""

    db = SessionLocal()

    try:
        articles = (
            db.query(Article)
            .filter(Article.relevance_score > 0)
            .order_by(Article.article_score.desc())
            .all()
        )

        return articles

    finally:
        db.close()


def build_embedding_text(article):
    """Combine article title and content for semantic embedding."""

    return f"""
Title: {article.title}

Content:
{article.content}
""".strip()


def calculate_similarity(articles, embeddings):
    """Calculate pairwise cosine similarity between article embeddings."""

    similarity_matrix = cosine_similarity(embeddings)

    results = []

    for i, j in combinations(range(len(articles)), 2):

        similarity = float(similarity_matrix[i][j])

        results.append(
            {
                "article_1": articles[i],
                "article_2": articles[j],
                "similarity": similarity,
            }
        )

    results.sort(
        key=lambda x: x["similarity"],
        reverse=True,
    )

    return results


def print_results(results):
    """Display the most semantically similar article pairs."""

    print("\n" + "=" * 80)
    print("SEMANTIC DEDUPLICATION RESULTS")
    print("=" * 80)

    print(f"\nTotal article pairs checked: {len(results)}")

    print("\nTop 15 most similar article pairs:")
    print("-" * 80)

    for index, result in enumerate(results[:15], start=1):

        article_1 = result["article_1"]
        article_2 = result["article_2"]
        similarity = result["similarity"]

        print(f"\nPair {index}")
        print(f"Similarity : {similarity:.4f}")

        print(
            f"Article 1  : "
            f"[ID {article_1.id}] {article_1.title}"
        )

        print(
            f"Article 2  : "
            f"[ID {article_2.id}] {article_2.title}"
        )

    suspicious = [
        result
        for result in results
        if result["similarity"] >= SIMILARITY_THRESHOLD
    ]

    print("\n" + "=" * 80)
    print(
        f"PAIRS ABOVE {SIMILARITY_THRESHOLD:.2f} SIMILARITY"
    )
    print("=" * 80)

    if not suspicious:
        print("\nNo potentially duplicate articles found.")

    else:
        print(
            f"\nPotentially similar pairs: "
            f"{len(suspicious)}"
        )

        for index, result in enumerate(suspicious, start=1):

            article_1 = result["article_1"]
            article_2 = result["article_2"]

            print(f"\nPotential Duplicate Pair {index}")
            print(f"Similarity : {result['similarity']:.4f}")

            print(
                f"Article 1  : "
                f"[ID {article_1.id}] {article_1.title}"
            )

            print(
                f"Article 2  : "
                f"[ID {article_2.id}] {article_2.title}"
            )

    print("\n" + "=" * 80)


def main():

    print("=" * 80)
    print("SEMANTIC DEDUPLICATION TEST")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. Load relevant articles
    # ---------------------------------------------------------

    articles = load_relevant_articles()

    print(f"\nRelevant articles loaded: {len(articles)}")

    if len(articles) < 2:
        print("Not enough articles for semantic comparison.")
        return

    # ---------------------------------------------------------
    # 2. Prepare text
    # ---------------------------------------------------------

    texts = [
        build_embedding_text(article)
        for article in articles
    ]

    print("Embedding article title + content...")

    # ---------------------------------------------------------
    # 3. Generate embeddings
    # ---------------------------------------------------------

    embedder = ArticleEmbedder()

    embeddings = embedder.embed_texts(
        texts,
        batch_size=16,
    )

    print(
        f"\nGenerated embeddings: {len(embeddings)}"
    )

    print(
        f"Embedding dimension: {len(embeddings[0])}"
    )

    # ---------------------------------------------------------
    # 4. Calculate semantic similarity
    # ---------------------------------------------------------

    print("\nCalculating pairwise cosine similarity...")

    results = calculate_similarity(
        articles,
        embeddings,
    )

    # ---------------------------------------------------------
    # 5. Display results
    # ---------------------------------------------------------

    print_results(results)

    print("\nDatabase was NOT modified.")


if __name__ == "__main__":
    main()