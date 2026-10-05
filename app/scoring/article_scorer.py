from datetime import datetime
from app.config.settings import settings


class ArticleScorer:
    """
    Scores already-relevant articles for editorial priority.

    Relevance and scoring are separate:
    - Relevance = should this article enter the magazine pipeline?
    - Score = how important/useful is this article compared with other
              relevant articles?
    """

    WEIGHTS = {
        "northeast_relevance": 0.30,
        "theme_relevance": 0.25,
        "security_relevance": 0.15,
        "freshness": 0.10,
        "source_quality": 0.10,
        "content_quality": 0.10,
    }

    SOURCE_SCORES = {
        "The Assam Tribune": 90,
    }

    SECURITY_TERMS = [
        "army",
        "indian army",
        "assam rifles",
        "military",
        "defence",
        "defense",
        "border",
        "border security",
        "india-myanmar border",
        "myanmar border",
        "drug trafficking",
        "drug-smuggling",
        "narcotics",
        "heroin",
        "insurgency",
        "security forces",
        "armed forces",
        "air force",
        "iaf",
        "bsf",
        "paramilitary",
        "terrorism",
        "counter-insurgency",
    ]

    def __init__(self):
        self.start_date = datetime.strptime(
            settings.START_DATE,
            "%Y-%m-%d"
        )

        self.end_date = datetime.strptime(
            settings.END_DATE,
            "%Y-%m-%d"
        )

    @staticmethod
    def _normalise(text: str) -> str:
        return " ".join((text or "").lower().split())

    def _count_term_matches(
        self,
        text: str,
        terms: list[str]
    ) -> int:
        text = self._normalise(text)

        return sum(
            1
            for term in terms
            if term.lower() in text
        )

    def _normalise_score(
        self,
        score: float,
        maximum: float
    ) -> float:
        if maximum <= 0:
            return 0.0

        return min(100.0, (score / maximum) * 100)

    def _freshness_score(
        self,
        published_date: datetime
    ) -> float:

        if published_date is None:
            return 0.0

        if published_date < self.start_date:
            return 0.0

        if published_date > self.end_date:
            published_date = self.end_date

        total_days = (
            self.end_date - self.start_date
        ).days

        age_days = (
            self.end_date - published_date
        ).days

        if total_days <= 0:
            return 100.0

        score = 100 - (
            age_days / total_days
        ) * 100

        return max(0.0, min(100.0, score))

    def _source_quality_score(
        self,
        source: str
    ) -> float:

        if not source:
            return 0.0

        return self.SOURCE_SCORES.get(
            source,
            60
        )

    def _content_quality_score(
        self,
        title: str,
        content: str
    ) -> float:

        title = title or ""
        content = content or ""

        score = 0.0

        # Title quality
        if len(title) >= 30:
            score += 20
        elif len(title) >= 15:
            score += 10

        # Content length
        content_length = len(content)

        if content_length >= 3000:
            score += 40
        elif content_length >= 1500:
            score += 30
        elif content_length >= 800:
            score += 20
        elif content_length >= 300:
            score += 10

        # Paragraph structure
        paragraphs = [
            p.strip()
            for p in content.split("\n")
            if p.strip()
        ]

        if len(paragraphs) >= 8:
            score += 20
        elif len(paragraphs) >= 5:
            score += 15
        elif len(paragraphs) >= 3:
            score += 10

        # Avoid extremely short articles
        if content_length < 300:
            return 0.0

        return min(100.0, score)

    def _security_relevance_score(
        self,
        title: str,
        content: str,
        category: str
    ) -> float:

        text = f"{title} {content}"

        matches = self._count_term_matches(
            text,
            self.SECURITY_TERMS
        )

        score = min(100, matches * 15)

        # Security & Strategic Affairs gets additional importance
        if category == "Security & Strategic Affairs":
            score += 40

        return min(100.0, score)

    def score_article(
        self,
        article: dict,
        classification: dict
    ) -> dict:

        title = article.get("title", "")
        content = article.get("content", "")
        source = article.get("source", "")
        published_date = article.get("published_date")

        category = classification.get(
            "category",
            "Regional News"
        )

        northeast_score = classification.get(
            "northeast_score",
            0
        )

        theme_scores = {
    "Security & Strategic Affairs": classification.get(
        "security_score",
        0
    ),
    "Development": classification.get(
        "development_score",
        0
    ),
    "Society & Youth": classification.get(
        "society_score",
        0
    ),
    "Sports & Achievements": classification.get(
        "sports_score",
        0
    ),
}

        # ----------------------------------------
        # 1. Northeast relevance
        # ----------------------------------------

        northeast_relevance = min(
            100.0,
            float(northeast_score)
        )

        # ----------------------------------------
        # 2. Theme relevance
        # ----------------------------------------

        highest_theme_score = max(
    theme_scores.values(),
    default=0
)

        theme_relevance = self._normalise_score(
            highest_theme_score,
            50
        )

        # ----------------------------------------
        # 3. Security / Army relevance
        # ----------------------------------------

        security_relevance = (
            self._security_relevance_score(
                title,
                content,
                category
            )
        )

        # ----------------------------------------
        # 4. Freshness
        # ----------------------------------------

        freshness = self._freshness_score(
            published_date
        )

        # ----------------------------------------
        # 5. Source quality
        # ----------------------------------------

        source_quality = self._source_quality_score(
            source
        )

        # ----------------------------------------
        # 6. Content quality
        # ----------------------------------------

        content_quality = self._content_quality_score(
            title,
            content
        )

        # ----------------------------------------
        # Final weighted score
        # ----------------------------------------

        final_score = (
            northeast_relevance
            * self.WEIGHTS["northeast_relevance"]
            +
            theme_relevance
            * self.WEIGHTS["theme_relevance"]
            +
            security_relevance
            * self.WEIGHTS["security_relevance"]
            +
            freshness
            * self.WEIGHTS["freshness"]
            +
            source_quality
            * self.WEIGHTS["source_quality"]
            +
            content_quality
            * self.WEIGHTS["content_quality"]
        )

        final_score = round(
            min(100.0, max(0.0, final_score)),
            2
        )

        return {
            "article_id": article.get("id"),
            "title": title,
            "source": source,
            "published_date": published_date,
            "category": category,

            "northeast_relevance": round(
                northeast_relevance,
                2
            ),

            "theme_relevance": round(
                theme_relevance,
                2
            ),

            "security_relevance": round(
                security_relevance,
                2
            ),

            "freshness": round(
                freshness,
                2
            ),

            "source_quality": round(
                source_quality,
                2
            ),

            "content_quality": round(
                content_quality,
                2
            ),

            "final_score": final_score,
        }