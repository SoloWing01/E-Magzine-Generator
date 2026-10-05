
import json
import re
from typing import Any

from app.rag.retriever import ArticleRetriever
from app.rag.grounding import GroundingValidator
from app.llm.mistral import MistralClient


class RAGGenerator:
    """
    Grounded RAG article generator.

    Control flow:

        User query
            ↓
        Retrieval query cleanup
            ↓
        Chroma retrieval
            ↓
        Retrieval quality gate
            ↓
        Evidence context
            ↓
        Mistral generation
            ↓
        JSON extraction
            ↓
        Structure validation
            ↓
        Citation validation
            ↓
        Claim-level grounding
            ↓
        Grounding acceptance gate
            ↓
        Trusted source metadata
            ↓
        SUCCESS

    Important safety rules:

    1. Mistral is NOT called when retrieval produces no
       sufficiently relevant evidence.

    2. Weak retrieval results are never forced into generation.

    3. A grounding failure is never returned as a successful article.

    4. Failed drafts are stored under "draft_article" for
       debugging, while "article" remains empty.

    5. Grounding failures may trigger a limited regeneration.

    6. Source metadata is always constructed from retrieved
       database/vector-store metadata, never from Mistral.
    """

    SYSTEM_PROMPT = """
You are an AI editorial writer for a Northeast India e-magazine.

Your task is to write a factual magazine article using ONLY the
source material supplied by the retrieval system.

STRICT GROUNDING RULES:

1. Use ONLY information explicitly present in the supplied sources.

2. Do NOT use outside knowledge.

3. Do NOT invent facts, numbers, dates, locations, organizations,
   events, quotes, explanations, historical context, or conclusions.

4. Do NOT make assumptions from general knowledge.

5. Every factual paragraph MUST contain at least one citation in
   this exact format:

   [Source 1]

6. Only use source IDs that actually appear in the supplied evidence.

7. Do not create source titles.

8. Do not create source URLs.

9. Do not create a bibliography.

10. Do not mention information that cannot be supported by the
    supplied source material.

11. Return ONLY valid JSON.

12. Do NOT wrap the JSON inside Markdown code fences.

13. The "article" value MUST be one JSON string.

14. Use escaped newline characters such as \\n\\n inside the
    article string instead of literal line breaks.

15. The source_ids field must contain exactly the source IDs
    cited in the article.

16. Keep claims conservative. If the sources do not establish
    something, do not state it.

17. Do not combine facts from different sources into a new
    unsupported conclusion.

JSON FORMAT:

{
    "headline": "string",
    "article": "string",
    "source_ids": [1]
}
"""

    def __init__(
        self,
        top_k: int = 3,
        min_similarity: float = 0.20,
        grounding_threshold: float = 0.45,
        max_generation_attempts: int = 2,
    ):
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        if min_similarity < -1 or min_similarity > 1:
            raise ValueError(
                "min_similarity must be between -1 and 1."
            )

        if grounding_threshold < -1 or grounding_threshold > 1:
            raise ValueError(
                "grounding_threshold must be between -1 and 1."
            )

        if max_generation_attempts <= 0:
            raise ValueError(
                "max_generation_attempts must be greater than zero."
            )

        self.top_k = top_k
        self.min_similarity = min_similarity
        self.grounding_threshold = grounding_threshold
        self.max_generation_attempts = max_generation_attempts

        self.retriever = ArticleRetriever(
            top_k=top_k,
            min_similarity=min_similarity,
        )

        self.llm = MistralClient(
            temperature=0.1,
            max_tokens=2000,
        )

        # Reuse the exact same embedding model instance used
        # by the retriever.
        self.grounding_validator = GroundingValidator(
            embedder=self.retriever.embedder,
            similarity_threshold=grounding_threshold,
        )

    # =============================================================
    # QUERY PREPARATION
    # =============================================================

    @staticmethod
    def _build_retrieval_query(query: str) -> str:
        """
        Convert an editorial instruction into a cleaner semantic
        retrieval query.

        Example:

        "Write a magazine article about security operations and
        drug trafficking along the India-Myanmar border"

        becomes approximately:

        "security operations and drug trafficking along the
        India-Myanmar border"
        """

        cleaned = query.strip()

        prefixes = [
            "write a magazine article about",
            "write an article about",
            "write a magazine article on",
            "write an article on",
            "write about",
            "generate a magazine article about",
            "generate an article about",
            "create a magazine article about",
            "create an article about",
        ]

        lowered = cleaned.lower()

        for prefix in prefixes:
            if lowered.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break

        cleaned = cleaned.rstrip(".")

        return cleaned

    # =============================================================
    # CONTEXT
    # =============================================================

    def _build_context(
        self,
        articles,
    ) -> str:
        if not articles:
            raise ValueError(
                "No relevant evidence was retrieved."
            )

        sections = []

        for article in articles:
            section = f"""
[Source {article.source_id}]

Article ID:
{article.article_id}

Title:
{article.title}

Source:
{article.source}

Published Date:
{article.published_date}

Category:
{article.category}

Article Score:
{article.article_score}

Retrieval Similarity:
{article.similarity:.4f}

Content:
{article.content}
""".strip()

            sections.append(section)

        return "\n\n".join(sections)

    # =============================================================
    # JSON EXTRACTION
    # =============================================================

    def _extract_json(
        self,
        text: str,
    ) -> dict[str, Any]:

        if not text or not text.strip():
            raise ValueError(
                "Mistral returned an empty response."
            )

        cleaned = text.strip()

        # ---------------------------------------------------------
        # Remove Markdown fences
        # ---------------------------------------------------------

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if (
                lines
                and lines[0].strip().startswith("```")
            ):
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        # ---------------------------------------------------------
        # Normal JSON
        # ---------------------------------------------------------

        try:
            return json.loads(cleaned)

        except json.JSONDecodeError:
            pass

        # ---------------------------------------------------------
        # Extract JSON object
        # ---------------------------------------------------------

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if (
            start == -1
            or end == -1
            or end <= start
        ):
            raise ValueError(
                "Mistral response does not contain "
                "a JSON object."
            )

        candidate = cleaned[start:end + 1]

        # ---------------------------------------------------------
        # Repair literal control characters
        # ---------------------------------------------------------

        repaired = []

        inside_string = False
        escaped = False

        for char in candidate:

            if escaped:
                repaired.append(char)
                escaped = False
                continue

            if char == "\\":
                repaired.append(char)
                escaped = True
                continue

            if char == '"':
                repaired.append(char)
                inside_string = not inside_string
                continue

            if inside_string:

                if char == "\n":
                    repaired.append("\\n")
                    continue

                if char == "\r":
                    repaired.append("\\r")
                    continue

                if char == "\t":
                    repaired.append("\\t")
                    continue

            repaired.append(char)

        repaired_candidate = "".join(repaired)

        try:
            return json.loads(repaired_candidate)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Mistral returned malformed JSON: {exc}"
            ) from exc

    # =============================================================
    # STRUCTURE VALIDATION
    # =============================================================

    def _validate_structure(
        self,
        data: dict[str, Any],
    ) -> None:

        if not isinstance(data, dict):
            raise ValueError(
                "LLM response must be a JSON object."
            )

        required_fields = [
            "headline",
            "article",
            "source_ids",
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(
                    f"Missing required field: {field}"
                )

        if not isinstance(data["headline"], str):
            raise ValueError(
                "'headline' must be a string."
            )

        if not isinstance(data["article"], str):
            raise ValueError(
                "'article' must be a string."
            )

        if not data["headline"].strip():
            raise ValueError(
                "Headline is empty."
            )

        if not data["article"].strip():
            raise ValueError(
                "Article is empty."
            )

        if not isinstance(data["source_ids"], list):
            raise ValueError(
                "'source_ids' must be a list."
            )

        for source_id in data["source_ids"]:
            if (
                not isinstance(source_id, int)
                or isinstance(source_id, bool)
            ):
                raise ValueError(
                    "Every source_id must be an integer."
                )

    # =============================================================
    # CITATIONS
    # =============================================================

    @staticmethod
    def _extract_citations(
        article_text: str,
    ) -> list[int]:

        matches = re.findall(
            r"\[Source\s+(\d+)\]",
            article_text,
            flags=re.IGNORECASE,
        )

        return sorted(
            {
                int(source_id)
                for source_id in matches
            }
        )

    # =============================================================
    # SOURCE METADATA
    # =============================================================

    def _build_sources(
        self,
        source_ids: list[int],
        retrieved_articles,
    ) -> list[dict[str, Any]]:

        article_by_source_id = {
            article.source_id: article
            for article in retrieved_articles
        }

        sources = []

        for source_id in source_ids:

            article = article_by_source_id.get(
                source_id
            )

            if article is None:
                raise ValueError(
                    f"Source ID {source_id} "
                    "was not retrieved."
                )

            sources.append(
                {
                    "source_id": article.source_id,
                    "article_id": article.article_id,
                    "title": article.title,
                    "source": article.source,
                    "url": article.url,
                    "published_date": article.published_date,
                }
            )

        return sources

    # =============================================================
    # RESULT BUILDERS
    # =============================================================

    @staticmethod
    def _grounding_to_dict(
        grounding,
    ) -> dict[str, Any]:

        return {
            "valid": grounding.valid,
            "cited_source_ids": (
                grounding.cited_source_ids
            ),
            "missing_source_ids": (
                grounding.missing_source_ids
            ),
            "invalid_source_ids": (
                grounding.invalid_source_ids
            ),
            "unsupported_claims": (
                grounding.unsupported_claims
            ),
            "claim_results": [
                {
                    "claim": claim.claim,
                    "source_id": claim.source_id,
                    "similarity": round(
                        claim.similarity,
                        4,
                    ),
                    "semantic_supported": (
                        claim.semantic_supported
                    ),
                    "factual_supported": (
                        claim.factual_supported
                    ),
                    "supported": claim.supported,
                    "claim_numbers": (
                        claim.claim_numbers
                    ),
                    "source_numbers": (
                        claim.source_numbers
                    ),
                    "claim_dates": (
                        claim.claim_dates
                    ),
                    "source_dates": (
                        claim.source_dates
                    ),
                    "claim_entities": (
                        claim.claim_entities
                    ),
                    "source_entities": (
                        claim.source_entities
                    ),
                    "factual_errors": (
                        claim.factual_errors
                    ),
                }
                for claim in grounding.claim_results
            ],
            "errors": grounding.errors,
        }

    def _build_failure_result(
        self,
        query: str,
        status: str,
        message: str,
        articles=None,
        headline: str = "",
        draft_article: str = "",
        source_ids: list[int] | None = None,
        errors: list[str] | None = None,
        grounding=None,
        attempt: int = 0,
    ) -> dict[str, Any]:

        if articles is None:
            articles = []

        if source_ids is None:
            source_ids = []

        if errors is None:
            errors = []

        result = {
            "success": False,
            "status": status,
            "message": message,
            "query": query,
            "headline": "",
            "article": "",
            "draft_headline": headline,
            "draft_article": draft_article,
            "source_ids": [],
            "sources": [],
            "retrieved_articles": articles,
            "attempt": attempt,
            "errors": errors,
        }

        if grounding is not None:
            result["grounding"] = self._grounding_to_dict(
                grounding
            )
        else:
            result["grounding"] = {
                "valid": False,
                "cited_source_ids": [],
                "missing_source_ids": [],
                "invalid_source_ids": [],
                "unsupported_claims": [],
                "claim_results": [],
                "errors": errors,
            }

        return result

    def _build_success_result(
        self,
        query: str,
        headline: str,
        article: str,
        grounding,
        sources,
        retrieved_articles,
        attempt: int,
    ) -> dict[str, Any]:

        return {
            "success": True,
            "status": "success",
            "message": "Grounded article generated successfully.",
            "query": query,
            "headline": headline,
            "article": article,
            "source_ids": grounding.cited_source_ids,
            "sources": sources,
            "retrieved_articles": retrieved_articles,
            "attempt": attempt,
            "grounding": self._grounding_to_dict(
                grounding
            ),
        }

    # =============================================================
    # GENERATION PROMPT
    # =============================================================

    def _build_user_prompt(
        self,
        query: str,
        context: str,
        correction: str = "",
    ) -> str:

        correction_block = ""

        if correction:
            correction_block = f"""

PREVIOUS ATTEMPT FAILED GROUNDING.

IMPORTANT CORRECTION:

{correction}

For this attempt, remove or rewrite every unsupported claim.
Do not repeat unsupported facts simply because they appeared in
the previous draft.
"""

        return f"""
Write a magazine article based ONLY on the evidence below.

QUERY:

{query}

RETRIEVED EVIDENCE:

{context}

IMPORTANT:

- Do not use outside knowledge.
- Do not invent facts.
- Do not infer facts.
- Do not make broad conclusions unless explicitly supported.
- Every factual paragraph must contain [Source N].
- Only use source IDs shown in the evidence.
- Return only valid JSON.
- Do not use Markdown code fences.
- The article must be a JSON string.
- Use escaped newline characters such as \\n\\n.
{correction_block}
"""

    # =============================================================
    # GROUNDING FAILURE CORRECTION
    # =============================================================

    @staticmethod
    def _build_grounding_correction(
        grounding,
    ) -> str:

        unsupported = grounding.unsupported_claims

        if not unsupported:
            return (
                "The previous article failed grounding. "
                "Rewrite it using only directly supported "
                "information from the supplied sources."
            )

        lines = [
            "The following claims were not sufficiently "
            "supported by the retrieved evidence:"
        ]

        for claim in unsupported:
            lines.append(
                f"- {claim}"
            )

        lines.append(
            "Remove these claims or rewrite them using "
            "only facts directly established by the sources."
        )

        lines.append(
            "Do not add replacement facts from outside knowledge."
        )

        return "\n".join(lines)

    # =============================================================
    # SINGLE GENERATION ATTEMPT
    # =============================================================

    def _generate_attempt(
        self,
        query: str,
        articles,
        context: str,
        attempt: int,
        correction: str = "",
    ) -> dict[str, Any]:

        user_prompt = self._build_user_prompt(
            query=query,
            context=context,
            correction=correction,
        )

        # ---------------------------------------------------------
        # Mistral
        # ---------------------------------------------------------

        try:
            raw_response = self.llm.generate(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            print()
            print("=" * 70)
            print("RAW MISTRAL RESPONSE")
            print("=" * 70)
            print(raw_response)
            print("=" * 70)

        except Exception as exc:
            return self._build_failure_result(
                query=query,
                status="generation_failed",
                message="Mistral generation failed.",
                articles=articles,
                errors=[str(exc)],
                attempt=attempt,
            )

        # ---------------------------------------------------------
        # JSON parsing
        # ---------------------------------------------------------

        try:
            data = self._extract_json(
                raw_response
            )

        except Exception as exc:
            return self._build_failure_result(
                query=query,
                status="invalid_json",
                message="Mistral returned invalid JSON.",
                articles=articles,
                draft_article=raw_response,
                errors=[str(exc)],
                attempt=attempt,
            )

        # ---------------------------------------------------------
        # Structure
        # ---------------------------------------------------------

        try:
            self._validate_structure(data)

        except Exception as exc:
            return self._build_failure_result(
                query=query,
                status="invalid_structure",
                message="Mistral returned an invalid article structure.",
                articles=articles,
                headline=data.get(
                    "headline",
                    "",
                ),
                draft_article=data.get(
                    "article",
                    "",
                ),
                source_ids=data.get(
                    "source_ids",
                    [],
                ),
                errors=[str(exc)],
                attempt=attempt,
            )

        headline = data["headline"]
        article = data["article"]

        declared_source_ids = sorted(
            set(data["source_ids"])
        )

        actual_source_ids = self._extract_citations(
            article
        )

        # ---------------------------------------------------------
        # source_ids must equal actual citations
        # ---------------------------------------------------------

        if declared_source_ids != actual_source_ids:
            return self._build_failure_result(
                query=query,
                status="citation_failed",
                message=(
                    "The source_ids field does not match "
                    "the citations actually used in the article."
                ),
                articles=articles,
                headline=headline,
                draft_article=article,
                source_ids=declared_source_ids,
                errors=[
                    (
                        "Declared source IDs: "
                        f"{declared_source_ids}; "
                        "actual citation IDs: "
                        f"{actual_source_ids}."
                    )
                ],
                attempt=attempt,
            )

        # ---------------------------------------------------------
        # Every citation must correspond to retrieved evidence
        # ---------------------------------------------------------

        available_source_ids = [
            article.source_id
            for article in articles
        ]

        invalid_citations = sorted(
            set(actual_source_ids)
            - set(available_source_ids)
        )

        if invalid_citations:
            return self._build_failure_result(
                query=query,
                status="citation_failed",
                message=(
                    "The article contains citations that "
                    "were not present in retrieved evidence."
                ),
                articles=articles,
                headline=headline,
                draft_article=article,
                source_ids=declared_source_ids,
                errors=[
                    (
                        "Invalid source IDs: "
                        f"{invalid_citations}"
                    )
                ],
                attempt=attempt,
            )

        # ---------------------------------------------------------
        # Claim-level grounding
        # ---------------------------------------------------------

        try:
            grounding = (
                self.grounding_validator.validate(
                    article_text=article,
                    available_source_ids=(
                        available_source_ids
                    ),
                    retrieved_articles=articles,
                    require_citations=True,
                )
            )

        except Exception as exc:
            return self._build_failure_result(
                query=query,
                status="grounding_error",
                message="Grounding validation failed unexpectedly.",
                articles=articles,
                headline=headline,
                draft_article=article,
                source_ids=declared_source_ids,
                errors=[str(exc)],
                attempt=attempt,
            )

        # ---------------------------------------------------------
        # Grounding failed
        # ---------------------------------------------------------

        if not grounding.valid:
            return self._build_failure_result(
                query=query,
                status="grounding_failed",
                message=(
                    "The generated article contains one or more "
                    "claims that could not be sufficiently grounded."
                ),
                articles=articles,
                headline=headline,
                draft_article=article,
                source_ids=declared_source_ids,
                grounding=grounding,
                attempt=attempt,
            )

        # ---------------------------------------------------------
        # Trusted sources
        # ---------------------------------------------------------

        try:
            sources = self._build_sources(
                source_ids=grounding.cited_source_ids,
                retrieved_articles=articles,
            )

        except Exception as exc:
            return self._build_failure_result(
                query=query,
                status="source_metadata_failed",
                message="Trusted source metadata could not be constructed.",
                articles=articles,
                headline=headline,
                draft_article=article,
                source_ids=declared_source_ids,
                grounding=grounding,
                errors=[str(exc)],
                attempt=attempt,
            )

        # ---------------------------------------------------------
        # SUCCESS
        # ---------------------------------------------------------

        return self._build_success_result(
            query=query,
            headline=headline,
            article=article,
            grounding=grounding,
            sources=sources,
            retrieved_articles=articles,
            attempt=attempt,
        )

    # =============================================================
    # GENERATE
    # =============================================================

    def generate(
        self,
        query: str,
    ) -> dict[str, Any]:

        if not query or not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        query = query.strip()

        # ---------------------------------------------------------
        # Retrieval query
        # ---------------------------------------------------------

        retrieval_query = self._build_retrieval_query(
            query
        )

        # ---------------------------------------------------------
        # Retrieval
        # ---------------------------------------------------------

        articles = self.retriever.retrieve(
            query=retrieval_query,
            top_k=self.top_k,
        )

        # ---------------------------------------------------------
        # HARD RETRIEVAL GATE
        #
        # If nothing passed the retrieval threshold:
        #
        #   DO NOT call Mistral.
        #   DO NOT attempt grounding.
        #   DO NOT generate an article.
        # ---------------------------------------------------------

        if not articles:
            return self._build_failure_result(
                query=query,
                status="insufficient_evidence",
                message=(
                    "No relevant evidence was retrieved. "
                    "The minimum retrieval similarity threshold "
                    f"is {self.min_similarity:.2f}."
                ),
                articles=[],
                errors=[
                    (
                        "Retrieval query: "
                        f"{retrieval_query}"
                    ),
                    (
                        "No retrieved article met the minimum "
                        "similarity threshold."
                    ),
                ],
            )

        # ---------------------------------------------------------
        # Build evidence context
        # ---------------------------------------------------------

        try:
            context = self._build_context(
                articles
            )

        except Exception as exc:
            return self._build_failure_result(
                query=query,
                status="context_build_failed",
                message="Evidence context could not be built.",
                articles=articles,
                errors=[str(exc)],
            )

        # ---------------------------------------------------------
        # Controlled generation attempts
        # ---------------------------------------------------------

        correction = ""
        last_result = None

        for attempt in range(
            1,
            self.max_generation_attempts + 1,
        ):

            result = self._generate_attempt(
                query=query,
                articles=articles,
                context=context,
                attempt=attempt,
                correction=correction,
            )

            last_result = result

            # -----------------------------------------------------
            # SUCCESS
            # -----------------------------------------------------

            if result["success"]:
                return result

            # -----------------------------------------------------
            # Only grounding failures should trigger regeneration.
            #
            # JSON, API, citation, structure, and retrieval failures
            # are not automatically regenerated.
            # -----------------------------------------------------

            if result["status"] != "grounding_failed":
                return result

            # -----------------------------------------------------
            # No more attempts
            # -----------------------------------------------------

            if attempt >= self.max_generation_attempts:
                break

            grounding_data = result.get(
                "grounding",
                {},
            )

            unsupported = grounding_data.get(
                "unsupported_claims",
                [],
            )

            if unsupported:
                correction = self._build_grounding_correction(
                    type(
                        "GroundingProxy",
                        (),
                        {
                            "unsupported_claims": unsupported
                        },
                    )()
                )
            else:
                correction = (
                    "The previous article failed grounding. "
                    "Rewrite it using only information that is "
                    "directly supported by the retrieved sources."
                )

        # ---------------------------------------------------------
        # All attempts failed
        # ---------------------------------------------------------

        if last_result is not None:
            last_result["message"] = (
                "Grounding failed after "
                f"{self.max_generation_attempts} "
                "generation attempt(s)."
            )

            return last_result

        return self._build_failure_result(
            query=query,
            status="generation_failed",
            message="No generation attempt completed.",
            articles=articles,
        )


# =================================================================
# TEST
# =================================================================

if __name__ == "__main__":

    print("=" * 70)
    print("GROUNDED RAG GENERATOR TEST")
    print("=" * 70)

    generator = RAGGenerator(
        top_k=3,
        min_similarity=0.20,
        grounding_threshold=0.45,
        max_generation_attempts=2,
    )

    # Keep the test query focused on the actual subject.
    # This also matches the retrieval test used in retriever.py.
    test_query = (
        "security operations and drug trafficking "
        "along the India-Myanmar border in Northeast India"
    )

    result = generator.generate(
        query=test_query
    )

    print()
    print("=" * 70)
    print("RAG STATUS")
    print("=" * 70)

    print(
        f"Success : {result.get('success')}"
    )

    print(
        f"Status  : {result.get('status')}"
    )

    print(
        f"Message : {result.get('message')}"
    )

    print(
        f"Attempt : {result.get('attempt', 0)}"
    )

    # -------------------------------------------------------------
    # Retrieval information
    # -------------------------------------------------------------

    retrieved_articles = result.get(
        "retrieved_articles",
        [],
    )

    print()
    print("=" * 70)
    print("RETRIEVAL")
    print("=" * 70)

    if retrieved_articles:

        for article in retrieved_articles:
            print()
            print(
                f"[Source {article.source_id}]"
            )
            print(
                f"Article ID : {article.article_id}"
            )
            print(
                f"Title      : {article.title}"
            )
            print(
                f"Similarity : "
                f"{article.similarity:.4f}"
            )

    else:
        print("No sufficiently relevant articles retrieved.")

    # -------------------------------------------------------------
    # Grounding
    # -------------------------------------------------------------

    grounding = result.get(
        "grounding",
        {},
    )

    print()
    print("=" * 70)
    print("GROUNDING STATUS")
    print("=" * 70)

    print(
        f"Valid          : "
        f"{grounding.get('valid')}"
    )

    print(
        f"Cited sources  : "
        f"{grounding.get('cited_source_ids')}"
    )

    print(
        f"Missing sources: "
        f"{grounding.get('missing_source_ids')}"
    )

    print(
        f"Invalid sources: "
        f"{grounding.get('invalid_source_ids')}"
    )

    # -------------------------------------------------------------
    # Claim results
    # -------------------------------------------------------------

    claim_results = grounding.get(
        "claim_results",
        [],
    )

    if claim_results:

        print()
        print("=" * 70)
        print("CLAIM VERIFICATION")
        print("=" * 70)

        for index, claim in enumerate(
            claim_results,
            start=1,
        ):

            print()
            print(
                f"Claim {index}"
            )

            print(
                f"Source     : "
                f"{claim.get('source_id')}"
            )

            print(
                f"Similarity : "
                f"{claim.get('similarity')}"
            )

            print(
                f"Semantic   : "
                f"{claim.get('semantic_supported')}"
            )

            print(
                f"Factual    : "
                f"{claim.get('factual_supported')}"
            )

            print(
                f"Supported  : "
                f"{claim.get('supported')}"
            )

            print(
                f"Text       : "
                f"{claim.get('claim')}"
            )

    # -------------------------------------------------------------
    # Unsupported claims
    # -------------------------------------------------------------

    unsupported = grounding.get(
        "unsupported_claims",
        [],
    )

    if unsupported:

        print()
        print("=" * 70)
        print("UNSUPPORTED CLAIMS")
        print("=" * 70)

        for claim in unsupported:
            print(
                f"- {claim}"
            )

    # -------------------------------------------------------------
    # Errors
    # -------------------------------------------------------------

    errors = result.get(
        "errors",
        [],
    )

    grounding_errors = grounding.get(
        "errors",
        [],
    )

    all_errors = []

    for error in errors + grounding_errors:
        if error not in all_errors:
            all_errors.append(error)

    if all_errors:

        print()
        print("=" * 70)
        print("ERRORS")
        print("=" * 70)

        for error in all_errors:
            print(
                f"- {error}"
            )

    # -------------------------------------------------------------
    # SUCCESS OUTPUT
    #
    # IMPORTANT:
    # We only print the magazine-ready article when success=True.
    # Failed drafts are intentionally NOT printed as final articles.
    # -------------------------------------------------------------

    if result.get("success"):

        print()
        print("=" * 70)
        print("HEADLINE")
        print("=" * 70)

        print(
            result.get(
                "headline",
                "",
            )
        )

        print()
        print("=" * 70)
        print("ARTICLE")
        print("=" * 70)

        print(
            result.get(
                "article",
                "",
            )
        )

        print()
        print("=" * 70)
        print("SOURCES")
        print("=" * 70)

        for source in result.get(
            "sources",
            [],
        ):

            print()
            print(
                f"[Source {source['source_id']}]"
            )

            print(
                f"Article ID : "
                f"{source['article_id']}"
            )

            print(
                f"Title      : "
                f"{source['title']}"
            )

            print(
                f"Source     : "
                f"{source['source']}"
            )

            print(
                f"URL        : "
                f"{source['url']}"
            )

            print(
                f"Published  : "
                f"{source['published_date']}"
            )

    else:

        print()
        print("=" * 70)
        print("ARTICLE NOT ACCEPTED")
        print("=" * 70)

        print(
            "The generated content was not accepted as "
            "a grounded magazine article."
        )

        print(
            f"Reason: {result.get('status')}"
        )

        print(
            f"Message: {result.get('message')}"
        )

        if result.get("draft_article"):
            print()
            print(
                "A rejected draft exists internally "
                "for debugging, but it is NOT treated "
                "as magazine-ready content."
            )
