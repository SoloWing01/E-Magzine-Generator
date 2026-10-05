class ArticleValidator:

    MIN_CONTENT_LENGTH = 300

    @classmethod
    def validate(cls, article: dict) -> tuple[bool, list[str]]:

        errors = []

        if not article.get("title"):
            errors.append("Missing title")

        if not article.get("url"):
            errors.append("Missing URL")

        if not article.get("source"):
            errors.append("Missing source")

        if not article.get("published_date"):
            errors.append("Missing publication date")

        content = article.get("content", "")

        if not content:
            errors.append("Missing content")

        elif len(content) < cls.MIN_CONTENT_LENGTH:
            errors.append(
                f"Content too short ({len(content)} characters)"
            )

        return len(errors) == 0, errors