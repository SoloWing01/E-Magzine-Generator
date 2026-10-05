
"""
End-to-End RAG Pipeline Quality Test

Tests the complete pipeline:

    Query
      ↓
    Retrieval
      ↓
    Mistral Generation
      ↓
    JSON Validation
      ↓
    Citation Validation
      ↓
    Claim-Level Grounding
      ↓
    Factual Consistency
      ↓
    Final Acceptance

Run:

    python -m app.rag.rag_pipeline_test
"""

from dataclasses import dataclass
from typing import Optional

from app.rag.generator import RAGGenerator


# ============================================================
# CONFIGURATION
# ============================================================

TOP_K = 3
MIN_SIMILARITY = 0.20
GROUNDING_THRESHOLD = 0.45
MAX_GENERATION_ATTEMPTS = 2


# ============================================================
# TEST CASE
# ============================================================

@dataclass
class PipelineTestCase:
    name: str
    query: str
    expected_article_ids: list[int]


# ============================================================
# TEST DATASET
# ============================================================

TEST_CASES = [

    PipelineTestCase(
        name="Security / Drug Trafficking",
        query=(
            "Write a magazine article about security operations "
            "and drug trafficking along the India-Myanmar border "
            "in Northeast India."
        ),
        expected_article_ids=[29],
    ),

    PipelineTestCase(
        name="Nagaland Coffee Development",
        query=(
            "Write a magazine article about Nagaland coffee "
            "farmers, government support and modernization "
            "of coffee production."
        ),
        expected_article_ids=[32],
    ),

    PipelineTestCase(
        name="Guwahati Railway Infrastructure",
        query=(
            "Write a magazine article about Guwahati railway "
            "station infrastructure development and passenger "
            "traffic."
        ),
        expected_article_ids=[15],
    ),

    PipelineTestCase(
        name="Mizoram Funding",
        query=(
            "Write a magazine article about Centre funds not "
            "being released to Mizoram and the MNF seeking "
            "an explanation."
        ),
        expected_article_ids=[30],
    ),

    PipelineTestCase(
        name="Manipur Kuki Incident",
        query=(
            "Write a magazine article about the missing Kuki "
            "man found dead in Kangpokpi forest in Manipur."
        ),
        expected_article_ids=[31],
    ),
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_retrieved_article_ids(result: dict) -> list[int]:
    """
    Extract article IDs from the actual RAGGenerator result.
    """

    retrieved_articles = result.get(
        "retrieved_articles",
        [],
    )

    return [
        article.article_id
        for article in retrieved_articles
    ]


def get_similarities(result: dict) -> list[float]:
    """
    Extract retrieval similarities.
    """

    retrieved_articles = result.get(
        "retrieved_articles",
        [],
    )

    return [
        float(article.similarity)
        for article in retrieved_articles
    ]


def get_top_similarity(
    result: dict,
) -> Optional[float]:

    similarities = get_similarities(result)

    if not similarities:
        return None

    return similarities[0]


def get_grounding_metrics(
    result: dict,
) -> dict:

    grounding = result.get(
        "grounding",
        {},
    )

    claim_results = grounding.get(
        "claim_results",
        [],
    )

    total_claims = len(claim_results)

    supported_claims = sum(
        1
        for claim in claim_results
        if claim.get("supported", False)
    )

    unsupported_claims = (
        total_claims - supported_claims
    )

    if total_claims > 0:
        claim_support_rate = (
            supported_claims / total_claims
        )
    else:
        claim_support_rate = 0.0

    return {
        "valid": grounding.get(
            "valid",
            False,
        ),
        "total_claims": total_claims,
        "supported_claims": supported_claims,
        "unsupported_claims": unsupported_claims,
        "claim_support_rate": claim_support_rate,
        "cited_source_ids": grounding.get(
            "cited_source_ids",
            [],
        ),
        "missing_source_ids": grounding.get(
            "missing_source_ids",
            [],
        ),
        "invalid_source_ids": grounding.get(
            "invalid_source_ids",
            [],
        ),
        "errors": grounding.get(
            "errors",
            [],
        ),
    }


# ============================================================
# SINGLE PIPELINE TEST
# ============================================================

def run_test(
    generator: RAGGenerator,
    test_case: PipelineTestCase,
):

    print()
    print("=" * 70)
    print(f"TEST: {test_case.name}")
    print("=" * 70)

    print()
    print(f"Query:")
    print(test_case.query)

    print()
    print(
        f"Expected article IDs: "
        f"{test_case.expected_article_ids}"
    )

    # --------------------------------------------------------
    # Run RAG pipeline
    # --------------------------------------------------------

    try:

        result = generator.generate(
            query=test_case.query
        )

    except Exception as exc:

        print()
        print("PIPELINE EXCEPTION")
        print("-" * 70)
        print(
            f"{type(exc).__name__}: {exc}"
        )

        return {
            "success": False,
            "status": "exception",
            "retrieval_success": False,
            "json_success": False,
            "citation_success": False,
            "grounding_success": False,
            "article_generated": False,
            "top_similarity": None,
            "grounding": {},
            "errors": [
                f"{type(exc).__name__}: {exc}"
            ],
        }

    # --------------------------------------------------------
    # Basic status
    # --------------------------------------------------------

    success = result.get(
        "success",
        False,
    )

    status = result.get(
        "status",
        "unknown",
    )

    message = result.get(
        "message",
        "",
    )

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    retrieved_ids = get_retrieved_article_ids(
        result
    )

    similarities = get_similarities(
        result
    )

    top_similarity = get_top_similarity(
        result
    )

    retrieval_success = any(
        article_id in test_case.expected_article_ids
        for article_id in retrieved_ids
    )

    # --------------------------------------------------------
    # Generation
    # --------------------------------------------------------

    headline = result.get(
        "headline",
        "",
    )

    article = result.get(
        "article",
        "",
    )

    article_generated = bool(
        headline.strip()
        and article.strip()
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    json_success = status not in {
        "invalid_json",
        "generation_failed",
    }

    # --------------------------------------------------------
    # Citation validation
    # --------------------------------------------------------

    grounding = result.get(
        "grounding",
        {},
    )

    cited_source_ids = grounding.get(
        "cited_source_ids",
        [],
    )

    missing_source_ids = grounding.get(
        "missing_source_ids",
        [],
    )

    invalid_source_ids = grounding.get(
        "invalid_source_ids",
        [],
    )

    citation_success = (
        bool(cited_source_ids)
        and not missing_source_ids
        and not invalid_source_ids
        and status != "citation_failed"
    )

    # --------------------------------------------------------
    # Grounding
    # --------------------------------------------------------

    grounding_metrics = get_grounding_metrics(
        result
    )

    grounding_success = grounding_metrics[
        "valid"
    ]

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print()
    print("PIPELINE RESULT")
    print("-" * 70)

    print(
        f"Success             : "
        f"{'PASS' if success else 'FAIL'}"
    )

    print(
        f"Status              : "
        f"{status}"
    )

    print(
        f"Message             : "
        f"{message}"
    )

    print()
    print("RETRIEVAL")
    print("-" * 70)

    print(
        f"Retrieved article IDs: "
        f"{retrieved_ids}"
    )

    if similarities:

        print(
            "Similarities         : "
            f"{[round(x, 4) for x in similarities]}"
        )

    else:

        print(
            "Similarities         : NONE"
        )

    if top_similarity is not None:

        print(
            f"Top similarity       : "
            f"{top_similarity:.4f}"
        )

    else:

        print(
            "Top similarity       : NONE"
        )

    print(
        f"Expected article     : "
        f"{'PASS' if retrieval_success else 'FAIL'}"
    )

    print()
    print("GENERATION")
    print("-" * 70)

    print(
        f"JSON processing      : "
        f"{'PASS' if json_success else 'FAIL'}"
    )

    print(
        f"Article generated    : "
        f"{'PASS' if article_generated else 'FAIL'}"
    )

    print()
    print("CITATIONS")
    print("-" * 70)

    print(
        f"Cited source IDs     : "
        f"{cited_source_ids}"
    )

    print(
        f"Missing source IDs   : "
        f"{missing_source_ids}"
    )

    print(
        f"Invalid source IDs   : "
        f"{invalid_source_ids}"
    )

    print(
        f"Citation validation  : "
        f"{'PASS' if citation_success else 'FAIL'}"
    )

    print()
    print("GROUNDING")
    print("-" * 70)

    print(
        f"Grounding valid      : "
        f"{'PASS' if grounding_success else 'FAIL'}"
    )

    print(
        f"Total claims         : "
        f"{grounding_metrics['total_claims']}"
    )

    print(
        f"Supported claims     : "
        f"{grounding_metrics['supported_claims']}"
    )

    print(
        f"Unsupported claims   : "
        f"{grounding_metrics['unsupported_claims']}"
    )

    print(
        f"Claim support rate   : "
        f"{grounding_metrics['claim_support_rate']:.2%}"
    )

    # --------------------------------------------------------
    # Errors
    # --------------------------------------------------------

    errors = result.get(
        "errors",
        [],
    )

    grounding_errors = grounding_metrics[
        "errors"
    ]

    all_errors = []

    for error in errors + grounding_errors:

        if error not in all_errors:
            all_errors.append(error)

    if all_errors:

        print()
        print("ERRORS")
        print("-" * 70)

        for error in all_errors:
            print(
                f"- {error}"
            )

    # --------------------------------------------------------
    # Final test decision
    # --------------------------------------------------------

    test_passed = (
        success
        and retrieval_success
        and json_success
        and citation_success
        and grounding_success
        and article_generated
    )

    print()
    print("-" * 70)

    print(
        f"FINAL TEST RESULT   : "
        f"{'PASS' if test_passed else 'FAIL'}"
    )

    print("-" * 70)

    return {
        "success": success,
        "status": status,
        "retrieval_success": retrieval_success,
        "json_success": json_success,
        "citation_success": citation_success,
        "grounding_success": grounding_success,
        "article_generated": article_generated,
        "top_similarity": top_similarity,
        "grounding": grounding_metrics,
        "errors": all_errors,
        "test_passed": test_passed,
    }


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    results: list[dict],
):

    total = len(results)

    if total == 0:
        return

    passed = sum(
        result["test_passed"]
        for result in results
    )

    retrieval_passed = sum(
        result["retrieval_success"]
        for result in results
    )

    json_passed = sum(
        result["json_success"]
        for result in results
    )

    citation_passed = sum(
        result["citation_success"]
        for result in results
    )

    grounding_passed = sum(
        result["grounding_success"]
        for result in results
    )

    article_passed = sum(
        result["article_generated"]
        for result in results
    )

    total_claims = sum(
        result["grounding"]["total_claims"]
        for result in results
    )

    supported_claims = sum(
        result["grounding"]["supported_claims"]
        for result in results
    )

    unsupported_claims = sum(
        result["grounding"]["unsupported_claims"]
        for result in results
    )

    top_similarities = [
        result["top_similarity"]
        for result in results
        if result["top_similarity"] is not None
    ]

    average_similarity = (
        sum(top_similarities)
        / len(top_similarities)
        if top_similarities
        else 0.0
    )

    claim_support_rate = (
        supported_claims / total_claims
        if total_claims
        else 0.0
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print()
    print("=" * 70)
    print("END-TO-END RAG QUALITY REPORT")
    print("=" * 70)

    print()
    print("PIPELINE")
    print("-" * 70)

    print(
        f"Tests completed      : "
        f"{total}"
    )

    print(
        f"Complete RAG success : "
        f"{passed}/{total} "
        f"({passed / total:.2%})"
    )

    print()
    print("RETRIEVAL")
    print("-" * 70)

    print(
        f"Expected article     : "
        f"{retrieval_passed}/{total} "
        f"({retrieval_passed / total:.2%})"
    )

    print(
        f"Average top similarity: "
        f"{average_similarity:.4f}"
    )

    print()
    print("GENERATION")
    print("-" * 70)

    print(
        f"JSON processing      : "
        f"{json_passed}/{total} "
        f"({json_passed / total:.2%})"
    )

    print(
        f"Articles generated   : "
        f"{article_passed}/{total} "
        f"({article_passed / total:.2%})"
    )

    print()
    print("CITATIONS")
    print("-" * 70)

    print(
        f"Citation validation  : "
        f"{citation_passed}/{total} "
        f"({citation_passed / total:.2%})"
    )

    print()
    print("GROUNDING")
    print("-" * 70)

    print(
        f"Grounding passed     : "
        f"{grounding_passed}/{total} "
        f"({grounding_passed / total:.2%})"
    )

    print(
        f"Total claims         : "
        f"{total_claims}"
    )

    print(
        f"Supported claims     : "
        f"{supported_claims}"
    )

    print(
        f"Unsupported claims   : "
        f"{unsupported_claims}"
    )

    print(
        f"Claim support rate   : "
        f"{claim_support_rate:.2%}"
    )

    print()
    print("TEST SUMMARY")
    print("-" * 70)

    for index, result in enumerate(
        results,
        start=1,
    ):

        status = (
            "PASS"
            if result["test_passed"]
            else "FAIL"
        )

        print(
            f"{index:02d}. "
            f"{status:<6} "
            f"{'Success' if result['success'] else result['status']}"
        )

    print()
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("END-TO-END RAG PIPELINE QUALITY TEST")
    print("=" * 70)

    print()
    print(
        f"Tests                : {len(TEST_CASES)}"
    )

    print(
        f"Top-K                : {TOP_K}"
    )

    print(
        f"Min similarity       : {MIN_SIMILARITY}"
    )

    print(
        f"Grounding threshold  : {GROUNDING_THRESHOLD}"
    )

    print(
        f"Max generation tries : {MAX_GENERATION_ATTEMPTS}"
    )

    print()
    print(
        "Initializing RAG generator..."
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Your actual class is RAGGenerator.
    # --------------------------------------------------------

    generator = RAGGenerator(
        top_k=TOP_K,
        min_similarity=MIN_SIMILARITY,
        grounding_threshold=GROUNDING_THRESHOLD,
        max_generation_attempts=MAX_GENERATION_ATTEMPTS,
    )

    results = []

    for test_case in TEST_CASES:

        result = run_test(
            generator,
            test_case,
        )

        results.append(result)

    print_summary(results)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
