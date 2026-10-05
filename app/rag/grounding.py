import re
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np


@dataclass
class ClaimResult:
    claim: str
    source_id: int
    best_similarity: float
    semantic_supported: bool
    factual_supported: bool
    supported: bool
    claim_numbers: list[str] = field(default_factory=list)
    source_numbers: list[str] = field(default_factory=list)
    claim_dates: list[str] = field(default_factory=list)
    source_dates: list[str] = field(default_factory=list)
    claim_entities: list[str] = field(default_factory=list)
    source_entities: list[str] = field(default_factory=list)
    factual_errors: list[str] = field(default_factory=list)

    @property
    def similarity(self) -> float:
        return self.best_similarity


@dataclass
class GroundingValidation:
    is_grounded: bool = False
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: list[str] = field(default_factory=list)
    claim_results: list[ClaimResult] = field(default_factory=list)
    supported_claim_results: list[ClaimResult] = field(default_factory=list)
    cited_source_ids: list[int] = field(default_factory=list)
    missing_source_ids: list[int] = field(default_factory=list)
    invalid_source_ids: list[int] = field(default_factory=list)
    citation_errors: list[str] = field(default_factory=list)
    grounding_errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.is_grounded

    @property
    def grounding_score(self) -> float:
        if self.total_claims == 0:
            return 0.0
        return (self.supported_claims / self.total_claims) * 100.0

    @property
    def errors(self) -> list[str]:
        return self.grounding_errors


class GroundingValidator:
    """
    Validates generated RAG content against retrieved source articles.

    Design:
      - semantic validation uses the best matching source sentence
      - factual validation uses the complete cited source article
      - source sentence embeddings are cached once per source
      - citation validation supports both paragraph-level citations and
        a single article-level trailing citation
      - dates are normalized to calendar values, so equivalent formats
        such as 'September 30, 2026' and '30 September 2026' match
    """

    NUMBER_PATTERN = re.compile(
        r"\b\d+(?:\.\d+)?(?:\s*(?:kg|km|crore|lakh|million|billion|%|percent|years?|days?|hours?|months?))?\b",
        re.IGNORECASE,
    )

    DATE_PATTERN = re.compile(
        r"\b(?:"
        r"\d{4}-\d{1,2}-\d{1,2}"
        r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)\s+\d{1,2}(?:,)?\s+\d{4}"
        r"|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}"
        r")\b",
        re.IGNORECASE,
    )

    YEAR_PATTERN = re.compile(r"\b\d{4}\b")

    CITATION_PATTERN = re.compile(r"\[Source\s+(\d+)\]", re.IGNORECASE)

    ENTITY_TERMS = [
        "assam",
        "arunachal pradesh",
        "manipur",
        "meghalaya",
        "mizoram",
        "nagaland",
        "sikkim",
        "tripura",
        "northeast india",
        "northeastern india",
        "northeast",
        "northeastern",
        "india-myanmar border",
        "myanmar border",
        "golden triangle",
        "indian army",
        "army",
        "assam rifles",
        "bsf",
        "iaf",
        "air force",
        "security forces",
        "paramilitary",
        "government",
        "centre",
        "central government",
        "state government",
        "heroin",
        "methamphetamine",
        "yaba",
        "ganja",
        "narcotics",
        "drug trafficking",
        "drug smuggling",
        "ndps act",
        "narcotic drugs and psychotropic substances act",
    ]

    def __init__(self, embedder, similarity_threshold: float = 0.45):
        self.embedder = embedder
        self.similarity_threshold = similarity_threshold

        print("=" * 70)
        print("GROUNDING VALIDATOR")
        print("=" * 70)
        print(f"Similarity threshold : {self.similarity_threshold}")
        print("Embedding model      : Reusing retriever embedder")
        print("Factual checking     : Full cited source")
        print("Embedding caching    : Enabled")
        print("Citation handling    : Paragraph + article-level inheritance")
        print("Date checking        : Calendar-date normalization")

    def extract_citations(self, text: str) -> list[int]:
        if not text:
            return []
        return sorted({int(match) for match in self.CITATION_PATTERN.findall(text)})

    def clean_claim(self, claim: str) -> str:
        if not claim:
            return ""
        return self.CITATION_PATTERN.sub("", claim).strip()

    def split_sentences(self, text: str) -> list[str]:
        if not text:
            return []
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []
        return [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", normalized)
            if sentence.strip()
        ]

    def extract_numbers(self, text: str) -> list[str]:
        if not text:
            return []
        return [m.group().strip().lower() for m in self.NUMBER_PATTERN.finditer(text)]

    @staticmethod
    def _parse_date(value: str):
        value = value.strip().replace(",", "")
        formats = (
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%B %d %Y",
            "%b %d %Y",
            "%d %B %Y",
            "%d %b %Y",
        )
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    def extract_dates(self, text: str) -> list[str]:
        """Return normalized dates as YYYY-MM-DD plus standalone years."""
        if not text:
            return []

        results = []
        occupied_spans = []

        for match in self.DATE_PATTERN.finditer(text):
            raw = match.group(0)
            parsed = self._parse_date(raw)
            if parsed:
                results.append(parsed.isoformat())
                occupied_spans.append(match.span())

        # Add standalone years that are not already part of a full date.
        for match in self.YEAR_PATTERN.finditer(text):
            if any(start <= match.start() < end for start, end in occupied_spans):
                continue
            results.append(match.group(0))

        return sorted(set(results))

    def extract_entities(self, text: str) -> list[str]:
        if not text:
            return []
        text_lower = text.lower()
        return sorted({entity for entity in self.ENTITY_TERMS if entity in text_lower})

    @staticmethod
    def normalize_fact(value: str) -> str:
        value = value.lower().strip()
        return re.sub(r"\s+", " ", value)

    def fact_exists_in_source(self, fact: str, source_facts: list[str]) -> bool:
        normalized_fact = self.normalize_fact(fact)
        normalized_source = [self.normalize_fact(item) for item in source_facts]

        if normalized_fact in normalized_source:
            return True

        fact_number_match = re.search(r"\d+(?:\.\d+)?", normalized_fact)
        if fact_number_match:
            fact_number = fact_number_match.group()
            for source_fact in normalized_source:
                source_number_match = re.search(r"\d+(?:\.\d+)?", source_fact)
                if source_number_match and source_number_match.group() == fact_number:
                    return True

        return False

    def check_factual_consistency(self, claim: str, source_text: str):
        claim_numbers = self.extract_numbers(claim)
        source_numbers = self.extract_numbers(source_text)
        claim_dates = self.extract_dates(claim)
        source_dates = self.extract_dates(source_text)
        claim_entities = self.extract_entities(claim)
        source_entities = self.extract_entities(source_text)

        factual_errors = []

        for number in claim_numbers:
            if not self.fact_exists_in_source(number, source_numbers):
                factual_errors.append(f"Number not found in source: {number}")

        for date in claim_dates:
            if not self.fact_exists_in_source(date, source_dates):
                factual_errors.append(f"Date not found in source: {date}")

        for entity in claim_entities:
            if entity not in source_entities:
                factual_errors.append(f"Entity not found in source: {entity}")

        return (
            len(factual_errors) == 0,
            claim_numbers,
            source_numbers,
            claim_dates,
            source_dates,
            claim_entities,
            source_entities,
            factual_errors,
        )

    def prepare_source(self, source_id: int, source_text: str) -> dict:
        sentences = self.split_sentences(source_text) or [source_text]
        embeddings = self.embedder.embed_texts(sentences, batch_size=32)
        return {
            "source_id": source_id,
            "sentences": sentences,
            "embeddings": np.asarray(embeddings, dtype=np.float32),
            "full_text": " ".join(sentences),
        }

    def verify_claim(self, claim: str, source_id: int, source_data: dict) -> ClaimResult:
        clean_claim = self.clean_claim(claim)
        if not clean_claim:
            return ClaimResult(
                claim=claim,
                source_id=source_id,
                best_similarity=0.0,
                semantic_supported=False,
                factual_supported=False,
                supported=False,
                factual_errors=["Empty claim"],
            )

        claim_embedding = np.asarray(
            self.embedder.embed_text(clean_claim),
            dtype=np.float32,
        )

        # Explicit L2 normalization so dot product = cosine similarity.
        claim_norm = np.linalg.norm(claim_embedding)

        if claim_norm > 0:
            claim_embedding = (
                claim_embedding / claim_norm
            )

        source_embeddings = source_data["embeddings"]

        source_norms = np.linalg.norm(
            source_embeddings,
            axis=1,
            keepdims=True,
        )

        source_norms = np.where(
            source_norms == 0,
            1.0,
            source_norms,
        )

        normalized_source_embeddings = (
            source_embeddings / source_norms
        )

        similarities = np.dot(
            normalized_source_embeddings,
            claim_embedding,
        )

        best_similarity = float(
            np.max(similarities)
        )

        semantic_supported = (
            best_similarity >= self.similarity_threshold
        )

        (
            factual_supported,
            claim_numbers,
            source_numbers,
            claim_dates,
            source_dates,
            claim_entities,
            source_entities,
            factual_errors,
        ) = self.check_factual_consistency(clean_claim, source_data["full_text"])

        supported = semantic_supported and factual_supported

        return ClaimResult(
            claim=claim,
            source_id=source_id,
            best_similarity=best_similarity,
            semantic_supported=semantic_supported,
            factual_supported=factual_supported,
            supported=supported,
            claim_numbers=claim_numbers,
            source_numbers=source_numbers,
            claim_dates=claim_dates,
            source_dates=source_dates,
            claim_entities=claim_entities,
            source_entities=source_entities,
            factual_errors=factual_errors,
        )

    def _citation_only_paragraph(self, paragraph: str) -> bool:
        return bool(self.extract_citations(paragraph)) and not self.clean_claim(paragraph)

    def validate(
        self,
        article_text: str,
        retrieved_articles: list,
        available_source_ids: list[int] | None = None,
        require_citations: bool = True,
    ) -> GroundingValidation:
        if not article_text:
            return GroundingValidation(is_grounded=False)

        source_articles = {}

        for article in retrieved_articles:
            if article is None:
                continue

            content = getattr(article, "content", None)

            if not content:
                continue

            # IMPORTANT:
            # Use the actual source_id from the retrieved article.
            #
            # Example:
            # Article ID 29 -> Source 29
            #
            # Do NOT enumerate sources as 1, 2, 3 because
            # Mistral citations use the actual article/source ID.

            source_id = getattr(article, "source_id", None)

            if source_id is None:
                source_id = getattr(article, "article_id", None)

            if source_id is None:
                continue

            source_articles[int(source_id)] = content


        valid_source_ids = (
            set(source_articles.keys())
            if available_source_ids is None
            else set(available_source_ids)
        )


        prepared_sources = {
            source_id: self.prepare_source(
                source_id,
                source_text,
            )
            for source_id, source_text in source_articles.items()
            if source_id in valid_source_ids
        }

        paragraphs = [
            paragraph.strip()
            for paragraph in article_text.splitlines()
            if paragraph.strip()
        ]

        # Collect article-level citations before processing paragraphs. If the
        # entire article cites exactly one valid source (often as a final
        # standalone '[Source 1]' line), that source is inherited by factual
        # paragraphs that do not repeat the citation.
        all_article_citations = set()
        for paragraph in paragraphs:
            all_article_citations.update(self.extract_citations(paragraph))

        valid_article_citations = all_article_citations & valid_source_ids
        invalid_article_citations = all_article_citations - valid_source_ids
        inherited_source_id = (
            next(iter(valid_article_citations))
            if len(valid_article_citations) == 1 and not invalid_article_citations
            else None
        )

        claim_results: list[ClaimResult] = []
        citation_errors: list[str] = []
        all_cited_source_ids = set(all_article_citations)

        for paragraph in paragraphs:
            citations = self.extract_citations(paragraph)

            # Ignore standalone citation markers such as a trailing '[Source 1]'.
            if self._citation_only_paragraph(paragraph):
                continue

            if not citations and inherited_source_id is not None:
                citations = [inherited_source_id]

            if not citations:
                if len(paragraph.split()) < 8:
                    continue
                if require_citations:
                    claim_results.append(
                        ClaimResult(
                            claim=paragraph,
                            source_id=-1,
                            best_similarity=0.0,
                            semantic_supported=False,
                            factual_supported=False,
                            supported=False,
                            claim_numbers=self.extract_numbers(paragraph),
                            claim_dates=self.extract_dates(paragraph),
                            claim_entities=self.extract_entities(paragraph),
                            factual_errors=["No source citation found"],
                        )
                    )
                    citation_errors.append("Generated paragraph has no source citation.")
                continue

            clean_paragraph = self.clean_claim(paragraph)
            claims = self.split_sentences(clean_paragraph) or [clean_paragraph]

            for claim in claims:
                for source_id in citations:
                    if source_id not in valid_source_ids:
                        citation_errors.append(
                            f"Invalid source citation: [Source {source_id}]"
                        )
                        claim_results.append(
                            ClaimResult(
                                claim=claim,
                                source_id=source_id,
                                best_similarity=0.0,
                                semantic_supported=False,
                                factual_supported=False,
                                supported=False,
                                claim_numbers=self.extract_numbers(claim),
                                claim_dates=self.extract_dates(claim),
                                claim_entities=self.extract_entities(claim),
                                factual_errors=["Referenced source is not available"],
                            )
                        )
                        continue

                    source_data = prepared_sources.get(source_id)
                    if source_data is None:
                        claim_results.append(
                            ClaimResult(
                                claim=claim,
                                source_id=source_id,
                                best_similarity=0.0,
                                semantic_supported=False,
                                factual_supported=False,
                                supported=False,
                                claim_numbers=self.extract_numbers(claim),
                                claim_dates=self.extract_dates(claim),
                                claim_entities=self.extract_entities(claim),
                                factual_errors=["Source content is unavailable"],
                            )
                        )
                        continue

                    claim_results.append(
                        self.verify_claim(
                            claim=claim,
                            source_id=source_id,
                            source_data=source_data,
                        )
                    )

        cited_source_ids = sorted(all_cited_source_ids)
        missing_source_ids = sorted(valid_source_ids - all_article_citations)
        invalid_source_ids = sorted(all_article_citations - valid_source_ids)

        supported_claim_results = [r for r in claim_results if r.supported]
        unsupported_claims = [r.claim for r in claim_results if not r.supported]

        grounding_errors = []
        for result in claim_results:
            if result.supported:
                continue
            if not result.semantic_supported:
                grounding_errors.append(f"Semantic grounding failed: {result.claim}")
            if not result.factual_supported:
                grounding_errors.append(f"Factual grounding failed: {result.claim}")

        total_claims = len(claim_results)
        supported_claims = len(supported_claim_results)

        is_grounded = (
            total_claims > 0
            and not unsupported_claims
            and not invalid_source_ids
            and (not require_citations or not citation_errors)
        )

        return GroundingValidation(
            is_grounded=is_grounded,
            total_claims=total_claims,
            supported_claims=supported_claims,
            unsupported_claims=unsupported_claims,
            claim_results=claim_results,
            supported_claim_results=supported_claim_results,
            cited_source_ids=cited_source_ids,
            missing_source_ids=missing_source_ids,
            invalid_source_ids=invalid_source_ids,
            citation_errors=citation_errors,
            grounding_errors=grounding_errors,
        )


if __name__ == "__main__":
    print("Grounding validator module loaded successfully.")
    print("Semantic threshold: 0.45")
    print("Citation handling: paragraph-level + single-source article-level inheritance")
    print("Date handling: calendar-date normalization")