
"""
RAG Retrieval Quality Test

Tests:
1. Retrieval accuracy
2. Recall@1
3. Recall@3
4. Recall@5
5. Mean Reciprocal Rank (MRR)
6. Average similarity
7. Negative-query rejection
8. Retrieval diagnostics

Run:
    python -m app.rag.rag_quality_test
"""

from dataclasses import dataclass
from typing import Optional

from app.rag.retriever import ArticleRetriever


# ============================================================
# TEST CASES
# ============================================================

@dataclass
class RAGTestCase:
    name: str
    query: str
    expected_article_ids: list[int]
    negative: bool = False


TEST_CASES = [
    RAGTestCase(
        name="Security / Drug Trafficking",
        query=(
            "security operations and drug trafficking along the "
            "India-Myanmar border in Northeast India"
        ),
        expected_article_ids=[29],
    ),

    RAGTestCase(
        name="Nagaland Coffee",
        query=(
            "Nagaland coffee farmers and government support for "
            "coffee production modernization"
        ),
        expected_article_ids=[32],
    ),

    RAGTestCase(
        name="Guwahati Railway Infrastructure",
        query=(
            "Guwahati railway station infrastructure development "
            "and increasing passenger traffic"
        ),
        expected_article_ids=[15],
    ),

    RAGTestCase(
        name="Assam Industrial Development",
        query=(
            "Assam industrial development land shortage land banks "
            "and industrial estates"
        ),
        expected_article_ids=[3],
    ),

    RAGTestCase(
        name="Guwahati Cricket Pitch",
        query=(
            "Guwahati cricket ODI match pitch and 800 run score"
        ),
        expected_article_ids=[34],
    ),

    RAGTestCase(
        name="Manipur Kuki Incident",
        query=(
            "missing Kuki man found dead in Kangpokpi Manipur"
        ),
        expected_article_ids=[31],
    ),

    RAGTestCase(
        name="Mizoram Funding",
        query=(
            "Mizoram government Centre funds not released "
            "and MNF seeks explanation"
        ),
        expected_article_ids=[30],
    ),

    RAGTestCase(
        name="Nagaon Bypoll",
        query=(
            "Nagaon bypoll election BJP Congress AIUDF "
            "campaign and political competition"
        ),
        expected_article_ids=[11, 12],
    ),

    RAGTestCase(
        name="Lumding Civic Issues",
        query=(
            "Lumding Assam civic problems roadside garbage "
            "and roaming cattle"
        ),
        expected_article_ids=[13],
    ),

    RAGTestCase(
        name="Unrelated Query",
        query=(
            "latest smartphone processor benchmark comparison "
            "between mobile CPUs"
        ),
        expected_article_ids=[],
        negative=True,
    ),
]


# ============================================================
# CONFIGURATION
# ============================================================

TOP_K = 5

# A result must meet this similarity to count as retrieved.
# This should match the threshold used by ArticleRetriever.
MIN_SIMILARITY = 0.20


# ============================================================
# RESULT CONTAINER
# ============================================================

@dataclass
class TestResult:
    name: str
    query: str
    expected_ids: list[int]
    retrieved_ids: list[int]
    similarities: list[float]

    relevant: bool
    negative: bool

    rank: Optional[int]
    reciprocal_rank: float

    top_similarity: Optional[float]

    recall_at_1: float
    recall_at_3: float
    recall_at_5: float

    negative_pass: Optional[bool]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def extract_article_id(article) -> Optional[int]:
    """
    Extract article ID from different possible retriever formats.
    """

    if article is None:
        return None

    if isinstance(article, dict):
        value = article.get("article_id")

        if value is None:
            value = article.get("id")

        if value is not None:
            return int(value)

    if hasattr(article, "article_id"):
        return int(article.article_id)

    if hasattr(article, "id"):
        return int(article.id)

    return None


def extract_similarity(article) -> Optional[float]:
    """
    Extract similarity from different possible retriever formats.
    """

    if article is None:
        return None

    if isinstance(article, dict):
        value = article.get("similarity")

        if value is None:
            value = article.get("score")

        if value is not None:
            return float(value)

    if hasattr(article, "similarity"):
        return float(article.similarity)

    if hasattr(article, "score"):
        return float(article.score)

    return None


def get_retrieved_articles(retriever, query: str):
    """
    Retrieve candidates directly so that the test can inspect
    similarity scores and rank positions.
    """

    if hasattr(retriever, "retrieve_candidates"):
        return retriever.retrieve_candidates(
            query=query,
            top_k=TOP_K,
        )

    # Fallback for older retriever implementations.
    return retriever.retrieve(
        query=query,
    )


# ============================================================
# SINGLE TEST
# ============================================================

def run_test_case(
    retriever: ArticleRetriever,
    test_case: RAGTestCase,
) -> TestResult:

    results = get_retrieved_articles(
        retriever,
        test_case.query,
    )

    retrieved_ids = []
    similarities = []

    for result in results:

        article_id = extract_article_id(result)
        similarity = extract_similarity(result)

        if article_id is None:
            continue

        if similarity is None:
            similarity = 0.0

        retrieved_ids.append(article_id)
        similarities.append(similarity)

    expected_ids = test_case.expected_article_ids

    # --------------------------------------------------------
    # Negative query
    # --------------------------------------------------------

    if test_case.negative:

        accepted_ids = [
            article_id
            for article_id, similarity
            in zip(retrieved_ids, similarities)
            if similarity >= MIN_SIMILARITY
        ]

        negative_pass = len(accepted_ids) == 0

        return TestResult(
            name=test_case.name,
            query=test_case.query,
            expected_ids=expected_ids,
            retrieved_ids=retrieved_ids,
            similarities=similarities,
            relevant=False,
            negative=True,
            rank=None,
            reciprocal_rank=0.0,
            top_similarity=(
                similarities[0]
                if similarities
                else None
            ),
            recall_at_1=0.0,
            recall_at_3=0.0,
            recall_at_5=0.0,
            negative_pass=negative_pass,
        )

    # --------------------------------------------------------
    # Relevant query
    # --------------------------------------------------------

    rank = None

    for index, article_id in enumerate(
        retrieved_ids,
        start=1,
    ):
        if article_id in expected_ids:
            rank = index
            break

    reciprocal_rank = (
        1.0 / rank
        if rank is not None
        else 0.0
    )

    recall_at_1 = 0.0

    if any(
        article_id in expected_ids
        for article_id in retrieved_ids[:1]
    ):
        recall_at_1 = 1.0

    recall_at_3 = 0.0

    if any(
        article_id in expected_ids
        for article_id in retrieved_ids[:3]
    ):
        recall_at_3 = 1.0

    recall_at_5 = 0.0

    if any(
        article_id in expected_ids
        for article_id in retrieved_ids[:5]
    ):
        recall_at_5 = 1.0

    relevant = rank is not None

    return TestResult(
        name=test_case.name,
        query=test_case.query,
        expected_ids=expected_ids,
        retrieved_ids=retrieved_ids,
        similarities=similarities,
        relevant=relevant,
        negative=False,
        rank=rank,
        reciprocal_rank=reciprocal_rank,
        top_similarity=(
            similarities[0]
            if similarities
            else None
        ),
        recall_at_1=recall_at_1,
        recall_at_3=recall_at_3,
        recall_at_5=recall_at_5,
        negative_pass=None,
    )


# ============================================================
# PRINT INDIVIDUAL RESULT
# ============================================================

def print_test_result(result: TestResult, number: int):

    print()
    print("=" * 70)
    print(f"TEST {number}: {result.name}")
    print("=" * 70)

    print(f"Query       : {result.query}")

    print(
        f"Expected IDs: "
        f"{result.expected_ids if result.expected_ids else 'NONE'}"
    )

    print(
        f"Retrieved   : "
        f"{result.retrieved_ids if result.retrieved_ids else 'NONE'}"
    )

    if result.similarities:

        formatted_scores = [
            f"{score:.4f}"
            for score in result.similarities
        ]

        print(
            f"Similarities: "
            f"{formatted_scores}"
        )

    else:
        print("Similarities: NONE")

    if result.negative:

        print(
            f"Top similarity: "
            f"{result.top_similarity:.4f}"
            if result.top_similarity is not None
            else "Top similarity: NONE"
        )

        print(
            f"Negative test: "
            f"{'PASS' if result.negative_pass else 'FAIL'}"
        )

        return

    print(
        f"Correct rank: "
        f"{result.rank if result.rank is not None else 'NOT FOUND'}"
    )

    print(
        f"Reciprocal rank: "
        f"{result.reciprocal_rank:.4f}"
    )

    print(
        f"Recall@1: "
        f"{'PASS' if result.recall_at_1 else 'FAIL'}"
    )

    print(
        f"Recall@3: "
        f"{'PASS' if result.recall_at_3 else 'FAIL'}"
    )

    print(
        f"Recall@5: "
        f"{'PASS' if result.recall_at_5 else 'FAIL'}"
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(results: list[TestResult]):

    relevant_results = [
        result
        for result in results
        if not result.negative
    ]

    negative_results = [
        result
        for result in results
        if result.negative
    ]

    total_relevant = len(relevant_results)
    total_negative = len(negative_results)

    if total_relevant:

        recall_at_1 = (
            sum(
                result.recall_at_1
                for result in relevant_results
            )
            / total_relevant
        )

        recall_at_3 = (
            sum(
                result.recall_at_3
                for result in relevant_results
            )
            / total_relevant
        )

        recall_at_5 = (
            sum(
                result.recall_at_5
                for result in relevant_results
            )
            / total_relevant
        )

        mrr = (
            sum(
                result.reciprocal_rank
                for result in relevant_results
            )
            / total_relevant
        )

        similarities = [
            result.top_similarity
            for result in relevant_results
            if result.top_similarity is not None
        ]

        average_similarity = (
            sum(similarities) / len(similarities)
            if similarities
            else 0.0
        )

    else:

        recall_at_1 = 0.0
        recall_at_3 = 0.0
        recall_at_5 = 0.0
        mrr = 0.0
        average_similarity = 0.0

    negative_pass_count = sum(
        1
        for result in negative_results
        if result.negative_pass
    )

    negative_rejection_rate = (
        negative_pass_count / total_negative
        if total_negative
        else 0.0
    )

    relevant_pass_count = sum(
        1
        for result in relevant_results
        if result.relevant
    )

    print()
    print()
    print("=" * 70)
    print("RAG RETRIEVAL QUALITY REPORT")
    print("=" * 70)

    print()
    print("DATASET")
    print("-" * 70)

    print(
        f"Total test cases       : {len(results)}"
    )

    print(
        f"Relevant queries       : {total_relevant}"
    )

    print(
        f"Negative queries      : {total_negative}"
    )

    print()
    print("RETRIEVAL METRICS")
    print("-" * 70)

    print(
        f"Recall@1               : "
        f"{recall_at_1:.2%}"
    )

    print(
        f"Recall@3               : "
        f"{recall_at_3:.2%}"
    )

    print(
        f"Recall@5               : "
        f"{recall_at_5:.2%}"
    )

    print(
        f"MRR                    : "
        f"{mrr:.4f}"
    )

    print(
        f"Average top similarity : "
        f"{average_similarity:.4f}"
    )

    print()
    print("NEGATIVE QUERY TEST")
    print("-" * 70)

    print(
        f"Rejected correctly     : "
        f"{negative_pass_count}/{total_negative}"
    )

    print(
        f"Rejection rate         : "
        f"{negative_rejection_rate:.2%}"
    )

    print()
    print("OVERALL")
    print("-" * 70)

    print(
        f"Relevant queries found : "
        f"{relevant_pass_count}/{total_relevant}"
    )

    if total_relevant:

        if recall_at_3 >= 0.90:
            print("Recall@3 assessment     : EXCELLENT")

        elif recall_at_3 >= 0.75:
            print("Recall@3 assessment     : GOOD")

        elif recall_at_3 >= 0.50:
            print("Recall@3 assessment     : NEEDS IMPROVEMENT")

        else:
            print("Recall@3 assessment     : POOR")

    if total_negative:

        if negative_rejection_rate == 1.0:
            print(
                "Negative query handling : EXCELLENT"
            )

        elif negative_rejection_rate >= 0.50:
            print(
                "Negative query handling : NEEDS IMPROVEMENT"
            )

        else:
            print(
                "Negative query handling : POOR"
            )

    print()
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("RAG RETRIEVAL QUALITY TEST")
    print("=" * 70)

    print()
    print(f"Test cases       : {len(TEST_CASES)}")
    print(f"Top-K            : {TOP_K}")
    print(f"Min similarity   : {MIN_SIMILARITY}")

    print()
    print("Initializing retriever...")
    print()

    retriever = ArticleRetriever(
        top_k=TOP_K,
        min_similarity=MIN_SIMILARITY,
    )

    results = []

    for index, test_case in enumerate(
        TEST_CASES,
        start=1,
    ):

        try:

            result = run_test_case(
                retriever,
                test_case,
            )

            results.append(result)

            print_test_result(
                result,
                index,
            )

        except Exception as e:

            print()
            print("=" * 70)
            print(
                f"TEST {index}: {test_case.name}"
            )
            print("=" * 70)

            print(
                f"ERROR: {type(e).__name__}: {e}"
            )

    if results:
        print_summary(results)

    else:
        print()
        print("No tests were completed.")


if __name__ == "__main__":
    main()
