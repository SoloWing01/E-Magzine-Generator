from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from weasyprint import HTML

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


# ============================================================================
# PATH CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parents[3]

OUTPUT_DIR = BASE_DIR / "data" / "output"

HTML_PATH = OUTPUT_DIR / "northeast_sentinel_magazine.html"
PDF_PATH = OUTPUT_DIR / "northeast_sentinel_magazine.pdf"

EXPECTED_PAGES = 50


# ============================================================================
# PDF CSS
# ============================================================================

PDF_CSS = """
<style id="pdf-magazine-normalization">

/* ========================================================================
   PHYSICAL PAGE
   ======================================================================== */

@page {
    size: A4;
    margin: 0;
}


/* ========================================================================
   ROOT
   ======================================================================== */

html,
body {
    margin: 0 !important;
    padding: 0 !important;

    width: 210mm !important;

    box-sizing: border-box !important;
}


/* ========================================================================
   GLOBAL BOX MODEL
   ======================================================================== */

*,
*::before,
*::after {
    box-sizing: border-box !important;
}


/* ========================================================================
   MAGAZINE PAGE
   ======================================================================== */

.magazine-page {

    width: 210mm !important;

    min-width: 210mm !important;
    max-width: 210mm !important;

    /*
       A4 physical height at the CSS page level.
    */
    height: 297mm !important;

    min-height: 297mm !important;
    max-height: 297mm !important;

    margin: 0 !important;

    padding: 0 !important;

    box-sizing: border-box !important;

    position: relative !important;

    overflow: hidden !important;

    /*
       Every .magazine-page is a complete physical page.
    */
    break-before: auto !important;
    break-after: page !important;
    break-inside: avoid !important;

    page-break-before: auto !important;
    page-break-after: always !important;
    page-break-inside: avoid !important;
}


/* ========================================================================
   LAST PAGE
   ======================================================================== */

.magazine-page:last-child {
    break-after: auto !important;
    page-break-after: auto !important;
}


/* ========================================================================
   ARTICLE PAGES
   ======================================================================== */

.article-page {

    width: 210mm !important;
    height: 297mm !important;

    min-height: 297mm !important;
    max-height: 297mm !important;

    overflow: hidden !important;

    break-inside: avoid !important;
    page-break-inside: avoid !important;
}


/*
   Article content must not independently generate pages.
*/

.article-page .article-body,
.article-page .article-content,
.article-page .article-text {

    overflow: hidden !important;

    max-height: 250mm !important;

    box-sizing: border-box !important;
}


/* ========================================================================
   ARTICLE TYPOGRAPHY
   ======================================================================== */

/*
   These PDF-only values prevent long generated articles from exceeding
   the physical page. The HTML version remains unchanged.
*/

.article-page p {

    margin-top: 0.8em !important;
    margin-bottom: 0.8em !important;

    line-height: 1.35 !important;

    break-inside: avoid !important;
    page-break-inside: avoid !important;
}


.article-page h1,
.article-page h2,
.article-page h3,
.article-page h4 {

    break-inside: avoid !important;
    page-break-inside: avoid !important;
}


/* ========================================================================
   IMAGES
   ======================================================================== */

.magazine-page img {

    max-width: 100% !important;

    box-sizing: border-box !important;

    object-fit: contain !important;

    break-inside: avoid !important;
    page-break-inside: avoid !important;
}


/* ========================================================================
   FIGURES
   ======================================================================== */

.magazine-page figure {

    max-width: 100% !important;

    margin: 0 !important;

    box-sizing: border-box !important;

    break-inside: avoid !important;
    page-break-inside: avoid !important;
}


/* ========================================================================
   TABLES
   ======================================================================== */

.magazine-page table {

    max-width: 100% !important;

    box-sizing: border-box !important;

    break-inside: avoid !important;
    page-break-inside: avoid !important;
}


/* ========================================================================
   CHARTS
   ======================================================================== */

.chart-page {

    break-inside: avoid !important;
    page-break-inside: avoid !important;
}


/* ========================================================================
   COVER PAGES
   ======================================================================== */

.cover-page,
.back-cover {

    break-inside: avoid !important;
    page-break-inside: avoid !important;
}


/* ========================================================================
   PRINT SAFETY
   ======================================================================== */

.no-print {
    display: none !important;
}

</style>
"""


# ============================================================================
# PDF GENERATOR
# ============================================================================


class PDFGenerator:

    def __init__(
        self,
        html_path: Path = HTML_PATH,
        pdf_path: Path = PDF_PATH,
        expected_pages: int = EXPECTED_PAGES,
    ):

        self.html_path = Path(html_path)
        self.pdf_path = Path(pdf_path)

        self.expected_pages = expected_pages

        self.html_content: Optional[str] = None
        self.pdf_html: Optional[str] = None

        self.soup: Optional[BeautifulSoup] = None


    # ========================================================================
    # HEADER
    # ========================================================================

    @staticmethod
    def header(title: str):

        print("\n" + "=" * 70)
        print(title)
        print("=" * 70)


    # ========================================================================
    # LOAD HTML
    # ========================================================================

    def load_html(self):

        self.header("Checking HTML input...")

        if not self.html_path.exists():

            raise FileNotFoundError(
                f"HTML input not found:\n{self.html_path}"
            )

        self.html_content = self.html_path.read_text(
            encoding="utf-8"
        )

        print("HTML input found:")
        print(self.html_path)

        size_kb = self.html_path.stat().st_size / 1024

        print(
            f"HTML size: {size_kb:.2f} KB"
        )


    # ========================================================================
    # HTML STRUCTURE
    # ========================================================================

    def validate_html_pages(self):

        self.header(
            "Validating HTML page structure..."
        )

        if self.html_content is None:

            raise RuntimeError(
                "HTML has not been loaded."
            )

        self.soup = BeautifulSoup(
            self.html_content,
            "html.parser",
        )

        pages = self.soup.select(
            ".magazine-page"
        )

        count = len(pages)

        print(
            f"HTML logical pages: {count}"
        )

        if count != self.expected_pages:

            raise ValueError(
                "\n"
                "HTML PAGE COUNT MISMATCH\n"
                f"Expected : {self.expected_pages}\n"
                f"Actual   : {count}\n"
            )

        print(
            "HTML page count: PASSED"
        )


    # ========================================================================
    # ASSET DISCOVERY
    # ========================================================================

    @staticmethod
    def is_external_asset(asset: str) -> bool:

        value = asset.lower().strip()

        return (
            value.startswith("http://")
            or value.startswith("https://")
            or value.startswith("data:")
            or value.startswith("//")
        )


    def resolve_asset(
        self,
        asset: str,
    ) -> Optional[Path]:

        if not asset:
            return None

        asset = asset.strip()

        if self.is_external_asset(asset):

            return None

        asset = asset.split("#")[0]
        asset = asset.split("?")[0]

        asset = asset.replace(
            "%20",
            " ",
        )

        candidates = []

        path = Path(asset)

        if path.is_absolute():

            candidates.append(path)

        candidates.append(
            BASE_DIR / asset
        )

        candidates.append(
            self.html_path.parent / asset
        )

        candidates.append(
            BASE_DIR / asset.lstrip("./")
        )

        for candidate in candidates:

            if candidate.exists():

                return candidate

        return None


    def validate_assets(self):

        self.header(
            "Validating HTML assets..."
        )

        if self.soup is None:

            raise RuntimeError(
                "HTML has not been parsed."
            )

        image_elements = self.soup.find_all(
            "img"
        )

        local_assets = 0
        external_assets = 0
        missing_assets = []

        for image in image_elements:

            src = image.get("src")

            if not src:
                continue

            if self.is_external_asset(src):

                external_assets += 1

                continue

            local_assets += 1

            if self.resolve_asset(src) is None:

                missing_assets.append(src)

        print(
            f"Image elements found: "
            f"{len(image_elements)}"
        )

        print(
            f"Local assets checked: "
            f"{local_assets}"
        )

        print(
            f"External/data assets: "
            f"{external_assets}"
        )

        print(
            f"Missing assets: "
            f"{len(missing_assets)}"
        )

        if missing_assets:

            print("\nMissing assets:")

            for asset in missing_assets:

                print(
                    f"  - {asset}"
                )

            raise FileNotFoundError(
                "Missing local HTML assets."
            )

        print(
            "Asset validation: PASSED"
        )


    # ========================================================================
    # CSS INSPECTION
    # ========================================================================

    def inspect_original_css(self):

        self.header(
            "Inspecting original HTML CSS..."
        )

        if self.html_content is None:

            raise RuntimeError(
                "HTML has not been loaded."
            )

        css = self.html_content.lower()

        a4_found = (
            "a4" in css
            or "210mm" in css
            or "297mm" in css
        )

        page_break_found = (
            "page-break" in css
            or "break-after" in css
            or "break-before" in css
        )

        print(
            "Original A4 declaration: "
            f"{'FOUND' if a4_found else 'NOT FOUND'}"
        )

        print(
            "Original page-break CSS: "
            f"{'FOUND' if page_break_found else 'NOT FOUND'}"
        )


    # ========================================================================
    # PREPARE PDF HTML
    # ========================================================================

    def prepare_pdf_html(self):

        self.header(
            "Preparing PDF HTML..."
        )

        if self.html_content is None:

            raise RuntimeError(
                "HTML has not been loaded."
            )

        html = self.html_content

        # ------------------------------------------------------------
        # Remove any previously injected PDF normalization block.
        #
        # This makes repeated runs deterministic.
        # ------------------------------------------------------------

        html = re.sub(
            r'<style[^>]*id=["\']pdf-normalization["\'][^>]*>.*?</style>',
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        html = re.sub(
            r'<style[^>]*id=["\']pdf-magazine-normalization["\'][^>]*>.*?</style>',
            "",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        # ------------------------------------------------------------
        # Insert as the final stylesheet.
        # ------------------------------------------------------------

        lower = html.lower()

        body_index = lower.rfind(
            "</body>"
        )

        if body_index != -1:

            html = (
                html[:body_index]
                + PDF_CSS
                + html[body_index:]
            )

        else:

            html += PDF_CSS

        self.pdf_html = html

        print(
            "PDF CSS normalization: APPLIED"
        )


    # ========================================================================
    # GENERATE PDF
    # ========================================================================

    def generate_pdf(self):

        self.header(
            "Generating PDF with WeasyPrint..."
        )

        if self.pdf_html is None:

            raise RuntimeError(
                "PDF HTML is not prepared."
            )

        self.pdf_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            f"Input : {self.html_path}"
        )

        print(
            f"Output: {self.pdf_path}"
        )

        document = HTML(
            string=self.pdf_html,
            base_url=str(BASE_DIR),
        )

        document.write_pdf(
            str(self.pdf_path)
        )

        if not self.pdf_path.exists():

            raise RuntimeError(
                "PDF was not created."
            )

        size_mb = (
            self.pdf_path.stat().st_size
            / (1024 * 1024)
        )

        print(
            "\nPDF generated successfully."
        )

        print(
            f"PDF path: {self.pdf_path}"
        )

        print(
            f"PDF size: {size_mb:.2f} MB"
        )


    # ========================================================================
    # PDF FILE VALIDATION
    # ========================================================================

    def validate_pdf_file(self):

        self.header(
            "Validating PDF file..."
        )

        if not self.pdf_path.exists():

            raise FileNotFoundError(
                self.pdf_path
            )

        with self.pdf_path.open(
            "rb"
        ) as file:

            header = file.read(5)

        if header != b"%PDF-":

            raise ValueError(
                "Invalid PDF header."
            )

        print(
            "PDF header: PASSED"
        )


    # ========================================================================
    # PAGE COUNT
    # ========================================================================

    def get_pdf_page_count(self):

        if PdfReader is None:

            raise RuntimeError(
                "pypdf is required for PDF validation."
            )

        reader = PdfReader(
            str(self.pdf_path)
        )

        return len(reader.pages)


    # ========================================================================
    # PAGE VALIDATION
    # ========================================================================

    def validate_pdf_pages(self):

        self.header(
            "Validating physical PDF page count..."
        )

        page_count = self.get_pdf_page_count()

        print(
            "Page-count method: pypdf"
        )

        print(
            f"Physical PDF pages: "
            f"{page_count}"
        )

        if page_count != self.expected_pages:

            raise ValueError(
                "\n"
                "PDF PAGE COUNT MISMATCH\n"
                f"Expected : {self.expected_pages}\n"
                f"Actual   : {page_count}\n"
            )

        print(
            "PDF page count: PASSED"
        )


    # ========================================================================
    # PDF TEXT DIAGNOSTIC
    # ========================================================================

    def diagnose_pdf(self):

        self.header(
            "PDF PAGE DIAGNOSTIC"
        )

        if PdfReader is None:

            print(
                "pypdf unavailable."
            )

            return

        reader = PdfReader(
            str(self.pdf_path)
        )

        print(
            f"Physical pages: {len(reader.pages)}"
        )

        print(
            f"Expected pages : {self.expected_pages}"
        )

        print(
            "\nPhysical page mapping:"
        )

        for number, page in enumerate(
            reader.pages,
            start=1,
        ):

            try:

                text = (
                    page.extract_text()
                    or ""
                )

                text = " ".join(
                    text.split()
                )

                preview = text[:160]

            except Exception as exc:

                preview = (
                    f"<extraction error: {exc}>"
                )

            print(
                f"{number:03d} | {preview}"
            )


    # ========================================================================
    # COMPLETE PIPELINE
    # ========================================================================

    def run(self):

        self.header(
            "PHASE 16 — PDF GENERATION"
        )

        try:

            # 1
            self.load_html()

            # 2
            self.validate_html_pages()

            # 3
            self.validate_assets()

            # 4
            self.inspect_original_css()

            # 5
            self.prepare_pdf_html()

            # 6
            self.generate_pdf()

            # 7
            self.validate_pdf_file()

            # 8
            try:

                self.validate_pdf_pages()

            except ValueError:

                self.diagnose_pdf()

                raise

            # --------------------------------------------------------
            # SUCCESS
            # --------------------------------------------------------

            self.header(
                "PHASE 16 COMPLETE"
            )

            print(
                "PDF generation: SUCCESS"
            )

            print(
                f"Logical pages : "
                f"{self.expected_pages}"
            )

            print(
                f"Physical pages: "
                f"{self.expected_pages}"
            )

            print(
                f"PDF output    : "
                f"{self.pdf_path}"
            )

            return self.pdf_path

        except Exception:

            print(
                "\nPHASE 16 FAILED."
            )

            raise


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():

    generator = PDFGenerator()

    generator.run()


if __name__ == "__main__":
    main()