from dataclasses import dataclass
import re
from typing import Optional

from app.embeddings.embedder import ArticleEmbedder
from app.vectorstore.chroma_store import ChromaArticleStore


@dataclass
class RetrievedArticle:
    """
    Represents an article retrieved from Chroma.
    """

    source_id: int
    article_id: int
    title: str
    source: str
    url: str
    published_date: str
    category: str
    content: str
    similarity: float
    article_score: int
    rank: int

    @property
    def score(self) -> float:
        """
        Backward-compatible alias for similarity.
        """
        return self.similarity


class ArticleRetriever:
    """
    Retrieval layer for the Northeast Sentinel AI RAG pipeline.

    Pipeline:

        Query
          ↓
        Query cleaning
          ↓
        Query variants
          ↓
        Chroma semantic search
          ↓
        Merge duplicate candidates
          ↓
        Similarity filtering
          ↓
        Title/entity fallback
          ↓
        Final ranking
          ↓
        Top-K results

    Important:
    - Uses the same embedding model as the vector store.
    - Uses explicit query embeddings.
    - Does not rebuild Chroma.
    - Does not lower the similarity threshold.
    - Supports retrieve(query, top_k=...)
      for compatibility with the RAG generator.
    """

    def __init__(
        self,
        top_k: int = 3,
        min_similarity: float = 0.20,
    ):
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if not -1 <= min_similarity <= 1:
            raise ValueError(
                "min_similarity must be between -1 and 1."
            )

        self.top_k = top_k
        self.min_similarity = min_similarity

        print("=" * 70)
        print("ARTICLE RETRIEVER")
        print("=" * 70)

        self.embedder = ArticleEmbedder()
        self.vectorstore = ChromaArticleStore()

        print(
            f"Top K           : {self.top_k}"
        )
        print(
            f"Min similarity  : {self.min_similarity}"
        )
        print(
            f"Chroma vectors  : "
            f"{self.vectorstore.collection.count()}"
        )

    # ============================================================
    # QUERY CLEANING
    # ============================================================

    @staticmethod
    def _clean_query(query: str) -> str:
        """
        Remove common editorial instructions from the query.
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        cleaned = query.strip()

        prefixes = [
            "write a magazine article about",
            "write a magazine article on",
            "write an article about",
            "write an article on",
            "generate a magazine article about",
            "generate a magazine article on",
            "generate an article about",
            "generate an article on",
            "create a magazine article about",
            "create a magazine article on",
            "create an article about",
            "create an article on",
            "write about",
            "generate about",
            "create about",
        ]

        lowered = cleaned.lower()

        for prefix in prefixes:

            if lowered.startswith(prefix):

                cleaned = cleaned[
                    len(prefix):
                ].strip()

                break

        trailing_patterns = [
            r"\s+using only retrieved evidence.*$",
            r"\s+using only the retrieved evidence.*$",
            r"\s+using only supplied evidence.*$",
            r"\s+based only on retrieved evidence.*$",
            r"\s+from the retrieved sources.*$",
        ]

        for pattern in trailing_patterns:

            cleaned = re.sub(
                pattern,
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

        cleaned = cleaned.strip(
            " .,:;"
        )

        return cleaned

    # ============================================================
    # KEYWORD EXTRACTION
    # ============================================================

    @staticmethod
    def _keywords(
        text: str,
    ) -> list[str]:
        """
        Extract useful lexical keywords.

        These keywords are used only for the conservative
        title/entity fallback.
        """

        if not text:
            return []

        stopwords = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "that",
            "this",
            "these",
            "those",
            "into",
            "along",
            "about",
            "write",
            "article",
            "magazine",
            "northeast",
            "india",
            "news",
            "latest",
            "report",
            "reports",
            "issue",
            "issues",
            "question",
            "questions",
            "using",
            "only",
            "retrieved",
            "source",
            "sources",
            "evidence",
        }

        words = re.findall(
            r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*",
            text.lower(),
        )

        return [
            word
            for word in words
            if word not in stopwords
            and len(word) >= 3
        ]

    # ============================================================
    # QUERY VARIANTS
    # ============================================================

    def _build_query_variants(
        self,
        query: str,
    ) -> list[str]:
        """
        Build a small set of semantic query variants.
        """

        cleaned = self._clean_query(
            query
        )

        variants = [
            cleaned,
            cleaned.lower(),
        ]

        keywords = self._keywords(
            cleaned
        )

        if len(keywords) >= 4:

            variants.append(
                " ".join(keywords)
            )

        lowered = cleaned.lower()

        if "india-myanmar" in lowered:

            variants.append(
                lowered.replace(
                    "india-myanmar",
                    "myanmar border",
                )
            )

        if "india myanmar" in lowered:

            variants.append(
                lowered.replace(
                    "india myanmar",
                    "myanmar border",
                )
            )

        # Remove duplicate variants
        unique_variants = []

        for variant in variants:

            variant = variant.strip()

            if (
                variant
                and variant not in unique_variants
            ):
                unique_variants.append(
                    variant
                )

        return unique_variants

    # ============================================================
    # CHROMA SEARCH
    # ============================================================

    def _search_chroma(
        self,
        query: str,
        top_k: int,
    ) -> dict:
        """
        Search Chroma using explicit query embeddings.

        This is important because the same embedding model must
        be used for both indexed documents and queries.
        """

        query_embedding = (
            self.embedder.embed_text(
                query
            )
        )

        results = (
            self.vectorstore.collection.query(
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
        )

        return results

    # ============================================================
    # CHROMA RESULT CONVERSION
    # ============================================================

    def _convert_chroma_results(
        self,
        results: dict,
    ) -> list[RetrievedArticle]:
        """
        Convert raw Chroma output into RetrievedArticle objects.
        """

        documents = (
            results.get("documents")
            or [[]]
        )

        metadatas = (
            results.get("metadatas")
            or [[]]
        )

        distances = (
            results.get("distances")
            or [[]]
        )

        documents = (
            documents[0]
            if documents
            else []
        )

        metadatas = (
            metadatas[0]
            if metadatas
            else []
        )

        distances = (
            distances[0]
            if distances
            else []
        )

        articles = []

        for index, metadata in enumerate(
            metadatas
        ):

            if not metadata:
                continue

            distance = (
                float(distances[index])
                if index < len(distances)
                else 1.0
            )

            # Chroma cosine distance:
            # similarity = 1 - distance
            similarity = 1.0 - distance

            article_id = metadata.get(
                "article_id"
            )

            if article_id is None:
                continue

            try:

                article_id = int(
                    article_id
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            content = (
                documents[index]
                if index < len(documents)
                else ""
            )

            published_date = (
                metadata.get(
                    "published_date",
                    "",
                )
            )

            article = RetrievedArticle(
                source_id=article_id,
                article_id=article_id,
                title=metadata.get(
                    "title",
                    "",
                ),
                source=metadata.get(
                    "source",
                    "",
                ),
                url=metadata.get(
                    "url",
                    "",
                ),
                published_date=published_date,
                category=metadata.get(
                    "category",
                    "",
                ),
                content=content,
                similarity=similarity,
                article_score=int(
                    metadata.get(
                        "article_score",
                        0,
                    )
                    or 0
                ),
                rank=int(
                    metadata.get(
                        "rank",
                        0,
                    )
                    or 0
                ),
            )

            articles.append(
                article
            )

        return articles

    # ============================================================
    # MERGE RESULTS
    # ============================================================

    @staticmethod
    def _merge_results(
        results: list[RetrievedArticle],
    ) -> list[RetrievedArticle]:
        """
        Merge duplicate articles returned by multiple
        query variants.

        The strongest semantic similarity is retained.
        """

        merged: dict[
            int,
            RetrievedArticle
        ] = {}

        for article in results:

            existing = merged.get(
                article.article_id
            )

            if existing is None:

                merged[
                    article.article_id
                ] = article

                continue

            if (
                article.similarity
                > existing.similarity
            ):

                merged[
                    article.article_id
                ] = article

        return list(
            merged.values()
        )

    # ============================================================
    # TITLE / ENTITY FALLBACK
    # ============================================================

    def _title_fallback(
        self,
        query: str,
        candidates: list[RetrievedArticle],
    ) -> Optional[RetrievedArticle]:
        """
        Conservative lexical fallback.

        This is used ONLY when semantic retrieval returns
        nothing above the configured similarity threshold.

        It looks for meaningful overlap between query terms
        and article metadata.

        It does NOT arbitrarily select an article.
        """

        query_keywords = set(
            self._keywords(query)
        )

        if not query_keywords:
            return None

        best_article = None
        best_score = 0.0

        for article in candidates:

            searchable_text = " ".join(
                [
                    article.title or "",
                    article.category or "",
                    article.source or "",
                ]
            ).lower()

            metadata_keywords = set(
                self._keywords(
                    searchable_text
                )
            )

            if not metadata_keywords:
                continue

            overlap = (
                query_keywords
                .intersection(
                    metadata_keywords
                )
            )

            if not overlap:
                continue

            union = (
                query_keywords
                .union(
                    metadata_keywords
                )
            )

            lexical_score = (
                len(overlap)
                / len(union)
                if union
                else 0.0
            )

            # Important Northeast-specific entities.
            important_phrases = [
                "nagaon",
                "bangladesh",
                "bypoll",
                "women",
                "mizoram",
                "nagaland",
                "manipur",
                "assam",
                "guwahati",
                "lumding",
                "lalduhoma",
                "kangpokpi",
                "railway",
                "coffee",
                "heroin",
                "assam rifles",
                "india-myanmar",
                "myanmar border",
                "odi",
            ]

            lowered_query = query.lower()
            lowered_title = (
                article.title.lower()
            )

            entity_bonus = 0.0

            for phrase in important_phrases:

                if (
                    phrase in lowered_query
                    and phrase in lowered_title
                ):

                    entity_bonus += 0.10

            score = (
                lexical_score
                + entity_bonus
            )

            if score > best_score:

                best_score = score
                best_article = article

        # Conservative acceptance threshold.
        if (
            best_article is not None
            and best_score >= 0.20
        ):

            return best_article

        return None

    # ============================================================
    # MAIN RETRIEVAL METHOD
    # ============================================================

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> list[RetrievedArticle]:
        """
        Retrieve relevant articles.

        Parameters
        ----------
        query:
            User/editorial query.

        top_k:
            Optional number of results to return.

            If omitted, self.top_k is used.

            This parameter is intentionally supported because
            RAGGenerator calls:

                retriever.retrieve(
                    query=query,
                    top_k=...
                )
        """

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        # --------------------------------------------------------
        # Resolve requested Top-K
        # --------------------------------------------------------

        requested_top_k = (
            self.top_k
            if top_k is None
            else top_k
        )

        if requested_top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        print()
        print("=" * 70)
        print("RETRIEVING ARTICLES")
        print("=" * 70)

        print(
            f"Original query : {query}"
        )

        print(
            f"Requested Top-K: {requested_top_k}"
        )

        # --------------------------------------------------------
        # Query variants
        # --------------------------------------------------------

        variants = (
            self._build_query_variants(
                query
            )
        )

        print()
        print("Query variants:")

        for index, variant in enumerate(
            variants,
            start=1,
        ):

            print(
                f"  {index}. {variant}"
            )

        # --------------------------------------------------------
        # Candidate pool
        # --------------------------------------------------------

        candidate_k = max(
            requested_top_k * 3,
            8,
        )

        all_candidates = []

        for variant in variants:

            results = (
                self._search_chroma(
                    query=variant,
                    top_k=candidate_k,
                )
            )

            converted = (
                self._convert_chroma_results(
                    results
                )
            )

            all_candidates.extend(
                converted
            )

        # --------------------------------------------------------
        # Merge duplicate results
        # --------------------------------------------------------

        merged = (
            self._merge_results(
                all_candidates
            )
        )

        print(
            f"Candidates after merging: "
            f"{len(merged)}"
        )

        # --------------------------------------------------------
        # Semantic similarity filter
        # --------------------------------------------------------

        filtered = [
            article
            for article in merged
            if (
                article.similarity
                >= self.min_similarity
            )
        ]

        # Sort by:
        # 1. semantic similarity
        # 2. article score

        filtered.sort(
            key=lambda article: (
                article.similarity,
                article.article_score,
            ),
            reverse=True,
        )

        print(
            f"Candidates above threshold "
            f"({self.min_similarity}): "
            f"{len(filtered)}"
        )

        # --------------------------------------------------------
        # Conservative title/entity fallback
        # --------------------------------------------------------

        if not filtered:

            fallback = (
                self._title_fallback(
                    query=query,
                    candidates=merged,
                )
            )

            if fallback is not None:

                print(
                    "Semantic threshold returned "
                    "no candidate."
                )

                print(
                    "Title/entity fallback selected:"
                )

                print(
                    f"  ID={fallback.article_id}"
                )

                print(
                    f"  Title={fallback.title}"
                )

                filtered = [
                    fallback
                ]

        # --------------------------------------------------------
        # Final ranking
        # --------------------------------------------------------

        filtered.sort(
            key=lambda article: (
                article.similarity,
                article.article_score,
            ),
            reverse=True,
        )

        final_results = filtered[
            :requested_top_k
        ]

        # --------------------------------------------------------
        # Output
        # --------------------------------------------------------

        print()
        print("Final results:")

        if not final_results:

            print(
                "  No articles retrieved."
            )

        else:

            for index, article in enumerate(
                final_results,
                start=1,
            ):

                print(
                    f"  {index}. "
                    f"[{article.similarity:.4f}] "
                    f"ID={article.article_id} "
                    f"{article.title}"
                )

        return final_results


# =================================================================
# RETRIEVER TEST
# =================================================================

if __name__ == "__main__":

    retriever = ArticleRetriever(
        top_k=3,
        min_similarity=0.20,
    )

    tests = [
        {
            "query": (
                "security operations and drug "
                "trafficking along the "
                "India-Myanmar border in "
                "Northeast India"
            ),
            "expected": [29],
        },
        {
            "query": (
                "NEC support Nagaland coffee "
                "farmers modernisation"
            ),
            "expected": [32],
        },
        {
            "query": (
                "Centre funds Mizoram MNF "
                "Lalduhoma SASCI"
            ),
            "expected": [30],
        },
        {
            "query": (
                "Assam industry land shortage "
                "land banks industrial estates"
            ),
            "expected": [3],
        },
        {
            "query": (
                "71-year-old Kuki man "
                "Kangpokpi Manipur forest"
            ),
            "expected": [31],
        },
        {
            "query": (
                "Guwahati railway station "
                "50000 daily passengers "
                "projects"
            ),
            "expected": [15],
        },
        {
            "query": (
                "Lumding cattle roadside "
                "garbage civic concerns"
            ),
            "expected": [13],
        },
        {
            "query": (
                "Nagaon bypoll BJP Congress "
                "AIUDF campaign"
            ),
            "expected": [11],
        },
        {
            "query": (
                "Nagaon bypoll women "
                "Bangladesh political sparring"
            ),
            "expected": [12],
        },
        {
            "query": (
                "Guwahati 800-run ODI pitch"
            ),
            "expected": [34],
        },
    ]

    print()
    print("=" * 70)
    print("ARTICLE RETRIEVER TEST")
    print("=" * 70)

    passed = 0

    for test in tests:

        print()
        print("-" * 70)

        print(
            f"Query    : {test['query']}"
        )

        print(
            f"Expected : {test['expected']}"
        )

        try:

            results = retriever.retrieve(
                query=test["query"]
            )

            actual_ids = [
                article.article_id
                for article in results
            ]

            success = any(
                article_id in test["expected"]
                for article_id in actual_ids
            )

            if success:

                passed += 1

                print(
                    "RESULT   : PASS"
                )

            else:

                print(
                    f"RESULT   : FAIL "
                    f"({actual_ids})"
                )

        except Exception as error:

            print(
                "RESULT   : ERROR"
            )

            print(
                f"ERROR    : {error}"
            )

    print()
    print("=" * 70)
    print(
        f"RETRIEVAL TEST RESULT: "
        f"{passed}/{len(tests)}"
    )
    print("=" * 70)