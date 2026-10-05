from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.magazine.page_builder import MagazinePageBuilder


class MagazineRenderer:
    """Phase 15 HTML renderer for the upgraded magazine composition engine."""

    TARGET_PAGES = 50

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[2]
        self.output_dir = Path(__import__("app.config.settings", fromlist=["settings"]).settings.OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.magazine_json = self.output_dir / "magazine_data.json"
        self.html_output = self.output_dir / "northeast_sentinel_magazine.html"
        self.template_dir = self.project_root / "app" / "magazine" / "templates"
        self.template_name = "magazine.html"
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "xml")),
        )

    @staticmethod
    def get_article_id(article: dict[str, Any]) -> str | None:
        for field in ("article_id", "id", "articleId", "source_id"):
            value = article.get(field)
            if value is not None:
                return str(value)
        return None

    def build_magazine(self) -> dict[str, Any]:
        print("\n" + "=" * 70)
        print("PHASE 15 — MAGAZINE HTML RENDERER")
        print("=" * 70)
        MagazinePageBuilder().build()
        if not self.magazine_json.exists():
            raise FileNotFoundError(f"Magazine data file was not created: {self.magazine_json}")
        with self.magazine_json.open("r", encoding="utf-8") as file:
            return json.load(file)

    def validate_magazine_structure(self, magazine: dict[str, Any]) -> None:
        required = {"metadata", "toc", "sections", "charts", "articles", "page_plan", "validation"}
        missing = sorted(required - set(magazine))
        if missing:
            raise ValueError(f"Missing keys in magazine_data.json: {', '.join(missing)}")
        if not isinstance(magazine["articles"], list):
            raise ValueError("magazine['articles'] must be a list.")
        if not isinstance(magazine["page_plan"], list):
            raise ValueError("magazine['page_plan'] must be a list.")
        if len(magazine["page_plan"]) != self.TARGET_PAGES:
            raise ValueError(f"Expected {self.TARGET_PAGES} logical pages, found {len(magazine['page_plan'])}.")
        if not magazine["articles"]:
            raise ValueError("No article records were found.")

    def build_article_lookup(self, magazine: dict[str, Any]) -> dict[str, dict[str, Any]]:
        lookup = {}
        for article in magazine.get("articles", []):
            if not isinstance(article, dict):
                continue
            article_id = self.get_article_id(article)
            if article_id is not None:
                lookup[article_id] = article
        if not lookup:
            raise ValueError("Article lookup is empty.")
        return lookup

    @staticmethod
    def first_value(data: dict[str, Any], fields: tuple[str, ...], default: Any = "") -> Any:
        for field in fields:
            value = data.get(field)
            if value is not None and value != "":
                return value
        return default

    def prepare_article_pages(self, magazine: dict[str, Any]) -> list[dict[str, Any]]:
        lookup = self.build_article_lookup(magazine)
        prepared_pages = []
        unresolved = []

        for page in magazine.get("page_plan", []):
            prepared = dict(page)
            if prepared.get("type") != "article":
                prepared_pages.append(prepared)
                continue

            article_id = prepared.get("article_id", prepared.get("id"))
            article = lookup.get(str(article_id)) if article_id is not None else None
            if article is None:
                unresolved.append({"page": prepared.get("page_number"), "article_id": article_id})
                continue

            prepared["article"] = article
            prepared["article_id"] = self.get_article_id(article) or str(article_id)
            prepared["article_title"] = self.first_value(article, ("title", "headline", "article_title"), prepared.get("title", ""))
            prepared["article_category"] = self.first_value(article, ("category", "section", "article_category"), prepared.get("category", ""))
            prepared["article_source"] = self.first_value(article, ("source", "article_source"), "")
            prepared["article_url"] = self.first_value(article, ("url", "article_url", "source_url"), "")
            prepared["article_image"] = self.first_value(article, ("image", "image_path", "image_file", "selected_image"), prepared.get("image", ""))
            prepared["published_date"] = article.get("published_date", prepared.get("published_date", ""))
            prepared["source_ids"] = article.get("source_ids", prepared.get("source_ids", []))
            prepared["article_content"] = article.get("body", article.get("article", article.get("content", "")))

            # Critical Phase 15 fix: use the chunk generated by page_builder.
            if not prepared.get("body_chunk"):
                raise ValueError(
                    f"Article page {prepared.get('page_number')} for article {prepared.get('article_id')} has no body_chunk."
                )
            prepared["content"] = prepared["body_chunk"]
            prepared_pages.append(prepared)

        if unresolved:
            raise ValueError(f"Unresolved article pages: {unresolved}")
        return prepared_pages

    def prepare_pages(
        self,
        magazine: dict[str, Any],
    ) -> list[dict[str, Any]]:

        pages = self.prepare_article_pages(
            magazine
        )

        normalized_pages = []

        for index, page in enumerate(
            pages,
            start=1,
        ):

            prepared = dict(page)

            if not prepared.get(
                "page_number"
            ):
                prepared[
                    "page_number"
                ] = index

            if not prepared.get(
                "type"
            ):
                prepared[
                    "type"
                ] = "generic"

            # ============================================================
            # HTML ASSET PATH FIX
            #
            # The generated HTML is stored in:
            #     data/output/northeast_sentinel_magazine.html
            #
            # Assets are stored in:
            #     data/charts/
            #     data/images/
            #
            # Therefore HTML must use:
            #     ../charts/...
            #     ../images/...
            #
            # instead of:
            #     data/charts/...
            #     data/images/...
            # ============================================================

            def html_asset_path(path: Any) -> Any:

                if not path:
                    return path

                path = str(path).replace("\\", "/")

                # Already-relative HTML paths
                if path.startswith("../"):
                    return path

                # Project-root relative asset paths
                if path.startswith("data/"):
                    return "../" + path[len("data/"):]

                return path

            # ------------------------------------------------------------
            # Chart paths
            # ------------------------------------------------------------

            if prepared.get("chart_path"):
                prepared["chart_path"] = html_asset_path(
                    prepared["chart_path"]
                )

            if prepared.get("image"):
                prepared["image"] = html_asset_path(
                    prepared["image"]
                )

            # ------------------------------------------------------------
            # Article image
            # ------------------------------------------------------------

            if prepared.get("article_image"):
                prepared["article_image"] = html_asset_path(
                    prepared["article_image"]
                )

            normalized_pages.append(
                prepared
            )

        return normalized_pages

    def build_template_context(self, magazine: dict[str, Any], pages: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "magazine": magazine,
            "metadata": magazine.get("metadata", {}),
            "toc": magazine.get("toc", []),
            "sections": magazine.get("sections", []),
            "charts": magazine.get("charts", []),
            "articles": magazine.get("articles", []),
            "page_plan": pages,
            "pages": pages,
            "validation": magazine.get("validation", {}),
            "title": magazine.get("metadata", {}).get("title", "Northeast Sentinel AI"),
            "project_name": "Northeast Sentinel AI",
        }

    def render_html(self, magazine: dict[str, Any]) -> Path:
        pages = self.prepare_pages(magazine)
        if len(pages) != self.TARGET_PAGES:
            raise ValueError(f"Expected {self.TARGET_PAGES} logical pages, received {len(pages)}.")

        template = self.env.get_template(self.template_name)
        html = template.render(**self.build_template_context(magazine, pages))
        if not html.strip():
            raise ValueError("Rendered HTML is empty.")
        self.html_output.write_text(html, encoding="utf-8")
        return self.html_output

    @staticmethod
    def count_html_pages(html: str) -> int:
        return html.count('<section class="magazine-page')

    def validate_html_page_count(self, html_path: Path) -> int:
        html = html_path.read_text(encoding="utf-8")
        count = self.count_html_pages(html)
        print(f"Rendered HTML pages: {count}")
        if count != self.TARGET_PAGES:
            raise ValueError(f"HTML page count mismatch. Expected {self.TARGET_PAGES}, found {count}.")
        return count

    def run(self) -> Path:
        magazine = self.build_magazine()
        self.validate_magazine_structure(magazine)
        output = self.render_html(magazine)
        self.validate_html_page_count(output)
        print("PHASE 15 — HTML RENDERING COMPLETE")
        print(f"Output: {output}")
        return output


if __name__ == "__main__":
    MagazineRenderer().run()