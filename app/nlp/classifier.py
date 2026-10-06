"""
Northeast Sentinel
==================

Phase 5 — Editorial Article Classification

Phase 4 (app.nlp.relevance) is the authoritative Northeast
relevance engine.

Phase 5 does NOT replace Phase 4 relevance decisions.

Pipeline:

    Article
        ↓
    Generic-content filter
        ↓
    Phase 4 Northeast relevance
        ↓
    relevant == True?
        ↓
    Title-first editorial classification
        ↓
    Database category

Categories:

    Security & Strategic Affairs
    Development
    Regional News
    Society & Youth
    Sports & Achievements
    Not Relevant
"""

from __future__ import annotations

import re
from typing import Any

from app.database.database import SessionLocal
from app.database.models import Article
from app.nlp.relevance import NortheastRelevanceClassifier


# ============================================================
# CATEGORIES
# ============================================================

CATEGORIES = [
    "Security & Strategic Affairs",
    "Development",
    "Regional News",
    "Society & Youth",
    "Sports & Achievements",
    "Not Relevant",
]


# ============================================================
# GENERIC / NON-EDITORIAL CONTENT
# ============================================================

GENERIC_CONTENT_TERMS = {
    "sunscreen",
    "dry skin",
    "skin care",
    "skincare",
    "emi calculator",
    "home loan emi",
    "find a home",
    "buy a home",
    "rent a home",
    "real estate guide",
    "vps hosting",
    "futures trading",
    "option chain",
    "trading platform",
    "cme aurora",
    "colocation",
    "parenthood",
    "fertility",
    "loan calculator",
}


GENERIC_TITLE_PATTERNS = [
    "5 best ",
    "best ",
    "guide to ",
    "complete guide",
    "how long does it",
    "how to ",
    "calculator",
    "transform your",
]


# ============================================================
# EDITORIAL TITLE KEYWORDS
# ============================================================

# ------------------------------------------------------------
# SECURITY
# ------------------------------------------------------------

SECURITY_TITLE_TERMS = {
    "assam rifles",
    "indian army",
    "army",
    "military",
    "border security",
    "security forces",
    "insurgency",
    "insurgent",
    "militant",
    "militancy",
    "terrorism",
    "terrorist",
    "counter insurgency",
    "counter-insurgency",
    "narcotics",
    "heroin",
    "drug trafficking",
    "drug smuggling",
    "arms",
    "weapons",
    "smuggling",
}


# ------------------------------------------------------------
# DEVELOPMENT
# ------------------------------------------------------------

DEVELOPMENT_TITLE_TERMS = {
    "development",
    "industry",
    "industrial",
    "infrastructure",
    "railway",
    "railways",
    "railway station",
    "airport",
    "connectivity",
    "investment",
    "funding",
    "funds",
    "land bank",
    "land banks",
    "project",
    "projects",
    "farmers",
    "agriculture",
    "coffee",
    "modernisation",
    "modernization",
    "employment",
    "jobs",
    "economy",
    "economic",
}


# ------------------------------------------------------------
# SPORTS
# ------------------------------------------------------------

SPORTS_TITLE_TERMS = {
    "cricket",
    "odi",
    "t20",
    "test match",
    "football",
    "soccer",
    "hockey",
    "badminton",
    "boxing",
    "wrestling",
    "athletics",
    "athlete",
    "athletes",
    "marathon",
    "tournament",
    "championship",
    "champion",
    "medal",
    "gold medal",
    "silver medal",
    "bronze medal",
    "asian games",
    "olympic",
    "olympics",
    "golf",
    "shooting",
    "pitch",
    "runs",
    "wicket",
    "wickets",
    "bowling",
    "batting",
    "player",
    "players",
}


# ------------------------------------------------------------
# SOCIETY & YOUTH
# ------------------------------------------------------------

SOCIETY_TITLE_TERMS = {
    "society",
    "social",
    "community",
    "communities",
    "youth",
    "student",
    "students",
    "school",
    "schools",
    "college",
    "university",
    "women",
    "woman",
    "children",
    "child",
    "health",
    "healthcare",
    "civic",
    "garbage",
    "waste",
    "sanitation",
    "pollution",
    "environment",
    "culture",
    "cultural",
    "tribal",
    "residents",
    "citizens",
}


# ------------------------------------------------------------
# REGIONAL NEWS
# ------------------------------------------------------------

REGIONAL_TITLE_TERMS = {
    "bypoll",
    "by-election",
    "byelection",
    "election",
    "elections",
    "political",
    "politics",
    "chief minister",
    "assembly",
    "mla",
    "mp",
    "campaign",
    "government",
    "administration",
    "minister",
    "political party",
}


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Normalize text for keyword matching.
    """

    if value is None:
        return ""

    text = str(value).lower()

    text = text.replace(
        "-",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def contains_terms(
    text: str,
    terms: set[str] | list[str],
) -> list[str]:
    """
    Return matching terms using word-boundary matching.
    """

    matches = []

    for term in terms:

        normalized_term = normalize_text(
            term
        )

        if not normalized_term:
            continue

        pattern = (
            r"\b"
            + re.escape(
                normalized_term
            )
            + r"\b"
        )

        if re.search(
            pattern,
            text,
        ):
            matches.append(term)

    return matches


def article_text(
    article: Article,
) -> str:
    """
    Combine title, summary and article content.
    """

    title = normalize_text(
        getattr(
            article,
            "title",
            "",
        )
    )

    summary = normalize_text(
        getattr(
            article,
            "summary",
            "",
        )
    )

    content = normalize_text(
        getattr(
            article,
            "content",
            "",
        )
    )

    return " ".join(
        part
        for part in [
            title,
            summary,
            content,
        ]
        if part
    )


# ============================================================
# GENERIC CONTENT FILTER
# ============================================================

def is_generic_content(
    article: Article,
) -> bool:
    """
    Reject obvious generic, commercial, SEO, finance,
    lifestyle and technology articles.

    This is an additional safety filter.

    Phase 4 remains the authoritative Northeast relevance
    decision.
    """

    title = normalize_text(
        getattr(
            article,
            "title",
            "",
        )
    )

    if not title:
        return False

    # --------------------------------------------------------
    # Explicit generic topics
    # --------------------------------------------------------

    if contains_terms(
        title,
        GENERIC_CONTENT_TERMS,
    ):

        return True

    # --------------------------------------------------------
    # Generic SEO title patterns
    # --------------------------------------------------------

    for pattern in GENERIC_TITLE_PATTERNS:

        if title.startswith(
            normalize_text(pattern)
        ):

            return True

    return False


# ============================================================
# TITLE-FIRST CLASSIFICATION
# ============================================================

def classify_from_title(
    article: Article,
    phase4_result,
) -> str:
    """
    Classify the article using the title as the strongest
    editorial subject signal.

    Phase 4 remains responsible for determining whether the
    article belongs to the Northeast corpus.
    """

    title = normalize_text(
        getattr(
            article,
            "title",
            "",
        )
    )

    # ========================================================
    # 1. SPORTS
    # ========================================================
    #
    # This comes first intentionally.
    #
    # Example:
    #
    # "Guwahati's 800-run ODI..."
    #
    # contains sports language in the title and must not be
    # classified as Regional News merely because the article
    # contains political/general words.
    # ========================================================

    sports_hits = contains_terms(
        title,
        SPORTS_TITLE_TERMS,
    )

    if sports_hits:

        return (
            "Sports & Achievements"
        )

    # ========================================================
    # 2. SECURITY
    # ========================================================

    security_hits = contains_terms(
        title,
        SECURITY_TITLE_TERMS,
    )

    if security_hits:

        return (
            "Security & Strategic Affairs"
        )

    # ========================================================
    # 3. DEVELOPMENT
    # ========================================================

    development_hits = contains_terms(
        title,
        DEVELOPMENT_TITLE_TERMS,
    )

    if development_hits:

        return "Development"

    # ========================================================
    # 4. SOCIETY & YOUTH
    # ========================================================

    society_hits = contains_terms(
        title,
        SOCIETY_TITLE_TERMS,
    )

    if society_hits:

        return "Society & Youth"

    # ========================================================
    # 5. REGIONAL NEWS
    # ========================================================

    regional_hits = contains_terms(
        title,
        REGIONAL_TITLE_TERMS,
    )

    if regional_hits:

        return "Regional News"

    # ========================================================
    # 6. USE PHASE 4 CATEGORY AS FALLBACK
    # ========================================================

    phase4_category = getattr(
        phase4_result,
        "category",
        "Regional News",
    )

    if phase4_category in {
        "Security & Strategic Affairs",
        "Development",
        "Regional News",
        "Society & Youth",
        "Sports & Achievements",
    }:

        return phase4_category

    # --------------------------------------------------------
    # Safe fallback
    # --------------------------------------------------------

    return "Regional News"


# ============================================================
# CLASSIFY SINGLE ARTICLE
# ============================================================

def classify_article(
    article: Article,
    relevance_classifier: NortheastRelevanceClassifier,
) -> tuple[str, dict[str, Any]]:
    """
    Classify one article.

    IMPORTANT:

    Phase 4 is authoritative for Northeast relevance.

    We do NOT independently decide that an article is
    Northeast-relevant merely because it contains an
    organization such as AJP, AASU or NEC.
    """

    # --------------------------------------------------------
    # Article text
    # --------------------------------------------------------

    text = article_text(
        article
    )

    if not text:

        return (
            "Not Relevant",
            {
                "reason": (
                    "Article has no usable text."
                )
            },
        )

    # --------------------------------------------------------
    # Generic content filter
    # --------------------------------------------------------

    if is_generic_content(
        article
    ):

        return (
            "Not Relevant",
            {
                "reason": (
                    "Generic/non-editorial "
                    "content detected."
                )
            },
        )

    # --------------------------------------------------------
    # Phase 4 relevance
    # --------------------------------------------------------

    phase4_result = (
        relevance_classifier.classify(
            title=getattr(
                article,
                "title",
                "",
            ),
            content=getattr(
                article,
                "content",
                "",
            ),
        )
    )

    # ========================================================
    # AUTHORITATIVE RELEVANCE GATE
    # ========================================================
    #
    # This is the most important change.
    #
    # We trust Phase 4's `relevant` field.
    #
    # Therefore:
    #
    #     relevant=False
    #         ↓
    #     Not Relevant
    #
    # Even if:
    #
    #     AJP
    #     AASU
    #     NEC
    #     Kuki
    #
    # appears somewhere in the article.
    # ========================================================

    if not phase4_result.relevant:

        return (
            "Not Relevant",
            {
                "reason": (
                    phase4_result.reason
                ),

                "northeast_score": (
                    phase4_result.northeast_score
                ),

                "relevance_score": (
                    phase4_result.relevance_score
                ),

                "phase4_category": (
                    phase4_result.category
                ),

                "northeast_signals": (
                    phase4_result
                    .matched_northeast_terms
                ),
            },
        )

    # ========================================================
    # FINAL EDITORIAL CATEGORY
    # ========================================================

    category = classify_from_title(
        article,
        phase4_result,
    )

    # ========================================================
    # METADATA
    # ========================================================

    metadata = {
        "relevance_score": (
            phase4_result.relevance_score
        ),

        "northeast_score": (
            phase4_result.northeast_score
        ),

        "security_score": (
            phase4_result.security_score
        ),

        "development_score": (
            phase4_result.development_score
        ),

        "society_score": (
            phase4_result.society_score
        ),

        "sports_score": (
            phase4_result.sports_score
        ),

        "phase4_category": (
            phase4_result.category
        ),

        "northeast_signals": (
            phase4_result
            .matched_northeast_terms
        ),

        "theme_signals": (
            phase4_result
            .matched_theme_terms
        ),

        "reason": (
            phase4_result.reason
        ),
    }

    return (
        category,
        metadata,
    )


# ============================================================
# DATABASE CLASSIFICATION
# ============================================================

def classify_articles() -> int:
    """
    Classify all articles currently stored in SQLite.
    """

    session = SessionLocal()

    try:

        articles = (
            session
            .query(Article)
            .all()
        )

        print("=" * 70)

        print(
            "NORTHEAST SENTINEL — ARTICLE CLASSIFIER"
        )

        print("=" * 70)

        print()

        print(
            f"Articles found: "
            f"{len(articles)}"
        )

        print()

        # ----------------------------------------------------
        # Create ONE Phase 4 classifier
        # ----------------------------------------------------

        relevance_classifier = (
            NortheastRelevanceClassifier()
        )

        counts = {
            category: 0
            for category in CATEGORIES
        }

        classified = 0

        # ====================================================
        # PROCESS ARTICLES
        # ====================================================

        for article in articles:

            category, metadata = (
                classify_article(
                    article,
                    relevance_classifier,
                )
            )

            # ------------------------------------------------
            # Save category
            # ------------------------------------------------

            article.category = category

            counts[
                category
            ] = (
                counts.get(
                    category,
                    0,
                )
                + 1
            )

            classified += 1

            # ------------------------------------------------
            # Print article information
            # ------------------------------------------------

            print(
                "-" * 70
            )

            print(
                f"ARTICLE ID : "
                f"{article.id}"
            )

            print(
                f"Title      : "
                f"{article.title}"
            )

            print(
                f"Category   : "
                f"{category}"
            )

            # ------------------------------------------------
            # Print scores for relevant articles
            # ------------------------------------------------

            if metadata:

                score_parts = []

                score_mapping = [
                    (
                        "security_score",
                        "Security",
                    ),
                    (
                        "development_score",
                        "Development",
                    ),
                    (
                        "society_score",
                        "Society",
                    ),
                    (
                        "sports_score",
                        "Sports",
                    ),
                ]

                for (
                    key,
                    display_name,
                ) in score_mapping:

                    if key in metadata:

                        score_parts.append(
                            f"{display_name}="
                            f"{metadata[key]}"
                        )

                if score_parts:

                    print(
                        "Scores     : "
                        + ", ".join(
                            score_parts
                        )
                    )

                # --------------------------------------------
                # Northeast signals
                # --------------------------------------------

                signals = metadata.get(
                    "northeast_signals",
                    [],
                )

                if signals:

                    print(
                        "NE signals : "
                        + ", ".join(
                            signals
                        )
                    )

            else:

                print(
                    "Scores     : "
                    "No Northeast relevance detected"
                )

        # ====================================================
        # COMMIT
        # ====================================================

        session.commit()

        # ====================================================
        # SUMMARY
        # ====================================================

        print()

        print("=" * 70)

        print(
            "CLASSIFICATION SUMMARY"
        )

        print("=" * 70)

        for category in CATEGORIES:

            print(
                f"{category:<32} : "
                f"{counts.get(category, 0)}"
            )

        print()

        print(
            f"Successfully classified: "
            f"{classified}"
        )

        return classified

    except Exception:

        session.rollback()

        raise

    finally:

        session.close()


# ============================================================
# ENTRY POINT
# ============================================================

def main() -> None:
    """
    Command-line entry point.
    """

    classify_articles()


if __name__ == "__main__":
    main()