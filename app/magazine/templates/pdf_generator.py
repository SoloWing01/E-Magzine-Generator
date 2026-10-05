from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup
from weasyprint import HTML

from app.config.settings import settings


# ============================================================
# PAGE CONSTANTS
# ============================================================

PX_PER_MM = 96 / 25.4

A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297

PAGE_W = A4_WIDTH_MM * PX_PER_MM
PAGE_H = A4_HEIGHT_MM * PX_PER_MM

# Safety margins for layout auditing
BOTTOM_MARGIN_MM = 20
ARTICLE_SOURCE_MARGIN_MM = 15

BOTTOM_LIMIT = PAGE_H - (BOTTOM_MARGIN_MM * PX_PER_MM)

ARTICLE_LIMIT = PAGE_H - (
    (BOTTOM_MARGIN_MM + ARTICLE_SOURCE_MARGIN_MM) * PX_PER_MM
)

TOLERANCE_MM = 0.5


# ============================================================
# WEASYPRINT BOX HELPERS
# ============================================================

def iter_boxes(box):
    """
    Recursively iterate through all WeasyPrint layout boxes.
    """
    yield box

    for child in getattr(box, "children", None) or []:
        yield from iter_boxes(child)


def classes_of(box) -> list[str]:
    """
    Return CSS classes associated with a WeasyPrint box.
    """
    element = getattr(box, "element", None)

    if element is None:
        return []

    classes = element.get("class") or ""

    return classes.split()


def bottom_of(box) -> float:
    """
    Return the bottom coordinate of a box.
    """
    try:
        return box.position_y + box.margin_height()
    except Exception:
        return 0.0


def element_text(element, limit: int = 120) -> str:
    """
    Extract a small amount of readable text from an HTML element.
    Useful for diagnostics.
    """
    if element is None:
        return ""

    try:
        text = " ".join(element.itertext()).strip()
        text = " ".join(text.split())

        if len(text) > limit:
            return text[:limit] + "..."

        return text

    except Exception:
        return ""


# ============================================================
# PDF GENERATOR
# ============================================================

class PDFGenerator:
    """
    Phase 16 - HTML to PDF conversion using WeasyPrint.

    Responsibilities:
        1. Locate the generated HTML magazine.
        2. Render HTML using WeasyPrint.
        3. Audit pagination.
        4. Detect overflowing content.
        5. Detect blank/stray physical pages.
        6. Compare logical HTML pages with physical PDF pages.
        7. Write the final PDF.
    """

    def __init__(
        self,
        html_path: Path | None = None,
        pdf_path: Path | None = None,
        expected_pages: int | None = None,
    ):
        # ----------------------------------------------------
        # Resolve output directory locally.
        #
        # Do NOT import resolve_path from page_builder.py.
        # The current page_builder.py does not define it.
        # ----------------------------------------------------

        output_dir = Path(settings.OUTPUT_DIR)

        if not output_dir.is_absolute():
            output_dir = Path(__file__).resolve().parents[3] / output_dir

        self.output_dir = output_dir

        self.html_path = (
            Path(html_path)
            if html_path
            else output_dir / "northeast_sentinel_magazine.html"
        )

        self.pdf_path = (
            Path(pdf_path)
            if pdf_path
            else output_dir / "northeast_sentinel_magazine.pdf"
        )

        self.expected_pages = expected_pages

        self.document = None

    # ========================================================
    # HEADER
    # ========================================================

    @staticmethod
    def header(title: str):
        print(
            "\n"
            + "=" * 70
            + f"\n{title}\n"
            + "=" * 70
        )

    # ========================================================
    # LOGICAL HTML PAGES
    # ========================================================

    def logical_pages(self) -> list:
        """
        Read the generated HTML and count .magazine-page elements.
        """
        if not self.html_path.exists():
            raise FileNotFoundError(
                f"HTML input not found: {self.html_path}"
            )

        html = self.html_path.read_text(
            encoding="utf-8"
        )

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        return soup.select(".magazine-page")

    # ========================================================
    # HTML STRUCTURE AUDIT
    # ========================================================

    def inspect_logical_pages(self):
        """
        Print logical HTML page information.

        This is useful before rendering the PDF.
        """

        pages = self.logical_pages()

        self.header("HTML PAGE STRUCTURE")

        print(f"HTML file       : {self.html_path}")
        print(f"Logical pages   : {len(pages)}")

        for index, page in enumerate(pages, start=1):

            page_classes = page.get("class", [])

            page_type = (
                page.get("data-page-type")
                or page.get("data-type")
                or ""
            )

            article_id = (
                page.get("data-article-id")
                or ""
            )

            text = element_text(
                page,
                limit=80,
            )

            print(
                f"  HTML {index:02d} | "
                f"type={page_type or 'unknown':15} | "
                f"article={article_id or '-':5} | "
                f"class={' '.join(page_classes)} | "
                f"{text}"
            )

    # ========================================================
    # RENDER
    # ========================================================

    def render(self):
        """
        Render HTML using WeasyPrint.

        filename= is important because image/chart paths in the
        generated HTML are relative to data/output/.
        """

        if not self.html_path.exists():
            raise FileNotFoundError(
                f"HTML input not found: {self.html_path}"
            )

        print(
            f"\nRendering HTML:\n"
            f"{self.html_path}"
        )

        self.document = HTML(
            filename=str(self.html_path)
        ).render()

        return self.document

    # ========================================================
    # PHYSICAL PAGE INSPECTION
    # ========================================================

    def inspect_physical_pages(self):
        """
        Inspect each physical page produced by WeasyPrint.

        This specifically helps diagnose situations such as:

            Logical HTML pages : 50
            Physical PDF pages : 51

        It reports how many .magazine-page elements exist on each
        physical page and provides basic identification.
        """

        if self.document is None:
            raise RuntimeError(
                "Document has not been rendered yet."
            )

        self.header("PHYSICAL PAGE INSPECTION")

        for physical_number, page in enumerate(
            self.document.pages,
            start=1,
        ):

            boxes = list(
                iter_boxes(page._page_box)
            )

            sheets = [
                box
                for box in boxes
                if "magazine-page" in classes_of(box)
            ]

            print(
                f"\nPDF page {physical_number:02d}: "
                f"{len(sheets)} magazine-page element(s)"
            )

            if not sheets:
                print(
                    "  WARNING: No .magazine-page element "
                    "found on this physical page."
                )

                continue

            for sheet_number, sheet in enumerate(
                sheets,
                start=1,
            ):

                element = getattr(
                    sheet,
                    "element",
                    None,
                )

                page_type = ""

                article_id = ""

                if element is not None:

                    page_type = (
                        element.get(
                            "data-page-type",
                            "",
                        )
                        or element.get(
                            "data-type",
                            "",
                        )
                    )

                    article_id = element.get(
                        "data-article-id",
                        "",
                    )

                text = element_text(
                    element,
                    limit=100,
                )

                print(
                    f"  Sheet {sheet_number}: "
                    f"type={page_type or 'unknown'}, "
                    f"article={article_id or '-'}, "
                    f"text={text}"
                )

    # ========================================================
    # LAYOUT AUDIT
    # ========================================================

    def audit(self) -> list[dict]:
        """
        Return one audit record per physical PDF page.
        """

        if self.document is None:
            raise RuntimeError(
                "Document has not been rendered yet."
            )

        records = []

        for number, page in enumerate(
            self.document.pages,
            start=1,
        ):

            boxes = list(
                iter_boxes(page._page_box)
            )

            # ------------------------------------------------
            # Find magazine sheet(s)
            # ------------------------------------------------

            sheets = [
                box
                for box in boxes
                if "magazine-page" in classes_of(box)
            ]

            rec = {
                "page": number,
                "sheets": len(sheets),
                "type": "",
                "article_id": "",
                "overflow_mm": 0.0,
                "height_mm": 0.0,
                "width_mm": 0.0,
                "text": "",
            }

            # ------------------------------------------------
            # Sheet metadata
            # ------------------------------------------------

            if sheets:

                sheet = sheets[0]

                element = getattr(
                    sheet,
                    "element",
                    None,
                )

                if element is not None:

                    rec["type"] = (
                        element.get(
                            "data-page-type",
                            "",
                        )
                        or element.get(
                            "data-type",
                            "",
                        )
                    )

                    rec["article_id"] = element.get(
                        "data-article-id",
                        "",
                    )

                    rec["text"] = element_text(
                        element,
                        limit=120,
                    )

                # --------------------------------------------
                # Physical sheet dimensions
                # --------------------------------------------

                try:
                    rec["width_mm"] = round(
                        sheet.width / PX_PER_MM,
                        2,
                    )

                    rec["height_mm"] = round(
                        sheet.height / PX_PER_MM,
                        2,
                    )

                except Exception:
                    pass

            # ------------------------------------------------
            # Determine overflow limit
            # ------------------------------------------------

            if rec["type"] == "article":
                limit = ARTICLE_LIMIT
            else:
                limit = BOTTOM_LIMIT

            # ------------------------------------------------
            # Check .fit elements
            # ------------------------------------------------

            worst = 0.0

            for box in boxes:

                if "fit" not in classes_of(box):
                    continue

                overflow_px = (
                    bottom_of(box) - limit
                )

                overflow_mm = (
                    overflow_px / PX_PER_MM
                )

                worst = max(
                    worst,
                    overflow_mm,
                )

            rec["overflow_mm"] = round(
                worst,
                1,
            )

            records.append(rec)

        return records

    # ========================================================
    # DIAGNOSE
    # ========================================================

    def diagnose(
        self,
        records: list[dict],
        logical_count: int,
    ) -> bool:

        self.header("PDF LAYOUT AUDIT")

        physical_count = len(records)

        print(
            f"Logical HTML pages : {logical_count}"
        )

        print(
            f"Physical PDF pages : {physical_count}"
        )

        print(
            f"Expected pages     : "
            f"{self.expected_pages or logical_count}"
        )

        print()

        # ----------------------------------------------------
        # Basic page-count check
        # ----------------------------------------------------

        ok = (
            physical_count
            == (self.expected_pages or logical_count)
        )

        # ----------------------------------------------------
        # Check every physical page
        # ----------------------------------------------------

        for record in records:

            problems = []

            # -----------------------------------------------
            # Missing or duplicate sheet
            # -----------------------------------------------

            if record["sheets"] == 0:

                problems.append(
                    "NO magazine-page element"
                )

            elif record["sheets"] > 1:

                problems.append(
                    f"{record['sheets']} magazine-page "
                    f"elements on this physical page"
                )

            # -----------------------------------------------
            # Overflow
            # -----------------------------------------------

            if (
                record["overflow_mm"]
                > TOLERANCE_MM
            ):

                problems.append(
                    "content overflows by "
                    f"{record['overflow_mm']} mm"
                )

            # -----------------------------------------------
            # Unusual sheet size
            # -----------------------------------------------

            width = record["width_mm"]
            height = record["height_mm"]

            if width and height:

                width_ok = (
                    abs(width - A4_WIDTH_MM)
                    <= 2
                )

                height_ok = (
                    abs(height - A4_HEIGHT_MM)
                    <= 2
                )

                # WeasyPrint may represent dimensions
                # slightly differently, so only report
                # clearly abnormal values.

                if not width_ok or not height_ok:

                    problems.append(
                        f"sheet size is "
                        f"{width}mm x {height}mm"
                    )

            # -----------------------------------------------
            # Print problems
            # -----------------------------------------------

            if problems:

                ok = False

                article_text = ""

                if record["article_id"]:

                    article_text = (
                        f" article={record['article_id']}"
                    )

                print(
                    f"  PDF page "
                    f"{record['page']:02d}"
                    f"{article_text}: "
                    + "; ".join(problems)
                )

        # ----------------------------------------------------
        # Page-count mismatch
        # ----------------------------------------------------

        if physical_count != (
            self.expected_pages
            or logical_count
        ):

            ok = False

            print()
            print(
                "PAGE COUNT MISMATCH DETECTED."
            )

            if physical_count > logical_count:

                print(
                    "There are more physical PDF pages "
                    "than logical HTML pages."
                )

                print(
                    "This usually means a magazine page "
                    "is being fragmented or an extra "
                    "blank/overflow page is being created."
                )

            else:

                print(
                    "There are fewer physical PDF pages "
                    "than logical HTML pages."
                )

                print(
                    "Some logical pages may be missing "
                    "during PDF rendering."
                )

        # ----------------------------------------------------
        # Final status
        # ----------------------------------------------------

        if ok:

            print()
            print(
                "No pagination or overflow problems detected."
            )

        else:

            print()
            print(
                "Layout audit FAILED."
            )

            print()
            print(
                "Recommended debugging steps:"
            )

            print(
                "1. Check the physical page inspection "
                "above."
            )

            print(
                "2. Look for a PDF page with "
                "'NO magazine-page element'."
            )

            print(
                "3. Look for an article page with "
                "overflow."
            )

            print(
                "4. If an article overflows, reduce "
                "its word budget in page_builder.py."
            )

            print(
                "5. Re-run the magazine rendering "
                "before generating the PDF again."
            )

        return ok

    # ========================================================
    # GENERATE PDF
    # ========================================================

    def run(
        self,
        strict: bool = False,
    ) -> Path:

        self.header(
            "PHASE 16 - PDF GENERATION"
        )

        # ----------------------------------------------------
        # Verify HTML
        # ----------------------------------------------------

        if not self.html_path.exists():

            raise FileNotFoundError(
                f"HTML input not found:\n"
                f"{self.html_path}"
            )

        # ----------------------------------------------------
        # Count logical pages
        # ----------------------------------------------------

        logical_pages = self.logical_pages()

        logical_count = len(
            logical_pages
        )

        expected = (
            self.expected_pages
            or logical_count
        )

        print(
            f"HTML:\n{self.html_path}"
        )

        print(
            f"\nLogical pages: {logical_count}"
        )

        print(
            f"Expected pages: {expected}"
        )

        # ----------------------------------------------------
        # Render
        # ----------------------------------------------------

        self.render()

        # ----------------------------------------------------
        # Physical-page diagnostic
        # ----------------------------------------------------

        self.inspect_physical_pages()

        # ----------------------------------------------------
        # Layout audit
        # ----------------------------------------------------

        records = self.audit()

        ok = self.diagnose(
            records,
            expected,
        )

        # ----------------------------------------------------
        # Strict mode
        # ----------------------------------------------------

        if not ok and strict:

            print()
            print(
                "STRICT MODE ENABLED."
            )

            print(
                "PDF will NOT be written because "
                "the layout audit failed."
            )

            raise RuntimeError(
                "Layout audit failed "
                "(strict mode); PDF not written."
            )

        # ----------------------------------------------------
        # Write PDF
        # ----------------------------------------------------

        self.pdf_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        print()
        print(
            "Writing PDF..."
        )

        self.document.write_pdf(
            str(self.pdf_path)
        )

        # ----------------------------------------------------
        # File information
        # ----------------------------------------------------

        size_mb = (
            self.pdf_path.stat().st_size
            / (1024 * 1024)
        )

        # ----------------------------------------------------
        # Final status
        # ----------------------------------------------------

        self.header(
            "PHASE 16 COMPLETE"
        )

        print(
            f"PDF:\n{self.pdf_path}"
        )

        print(
            f"Size: {size_mb:.2f} MB"
        )

        print(
            f"Physical pages: "
            f"{len(self.document.pages)}"
        )

        print(
            f"Logical HTML pages: "
            f"{logical_count}"
        )

        if len(self.document.pages) == expected:

            print(
                "\nSUCCESS: PDF page count matches "
                "the expected page count."
            )

        else:

            print(
                "\nWARNING: PDF page count does not "
                "match the expected page count."
            )

        return self.pdf_path


# ============================================================
# COMMAND LINE ENTRY POINT
# ============================================================

if __name__ == "__main__":

    strict_mode = (
        "--strict"
        in sys.argv
    )

    try:

        PDFGenerator().run(
            strict=strict_mode
        )

    except Exception as exc:

        print()
        print(
            "=" * 70
        )

        print(
            "PDF GENERATION FAILED"
        )

        print(
            "=" * 70
        )

        print(
            f"\nError: {exc}"
        )

        raise