import re
from dataclasses import dataclass, asdict


@dataclass
class RelevanceResult:
    relevant: bool
    relevance_score: int
    category: str
    northeast_score: int
    security_score: int
    development_score: int
    society_score: int
    sports_score: int
    matched_northeast_terms: list[str]
    matched_theme_terms: list[str]
    reason: str

    def to_dict(self):
        return asdict(self)


class NortheastRelevanceClassifier:

    # =========================================================
    # NORTHEAST STATES
    # =========================================================

    NORTHEAST_STATES = {
        "assam": 8,
        "arunachal pradesh": 8,
        "manipur": 8,
        "meghalaya": 8,
        "mizoram": 8,
        "nagaland": 8,
        "tripura": 8,
        "sikkim": 8,
    }

    # =========================================================
    # IMPORTANT NORTHEAST LOCATIONS / ENTITIES
    # =========================================================

    NORTHEAST_ENTITIES = {
        "guwahati": 6,
        "dibrugarh": 5,
        "silchar": 5,
        "nagaon": 6,
        "lumding": 6,
        "tezpur": 5,
        "jorhat": 5,
        "tinsukia": 5,
        "dimapur": 6,
        "kohima": 6,
        "aizawl": 6,
        "champhai": 6,
        "imphal": 6,
        "shillong": 6,
        "tura": 5,
        "gangtok": 6,
        "itanagar": 6,
        "agartala": 6,
        "mokokchung": 5,
        "mon district": 5,
        "kuki": 5,
        "mizo": 5,
        "naga": 5,
        "bodo": 5,
        "north eastern council": 7,
        "nec": 5,
        "assam rifles": 8,
    }

    # =========================================================
    # NORTHEAST / REGIONAL TERMS
    # =========================================================

    NORTHEAST_TERMS = {
        "northeast": 7,
        "north east": 7,
        "north-eastern": 7,
        "north eastern": 7,
        "seven sisters": 7,
        "eight northeastern states": 8,
        "eight north eastern states": 8,
        "india-myanmar border": 8,
        "india-bangladesh border": 8,
        "myanmar border": 7,
        "bangladesh border": 7,
        "northeastern region": 7,
    }

    # =========================================================
    # SECURITY
    # =========================================================

    SECURITY_TERMS = {
        "indian army": 10,
        "army": 5,
        "assam rifles": 10,
        "border security": 8,
        "border": 3,
        "military": 6,
        "security forces": 7,
        "armed forces": 7,
        "insurgency": 8,
        "counter-insurgency": 9,
        "counter insurgency": 9,
        "militant": 7,
        "militancy": 7,
        "terrorism": 7,
        "terrorist": 7,
        "ceasefire": 6,
        "drug trafficking": 7,
        "drug-smuggling": 7,
        "drug smuggling": 7,
        "narcotics": 6,
        "heroin": 4,
        "smuggling": 5,
        "international border": 7,
        "infiltration": 7,
        "air force": 5,
        "iaf": 5,
        "defence": 5,
        "defense": 5,
        "strategic": 5,
        "china border": 8,
        "india-china": 8,
        "lac": 6,
    }

    # =========================================================
    # DEVELOPMENT
    # =========================================================

    DEVELOPMENT_TERMS = {
        "infrastructure": 6,
        "development": 5,
        "investment": 4,
        "funding": 5,
        "funds": 4,
        "government scheme": 5,
        "scheme": 3,
        "capital investment": 7,
        "roads": 4,
        "railway": 5,
        "railways": 5,
        "airport": 4,
        "connectivity": 6,
        "industry": 5,
        "industrial": 5,
        "land bank": 6,
        "land banks": 6,
        "modernisation": 5,
        "modernization": 5,
        "agriculture": 5,
        "farmers": 5,
        "coffee": 4,
        "education": 4,
        "healthcare": 4,
        "health": 3,
        "employment": 4,
        "jobs": 4,
        "economic": 4,
        "economy": 4,
    }

    # =========================================================
    # SOCIETY / YOUTH
    # =========================================================

    SOCIETY_TERMS = {
        "youth": 7,
        "students": 5,
        "student": 5,
        "society": 4,
        "community": 5,
        "women": 5,
        "woman": 5,
        "children": 4,
        "school": 4,
        "college": 4,
        "university": 4,
        "civic": 5,
        "sanitation": 5,
        "garbage": 4,
        "citizens": 4,
        "civil society": 6,
        "journalist": 4,
        "journalists": 4,
    }

    # =========================================================
    # SPORTS
    # =========================================================

    SPORTS_TERMS = {
        "sports": 5,
        "sport": 4,
        "cricket": 6,
        "football": 6,
        "hockey": 6,
        "badminton": 6,
        "boxing": 6,
        "wrestling": 6,
        "athletics": 6,
        "marathon": 6,
        "golf": 5,
        "athlete": 5,
        "athletes": 5,
        "medal": 5,
        "gold medal": 7,
        "silver medal": 7,
        "bronze medal": 7,
        "asian games": 7,
        "olympics": 7,
    }

    # =========================================================
    # IRRELEVANT TERMS
    # =========================================================

    IRRELEVANT_TERMS = {
        "sunscreen": 8,
        "vps hosting": 8,
        "trading platform": 7,
        "option chain": 7,
        "emi calculator": 7,
        "home loan calculator": 7,
        "parenthood": 6,
        "fertility": 6,
    }

    # =========================================================
    # TEXT NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalise(text: str) -> str:
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    # =========================================================
    # TERM MATCHING
    # =========================================================

    def _match_terms(
        self,
        text: str,
        terms: dict[str, int],
    ) -> tuple[int, list[str]]:

        score = 0
        matched = []

        for term, weight in terms.items():

            pattern = r"\b" + re.escape(term) + r"\b"

            if re.search(pattern, text):
                score += weight
                matched.append(term)

        return score, matched

    # =========================================================
    # TITLE MATCHING
    # =========================================================

    def _match_title_terms(
        self,
        title: str,
        terms: dict[str, int],
    ) -> tuple[int, list[str]]:

        score = 0
        matched = []

        for term, weight in terms.items():

            pattern = r"\b" + re.escape(term) + r"\b"

            if re.search(pattern, title):
                # Title matches are stronger evidence.
                score += weight * 2
                matched.append(term)

        return score, matched

        # =========================================================
    # THEME CLASSIFICATION
    # =========================================================

    def _classify_theme(
        self,
        title: str,
        content: str,
        security_terms: list[str],
        development_terms: list[str],
        society_terms: list[str],
        sports_terms: list[str],
    ) -> tuple[str, dict[str, int], list[str]]:

        title = self._normalise(title)
        content = self._normalise(content)

        theme_definitions = {
            "Security & Strategic Affairs": self.SECURITY_TERMS,
            "Development": self.DEVELOPMENT_TERMS,
            "Society & Youth": self.SOCIETY_TERMS,
            "Sports & Achievements": self.SPORTS_TERMS,
        }

        body_scores = {}
        title_scores = {}

        # Calculate theme scores separately for title and body.
        for category, terms in theme_definitions.items():

            body_score, _ = self._match_terms(
                content,
                terms,
            )

            title_score, _ = self._match_title_terms(
                title,
                terms,
            )

            body_scores[category] = body_score
            title_scores[category] = title_score

        # -----------------------------------------------------
        # TITLE HAS GREATER IMPORTANCE
        # -----------------------------------------------------
        #
        # The headline usually describes the actual subject.
        # Body terms may describe secondary/contextual topics.
        #
        # Example:
        #
        # "3,500 runners, IAF firepower mark Sekhon Marathon"
        #
        # Sports appears in the title.
        # IAF/security appears mainly as context.
        #
        # Therefore Sports should win.

        final_scores = {}

        for category in theme_definitions:

            title_score = title_scores[category]
            body_score = body_scores[category]

            final_scores[category] = (
                title_score * 2
                + body_score
            )

        # -----------------------------------------------------
        # SPORTS TITLE BOOST
        # -----------------------------------------------------

        sports_title_terms = [
            "marathon",
            "cricket",
            "football",
            "hockey",
            "badminton",
            "boxing",
            "wrestling",
            "athletics",
            "golf",
            "sports",
            "sport",
            "athlete",
            "athletes",
            "medal",
            "gold",
            "silver",
            "bronze",
            "asian games",
            "olympics",
        ]

        sports_title_hits = [
            term
            for term in sports_title_terms
            if re.search(
                r"\b" + re.escape(term) + r"\b",
                title,
            )
        ]

        if sports_title_hits:

            final_scores["Sports & Achievements"] += (
                len(sports_title_hits) * 5
            )

        # -----------------------------------------------------
        # SECURITY TITLE BOOST
        # -----------------------------------------------------

        security_title_terms = [
            "army",
            "assam rifles",
            "military",
            "border",
            "security",
            "insurgency",
            "militant",
            "militancy",
            "terrorism",
            "terrorist",
            "counter-insurgency",
            "counter insurgency",
            "defence",
            "defense",
            "iaf",
            "air force",
            "india-myanmar",
            "india-bangladesh",
            "china border",
        ]

        security_title_hits = [
            term
            for term in security_title_terms
            if re.search(
                r"\b" + re.escape(term) + r"\b",
                title,
            )
        ]

        if security_title_hits:

            final_scores["Security & Strategic Affairs"] += (
                len(security_title_hits) * 5
            )

        # -----------------------------------------------------
        # DEVELOPMENT TITLE BOOST
        # -----------------------------------------------------

        development_title_terms = [
            "development",
            "industry",
            "industrial",
            "infrastructure",
            "railway",
            "railways",
            "airport",
            "connectivity",
            "investment",
            "funding",
            "funds",
            "scheme",
            "farmers",
            "agriculture",
            "modernisation",
            "modernization",
            "economy",
            "economic",
            "jobs",
            "employment",
        ]

        development_title_hits = [
            term
            for term in development_title_terms
            if re.search(
                r"\b" + re.escape(term) + r"\b",
                title,
            )
        ]

        if development_title_hits:

            final_scores["Development"] += (
                len(development_title_hits) * 5
            )

        # -----------------------------------------------------
        # SOCIETY TITLE BOOST
        # -----------------------------------------------------

        society_title_terms = [
            "youth",
            "students",
            "student",
            "school",
            "college",
            "university",
            "women",
            "woman",
            "children",
            "community",
            "civic",
            "citizens",
            "journalist",
            "journalists",
            "society",
        ]

        society_title_hits = [
            term
            for term in society_title_terms
            if re.search(
                r"\b" + re.escape(term) + r"\b",
                title,
            )
        ]

        if society_title_hits:

            final_scores["Society & Youth"] += (
                len(society_title_hits) * 5
            )

        # -----------------------------------------------------
        # SELECT PRIMARY CATEGORY
        # -----------------------------------------------------

        category = max(
            final_scores,
            key=final_scores.get,
        )

        # -----------------------------------------------------
        # ALL THEME SCORES ARE WEAK
        # -----------------------------------------------------

        if final_scores[category] < 10:

            category = "Regional News"

        matched_terms = {
            "Security & Strategic Affairs": security_terms,
            "Development": development_terms,
            "Society & Youth": society_terms,
            "Sports & Achievements": sports_terms,
            "Regional News": (
                security_terms
                + development_terms
                + society_terms
                + sports_terms
            ),
        }

        return (
            category,
            final_scores,
            matched_terms[category],
        )

    # =========================================================
    # MAIN CLASSIFIER
    # =========================================================

    def classify(
        self,
        title: str,
        content: str,
    ) -> RelevanceResult:

        title = title or ""
        content = content or ""

        title_text = self._normalise(title)
        content_text = self._normalise(content)

        # Title is intentionally repeated here.
        #
        # This gives important headline information more weight
        # without completely ignoring article body evidence.

        combined_text = self._normalise(
            f"{title} {title} {content}"
        )

        # =====================================================
        # 1. NORTHEAST EVIDENCE
        # =====================================================

        state_score, matched_states = self._match_terms(
            combined_text,
            self.NORTHEAST_STATES,
        )

        entity_score, matched_entities = self._match_terms(
            combined_text,
            self.NORTHEAST_ENTITIES,
        )

        regional_score, matched_regional = self._match_terms(
            combined_text,
            self.NORTHEAST_TERMS,
        )

        # Stronger evidence when Northeast information appears
        # directly in the headline.

        title_state_score, title_states = self._match_title_terms(
            title_text,
            self.NORTHEAST_STATES,
        )

        title_entity_score, title_entities = self._match_title_terms(
            title_text,
            self.NORTHEAST_ENTITIES,
        )

        title_regional_score, title_regional = self._match_title_terms(
            title_text,
            self.NORTHEAST_TERMS,
        )

        northeast_score = (
            state_score
            + entity_score
            + regional_score
            + title_state_score
            + title_entity_score
            + title_regional_score
        )

        northeast_score = min(
            100,
            northeast_score,
        )

        matched_northeast_terms = list(
            dict.fromkeys(
                matched_states
                + matched_entities
                + matched_regional
                + title_states
                + title_entities
                + title_regional
            )
        )

        # =====================================================
        # 2. THEME SCORES
        # =====================================================

        security_score, security_terms = self._match_terms(
            combined_text,
            self.SECURITY_TERMS,
        )

        development_score, development_terms = self._match_terms(
            combined_text,
            self.DEVELOPMENT_TERMS,
        )

        society_score, society_terms = self._match_terms(
            combined_text,
            self.SOCIETY_TERMS,
        )

        sports_score, sports_terms = self._match_terms(
            combined_text,
            self.SPORTS_TERMS,
        )

        # =====================================================
        # 3. IRRELEVANT CONTENT
        # =====================================================

        irrelevant_score, irrelevant_terms = self._match_terms(
            combined_text,
            self.IRRELEVANT_TERMS,
        )

        # =====================================================
        # 4. NO NORTHEAST CONNECTION
        # =====================================================

        if northeast_score == 0:

            return RelevanceResult(
                relevant=False,
                relevance_score=0,
                category="Not Relevant",
                northeast_score=0,
                security_score=security_score,
                development_score=development_score,
                society_score=society_score,
                sports_score=sports_score,
                matched_northeast_terms=[],
                matched_theme_terms=[],
                reason=(
                    "No clear Northeast connection found."
                ),
            )

        # =====================================================
        # 5. CONTEXT-AWARE THEME CLASSIFICATION
        # =====================================================

        category, theme_scores, matched_theme_terms = (
            self._classify_theme(
                title=title_text,
                content=content_text,
                security_terms=security_terms,
                development_terms=development_terms,
                society_terms=society_terms,
                sports_terms=sports_terms,
            )
        )

        highest_theme_score = max(
            theme_scores.values()
        )

        # =====================================================
        # 6. SPORTS RULE
        # =====================================================

        # A national sports article should not qualify merely
        # because it contains sports vocabulary.

        if category == "Sports & Achievements":

            # A direct Northeast sports article normally has
            # either a strong location/entity in the title or
            # multiple Northeast signals.

            title_has_ne = bool(
                title_states
                or title_entities
                or title_regional
            )

            strong_ne_context = (
                northeast_score >= 8
            )

            if not title_has_ne and not strong_ne_context:

                return RelevanceResult(
                    relevant=False,
                    relevance_score=0,
                    category="Not Relevant",
                    northeast_score=northeast_score,
                    security_score=security_score,
                    development_score=development_score,
                    society_score=society_score,
                    sports_score=sports_score,
                    matched_northeast_terms=matched_northeast_terms,
                    matched_theme_terms=sports_terms,
                    reason=(
                        "Sports article lacks a sufficiently "
                        "strong Northeast connection."
                    ),
                )

        # =====================================================
        # 7. SECURITY RULE
        # =====================================================

        if category == "Security & Strategic Affairs":

            title_has_ne = bool(
                title_states
                or title_entities
                or title_regional
            )

            strong_ne_context = (
                northeast_score >= 8
            )

            if not title_has_ne and not strong_ne_context:

                return RelevanceResult(
                    relevant=False,
                    relevance_score=0,
                    category="Not Relevant",
                    northeast_score=northeast_score,
                    security_score=security_score,
                    development_score=development_score,
                    society_score=society_score,
                    sports_score=sports_score,
                    matched_northeast_terms=matched_northeast_terms,
                    matched_theme_terms=security_terms,
                    reason=(
                        "Security article lacks a sufficiently "
                        "strong Northeast connection."
                    ),
                )


        # =====================================================
        # 8. FINAL RELEVANCE SCORE
        # =====================================================

        # The old formula penalised moderate but legitimate
        # Northeast stories too heavily.
        #
        # New formula:
        #
        #   60% Northeast evidence
        #   40% theme evidence
        #
        # Both are normalized before combining.

        normalized_ne = min(
            100,
            northeast_score,
        )

        normalized_theme = min(
            100,
            highest_theme_score * 2,
        )

        final_score = (
            normalized_ne * 0.60
            + normalized_theme * 0.40
        )

        # Apply irrelevant penalty only after establishing
        # Northeast relevance.

        final_score -= min(
            15,
            irrelevant_score,
        )

        final_score = max(
            0,
            min(
                100,
                round(final_score),
            ),
        )

        # =====================================================
        # 9. FINAL DECISION
        # =====================================================

        # Strong Northeast signal + meaningful theme evidence.

        relevant = (
            northeast_score >= 8
            and highest_theme_score >= 5
            and final_score >= 20
        )

        # A direct Northeast location/entity in the title is
        # strong evidence even when the calculated score is
        # relatively modest.

        title_has_ne = bool(
            title_states
            or title_entities
            or title_regional
        )

        if (
            title_has_ne
            and northeast_score >= 8
            and highest_theme_score >= 5
            and irrelevant_score < 10
        ):
            relevant = True

        # =====================================================
        # 10. REASON
        # =====================================================

        if relevant:

            ne_preview = ", ".join(
                matched_northeast_terms[:6]
            )

            reason = (
                f"Northeast connection detected through "
                f"{ne_preview}. "
                f"Primary theme: {category}."
            )

        else:

            reason = (
                "Article has some Northeast connection but "
                "does not meet the minimum relevance threshold."
            )

        return RelevanceResult(
            relevant=relevant,
            relevance_score=final_score,
            category=category if relevant else "Not Relevant",
            northeast_score=northeast_score,
            security_score=security_score,
            development_score=development_score,
            society_score=society_score,
            sports_score=sports_score,
            matched_northeast_terms=matched_northeast_terms,
            matched_theme_terms=matched_theme_terms,
            reason=reason,
        )


# =============================================================
# CONVENIENCE FUNCTION
# =============================================================

classifier = NortheastRelevanceClassifier()


def classify_article(
    title: str,
    content: str,
) -> dict:

    result = classifier.classify(
        title=title,
        content=content,
    )

    return result.to_dict()