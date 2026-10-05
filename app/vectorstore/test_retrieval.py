import chromadb

from app.config.settings import settings
from app.vectorstore.chroma_store import ChromaArticleStore

COLLECTION_NAME = "northeast_articles"


def display_results(query, results):

    print("\n" + "=" * 80)
    print(f"QUERY: {query}")
    print("=" * 80)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for index, (document, metadata, distance) in enumerate(
        zip(documents, metadatas, distances),
        start=1,
    ):

        similarity = 1 - distance

        print(f"\nResult {index}")
        print("-" * 80)
        print(f"Similarity : {similarity:.4f}")
        print(f"Article ID : {metadata.get('article_id')}")
        print(f"Title      : {metadata.get('title')}")
        print(f"Category   : {metadata.get('category')}")
        print(f"Source     : {metadata.get('source')}")
        print(f"Rank       : {metadata.get('rank')}")
        print(f"Score      : {metadata.get('article_score')}")
        print(f"URL        : {metadata.get('url')}")

        preview = document[:300].replace("\n", " ")
        print(f"Preview    : {preview}...")


def main():

    print("=" * 80)
    print("CHROMA SEMANTIC RETRIEVAL TEST")
    print("=" * 80)

    store = ChromaArticleStore()

    print(
        f"\nCollection : {store.collection.name}"
    )

    print(
        f"Vectors    : {store.collection.count()}"
    )

    queries = [
        "Assam Rifles operations and drug trafficking along the Myanmar border",

        "development projects and economic growth in Northeast India",

        "political developments and elections in Assam",

        "infrastructure development in Guwahati",

        "Nagaland coffee farmers and agricultural development",
    ]

    for query in queries:

        results = store.search(
            query=query,
            top_k=3,
        )

        display_results(
            query=query,
            results=results,
        )

    print("\n" + "=" * 80)
    print("RETRIEVAL TEST COMPLETE")
    print("=" * 80)

    print("\nChroma database was NOT modified.")


if __name__ == "__main__":
    main()  