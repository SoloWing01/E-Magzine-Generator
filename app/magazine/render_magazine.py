from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.magazine.page_builder import MagazinePageBuilder


class MagazineRenderer:
    """Phase 15 HTML renderer for the upgraded magazine composition engine."""

    TARGET_PAGES = 50

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]

        self.output_dir = Path(
            __import__(
                "app.config.settings",
                fromlist=["settings"],
            ).settings.OUTPUT_DIR
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.magazine_json = (
            self.output_dir / "magazine_data.json"
        )

        self.html_output = (
            self.output_dir
            / "northeast_sentinel_magazine.html"
        )

        self.template_dir = (
            self.project_root
            / "app"
            / "magazine"
            / "templates"
        )

        self.template_name = "magazine.html"

        self.env = Environment(
            loader=FileSystemLoader(
                str(self.template_dir)
            ),
            autoescape=select_autoescape(
                enabled_extensions=(
                    "html",
                    "xml",
                )
            ),
        )

    # ============================================================
    # MARKDOWN CLEANING
    # ============================================================

    @staticmethod
    def clean_markdown_formatting(
        text: Any,
    ) -> Any:
        """
        Remove Markdown formatting markers that should not
        appear as literal characters in the magazine.

        Example:

            **Indian Army**

        becomes:

            Indian Army

        Only Markdown markers are removed.
        The actual text remains unchanged.
        """

        if text is None:
            return text

        if not isinstance(text, str):
            return text

        # Remove Markdown bold markers.
        #
        # **Important text**
        #        ↓
        # Important text
        text = text.replace(
            "**",
            "",
        )

        return text

    # ============================================================
    # ARTICLE ID
    # ============================================================

    @staticmethod
    def get_article_id(
        article: dict[str, Any],
    ) -> str | None:

        for field in (
            "article_id",
            "id",
            "articleId",
            "source_id",
        ):

            value = article.get(field)

            if value is not None:
                return str(value)

        return None

    # ============================================================
    # FIRST VALUE
    # ============================================================

    @staticmethod
    def first_value(
        data: dict[str, Any],
        fields: tuple[str, ...],
        default: Any = "",
    ) -> Any:

        for field in fields:

            value = data.get(field)

            if value is not None:

                if isinstance(
                    value,
                    str,
                ):

                    if value.strip():
                        return value

                else:
                    return value

        return default

    # ============================================================
    # BUILD MAGAZINE
    # ============================================================

    def build_magazine(
        self,
    ) -> dict[str, Any]:

        print(
            "\n" + "=" * 70
        )

        print(
            "PHASE 15 — MAGAZINE HTML RENDERER"
        )

        print(
            "=" * 70
        )

        MagazinePageBuilder().build()

        if not self.magazine_json.exists():

            raise FileNotFoundError(
                "Magazine data file was not created: "
                f"{self.magazine_json}"
            )

        with self.magazine_json.open(
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    # ============================================================
    # VALIDATE MAGAZINE STRUCTURE
    # ============================================================

    def validate_magazine_structure(
        self,
        magazine: dict[str, Any],
    ) -> None:

        required = {
            "metadata",
            "toc",
            "sections",
            "charts",
            "articles",
            "page_plan",
            "validation",
        }

        missing = sorted(
            required - set(magazine)
        )

        if missing:

            raise ValueError(
                "Missing keys in magazine_data.json: "
                + ", ".join(missing)
            )

        if not isinstance(
            magazine["articles"],
            list,
        ):

            raise ValueError(
                "magazine['articles'] must be a list."
            )

        if not isinstance(
            magazine["page_plan"],
            list,
        ):

            raise ValueError(
                "magazine['page_plan'] must be a list."
            )

        if len(
            magazine["page_plan"]
        ) != self.TARGET_PAGES:

            raise ValueError(
                f"Expected "
                f"{self.TARGET_PAGES} "
                f"logical pages, "
                f"found "
                f"{len(magazine['page_plan'])}."
            )

        if not magazine["articles"]:

            raise ValueError(
                "No article records were found."
            )

    # ============================================================
    # ARTICLE LOOKUP
    # ============================================================

    def build_article_lookup(
        self,
        magazine: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:

        lookup = {}

        for article in magazine.get(
            "articles",
            [],
        ):

            if not isinstance(
                article,
                dict,
            ):
                continue

            article_id = (
                self.get_article_id(
                    article
                )
            )

            if article_id is not None:

                lookup[
                    article_id
                ] = article

        if not lookup:

            raise ValueError(
                "Article lookup is empty."
            )

        return lookup

    # ============================================================
    # ASSET PATH HANDLING
    # ============================================================

    @staticmethod
    def html_asset_path(
        path: Any,
    ) -> Any:

        if not path:
            return path

        path = str(path).replace(
            "\\",
            "/",
        )

        # Already relative to data/output/
        if path.startswith(
            "../"
        ):

            return path

        # Project-relative paths:
        #
        # data/charts/example.png
        #       ↓
        # ../charts/example.png
        #
        # data/images/example.jpg
        #       ↓
        # ../images/example.jpg

        if path.startswith(
            "data/"
        ):

            return (
                "../"
                + path[
                    len("data/") :
                ]
            )

        return path
    @staticmethod
    def clean_markdown_formatting(
        text: Any,
    ) -> Any:
        """
        Clean formatting markers from generated magazine content.

        Removes:
            **bold**
            [Source 29]
            [Source 1]
            [Source 123]

        while preserving the actual article text.
        """

        if text is None:
            return text

        if not isinstance(text, str):
            return text

        # --------------------------------------------------------
        # Remove Markdown bold markers
        #
        # **Indian Army**
        #        ↓
        # Indian Army
        # --------------------------------------------------------

        text = text.replace(
            "**",
            "",
        )

        # --------------------------------------------------------
        # Remove inline source markers
        #
        # [Source 29]
        # [Source 1]
        # [Source 123]
        #
        #        ↓
        #
        # removed completely
        # --------------------------------------------------------

        text = re.sub(
            r"\[\s*Source\s+\d+\s*\]",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # --------------------------------------------------------
        # Clean spaces left behind after removing citations
        # --------------------------------------------------------

        text = re.sub(
            r"[ \t]{2,}",
            " ",
            text,
        )

        # Avoid spaces before punctuation
        text = re.sub(
            r"\s+([,.!?;:])",
            r"\1",
            text,
        )

        return text
    # ============================================================
    # ARTICLE PAGE PREPARATION
    # ============================================================

    def prepare_article_pages(
        self,
        magazine: dict[str, Any],
    ) -> list[dict[str, Any]]:

        lookup = (
            self.build_article_lookup(
                magazine
            )
        )

        prepared_pages = []
        unresolved = []

        for page in magazine.get(
            "page_plan",
            [],
        ):

            prepared = dict(page)

            # ----------------------------------------------------
            # Non-article page
            # ----------------------------------------------------

            if prepared.get(
                "type"
            ) != "article":

                prepared_pages.append(
                    prepared
                )

                continue

            # ----------------------------------------------------
            # Find article
            # ----------------------------------------------------

            article_id = prepared.get(
                "article_id",
                prepared.get(
                    "id"
                ),
            )

            article = (
                lookup.get(
                    str(article_id)
                )
                if article_id is not None
                else None
            )

            if article is None:

                unresolved.append(
                    {
                        "page": prepared.get(
                            "page_number"
                        ),
                        "article_id": article_id,
                    }
                )

                continue

            # ----------------------------------------------------
            # Article reference
            # ----------------------------------------------------

            prepared["article"] = article

            prepared["article_id"] = (
                self.get_article_id(
                    article
                )
                or str(article_id)
            )

            # ----------------------------------------------------
            # Article title
            # ----------------------------------------------------

            prepared["article_title"] = (
                self.first_value(
                    article,
                    (
                        "title",
                        "headline",
                        "article_title",
                    ),
                    prepared.get(
                        "title",
                        "",
                    ),
                )
            )

            prepared["article_title"] = (
                self.clean_markdown_formatting(
                    prepared["article_title"]
                )
            )

            # ----------------------------------------------------
            # Article category
            # ----------------------------------------------------

            prepared["article_category"] = (
                self.first_value(
                    article,
                    (
                        "category",
                        "section",
                        "article_category",
                    ),
                    prepared.get(
                        "category",
                        "",
                    ),
                )
            )

            prepared["article_category"] = (
                self.clean_markdown_formatting(
                    prepared[
                        "article_category"
                    ]
                )
            )

            # ----------------------------------------------------
            # Article source
            # ----------------------------------------------------

            prepared["article_source"] = (
                self.first_value(
                    article,
                    (
                        "source",
                        "article_source",
                    ),
                    "",
                )
            )

            prepared["article_source"] = (
                self.clean_markdown_formatting(
                    prepared[
                        "article_source"
                    ]
                )
            )

            # ----------------------------------------------------
            # Article URL
            # ----------------------------------------------------

            prepared["article_url"] = (
                self.first_value(
                    article,
                    (
                        "url",
                        "article_url",
                        "source_url",
                    ),
                    "",
                )
            )

            # ----------------------------------------------------
            # Article image
            # ----------------------------------------------------

            prepared["article_image"] = (
                self.first_value(
                    article,
                    (
                        "image",
                        "image_path",
                        "image_file",
                        "selected_image",
                    ),
                    prepared.get(
                        "image",
                        "",
                    ),
                )
            )

            # ----------------------------------------------------
            # Published date
            # ----------------------------------------------------

            prepared["published_date"] = (
                article.get(
                    "published_date",
                    prepared.get(
                        "published_date",
                        "",
                    ),
                )
            )

            # ----------------------------------------------------
            # Source IDs
            # ----------------------------------------------------

            prepared["source_ids"] = (
                article.get(
                    "source_ids",
                    prepared.get(
                        "source_ids",
                        [],
                    ),
                )
            )

            # ----------------------------------------------------
            # Full article content
            # ----------------------------------------------------

            prepared["article_content"] = (
                article.get(
                    "body",
                    article.get(
                        "article",
                        article.get(
                            "content",
                            "",
                        ),
                    ),
                )
            )

            prepared["article_content"] = (
                self.clean_markdown_formatting(
                    prepared[
                        "article_content"
                    ]
                )
            )

            # ----------------------------------------------------
            # Body chunk
            # ----------------------------------------------------

            if not prepared.get(
                "body_chunk"
            ):

                raise ValueError(
                    f"Article page "
                    f"{prepared.get('page_number')} "
                    f"for article "
                    f"{prepared.get('article_id')} "
                    f"has no body_chunk."
                )

            # ----------------------------------------------------
            # IMPORTANT:
            #
            # Clean Markdown before sending content
            # to Jinja2 / HTML.
            #
            # This removes:
            #
            #     **text**
            #
            # and produces:
            #
            #     text
            # ----------------------------------------------------

            prepared["body_chunk"] = (
                self.clean_markdown_formatting(
                    prepared[
                        "body_chunk"
                    ]
                )
            )

            prepared["content"] = (
                prepared[
                    "body_chunk"
                ]
            )

            prepared_pages.append(
                prepared
            )

        # --------------------------------------------------------
        # Check unresolved article pages
        # --------------------------------------------------------

        if unresolved:

            raise ValueError(
                "Unresolved article pages: "
                f"{unresolved}"
            )

        return prepared_pages

    # ============================================================
    # PAGE PREPARATION
    # ============================================================

    def prepare_pages(
        self,
        magazine: dict[str, Any],
    ) -> list[dict[str, Any]]:

        pages = (
            self.prepare_article_pages(
                magazine
            )
        )

        normalized_pages = []

        for index, page in enumerate(
            pages,
            start=1,
        ):

            prepared = dict(page)

            # ----------------------------------------------------
            # Page number
            # ----------------------------------------------------

            if not prepared.get(
                "page_number"
            ):

                prepared[
                    "page_number"
                ] = index

            # ----------------------------------------------------
            # Page type
            # ----------------------------------------------------

            if not prepared.get(
                "type"
            ):

                prepared[
                    "type"
                ] = "generic"

            # ----------------------------------------------------
            # Presentation-layer asset paths
            # ----------------------------------------------------

            for field in (
                "image",
                "article_image",
                "chart_path",
                "chart",
            ):

                if prepared.get(
                    field
                ):

                    prepared[field] = (
                        self.html_asset_path(
                            prepared[field]
                        )
                    )

            # ----------------------------------------------------
            # Optional image metadata
            # ----------------------------------------------------

            if prepared.get(
                "article_image"
            ):

                prepared[
                    "article_image_alt"
                ] = prepared.get(
                    "article_title",
                    prepared.get(
                        "title",
                        "Article image",
                    ),
                )

            # ----------------------------------------------------
            # Final safety cleanup
            #
            # This makes sure that even if another field containing
            # Markdown reaches the template, ** will not appear.
            # ----------------------------------------------------

            text_fields = (
                "title",
                "subtitle",
                "heading",
                "article_title",
                "article_category",
                "article_source",
                "body_chunk",
                "content",
                "article_content",
            )

            for field in text_fields:

                if field in prepared:

                    prepared[field] = (
                        self.clean_markdown_formatting(
                            prepared[field]
                        )
                    )

            normalized_pages.append(
                prepared
            )

        return normalized_pages

    # ============================================================
    # TEMPLATE CONTEXT
    # ============================================================

    def build_template_context(
        self,
        magazine: dict[str, Any],
        pages: list[dict[str, Any]],
    ) -> dict[str, Any]:

        return {
            "magazine": magazine,

            "metadata": magazine.get(
                "metadata",
                {},
            ),

            "toc": magazine.get(
                "toc",
                [],
            ),

            "sections": magazine.get(
                "sections",
                [],
            ),

            "charts": magazine.get(
                "charts",
                [],
            ),

            "articles": magazine.get(
                "articles",
                [],
            ),

            "page_plan": pages,

            "pages": pages,

            "validation": magazine.get(
                "validation",
                {},
            ),

            "title": magazine.get(
                "metadata",
                {},
            ).get(
                "title",
                "Northeast Sentinel AI",
            ),

            "project_name": (
                "Northeast Sentinel AI"
            ),
        }

    # ============================================================
    # HTML RENDERING
    # ============================================================

    def render_html(
        self,
        magazine: dict[str, Any],
    ) -> Path:

        pages = (
            self.prepare_pages(
                magazine
            )
        )

        # --------------------------------------------------------
        # Validate page count
        # --------------------------------------------------------

        if len(pages) != self.TARGET_PAGES:

            raise ValueError(
                f"Expected "
                f"{self.TARGET_PAGES} "
                f"logical pages, "
                f"received "
                f"{len(pages)}."
            )

        # --------------------------------------------------------
        # Load template
        # --------------------------------------------------------

        template = (
            self.env.get_template(
                self.template_name
            )
        )

        # --------------------------------------------------------
        # Render HTML
        # --------------------------------------------------------

        html = template.render(
            **self.build_template_context(
                magazine,
                pages,
            )
        )

        if not html.strip():

            raise ValueError(
                "Rendered HTML is empty."
            )

        # --------------------------------------------------------
        # Write HTML
        # --------------------------------------------------------

        self.html_output.write_text(
            html,
            encoding="utf-8",
        )

        print(
            f"\nHTML generated successfully:"
        )

        print(
            f"  {self.html_output}"
        )

        return self.html_output

    # ============================================================
    # HTML PAGE COUNT
    # ============================================================

    @staticmethod
    def count_html_pages(
        html: str,
    ) -> int:

        return html.count(
            '<section class="magazine-page'
        )

    # ============================================================
    # VALIDATE HTML PAGE COUNT
    # ============================================================

    def validate_html_page_count(
        self,
        html_path: Path,
    ) -> int:

        html = html_path.read_text(
            encoding="utf-8"
        )

        count = (
            self.count_html_pages(
                html
            )
        )

        print(
            f"Rendered HTML pages: {count}"
        )

        if count != self.TARGET_PAGES:

            raise ValueError(
                "HTML page count mismatch. "
                f"Expected "
                f"{self.TARGET_PAGES}, "
                f"found {count}."
            )

        return count

    # ============================================================
    # RUN
    # ============================================================

    def run(
        self,
    ) -> Path:

        # --------------------------------------------------------
        # Build magazine data
        # --------------------------------------------------------

        magazine = (
            self.build_magazine()
        )

        # --------------------------------------------------------
        # Validate source data
        # --------------------------------------------------------

        self.validate_magazine_structure(
            magazine
        )

        # --------------------------------------------------------
        # Render HTML
        # --------------------------------------------------------

        html_path = (
            self.render_html(
                magazine
            )
        )

        # --------------------------------------------------------
        # Validate rendered HTML
        # --------------------------------------------------------

        self.validate_html_page_count(
            html_path
        )

        print(
            "\n" + "=" * 70
        )

        print(
            "PHASE 15 COMPLETE"
        )

        print(
            "=" * 70
        )

        print(
            f"HTML: {html_path}"
        )

        print(
            f"Pages: {self.TARGET_PAGES}"
        )

        return html_path


# ================================================================
# MAIN
# ================================================================

def main():
    renderer = MagazineRenderer()
    renderer.run()


if __name__ == "__main__":
    main()