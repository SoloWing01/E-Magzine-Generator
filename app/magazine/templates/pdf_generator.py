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

# pdf_generator.py
# app/magazine/templates/pdf_generator.py
#
# parents[0] -> templates
# parents[1] -> magazine
# parents[2] -> app
# parents[3] -> project root

BASE_DIR = Path(__file__).resolve().parents[3]

OUTPUT_DIR = BASE_DIR / "data" / "output"

HTML_PATH = OUTPUT_DIR / "northeast_sentinel_magazine.html"
PDF_PATH = OUTPUT_DIR / "northeast_sentinel_magazine.pdf"

EXPECTED_PAGES = 50


# ============================================================================
# PDF CSS
# ============================================================================
#
# IMPORTANT:
# This stylesheet is deliberately conservative.
#
# render_magazine.py already prepares the HTML and converts:
#
#   data/images/...  -> ../images/...
#   data/charts/...  -> ../charts/...
#
# The PDF generator should therefore preserve the HTML magazine layout
# instead of rebuilding or replacing its alignment.
#
# The main purpose of this CSS is:
#   1. Define A4 physical pages.
#   2. Preserve .magazine-page boundaries.
#   3. Prevent accidental page splitting.
#   4. Preserve the existing magazine margins/padding.
#   5. Keep images and charts inside their containers.
#   6. Hide elements marked .no-print.
#
# ============================================================================

PDF_CSS = """
<style id="pdf-magazine-normalization">

/* =========================================================================
   A4 PAGE
   ========================================================================= */

@page {
    size: A4;
    margin: 0;
}


/* =========================================================================
   DOCUMENT ROOT
   ========================================================================= */

html,
body {
    margin: 0 !important;
    padding: 0 !important;

    width: 210mm !important;

    background: white !important;
}


/* =========================================================================
   GLOBAL BOX MODEL
   ========================================================================= */

*,
*::before,
*::after {
    box-sizing: border-box !important;
}


/* =========================================================================
   MAGAZINE PAGE
   ========================================================================= */

/*
   IMPORTANT:

   Do NOT set padding to zero here.

   The actual magazine template is responsible for the visual alignment,
   margins, typography and spacing.

   We only enforce the physical A4 dimensions and page breaking.
*/

.magazine-page {

    width: 210mm !important;
    min-width: 210mm !important;
    max-width: 210mm !important;

    height: 297mm !important;
    min-height: 297mm !important;
    max-height: 297mm !important;

    margin: 0 !important;

    position: relative !important;

    overflow: hidden !important;

    box-sizing: border-box !important;

    break-before: auto !important;
    break-after: page !important;
    break-inside: avoid !important;

    page-break-before: auto !important;
    page-break-after: always !important;
    page-break-inside: avoid !important;
}


/* =========================================================================
   LAST PAGE
   ========================================================================= */

.magazine-page:last-child {

    break-after: auto !important;

    page-break-after: auto !important;
}


/* =========================================================================
   COVER
   ========================================================================= */

.cover-page {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   INSIDE COVER
   ========================================================================= */

.inside-cover {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   SECTION PAGE
   ========================================================================= */

.section-page {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   ARTICLE PAGE
   ========================================================================= */

.article-page {

    width: 210mm !important;

    height: 297mm !important;

    min-height: 297mm !important;

    max-height: 297mm !important;

    break-inside: avoid !important;

    page-break-inside: avoid !important;

    overflow: hidden !important;
}


/* =========================================================================
   ARTICLE HEADER
   ========================================================================= */

.article-header {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   ARTICLE TITLE
   ========================================================================= */

.article-title {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   ARTICLE META
   ========================================================================= */

.article-meta {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   ARTICLE IMAGE
   ========================================================================= */

.article-image {

    display: block !important;

    max-width: 100% !important;

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   ARTICLE BODY
   ========================================================================= */

/*
   Do NOT give the article body an arbitrary fixed max-height.

   The page builder already divides articles into page-sized body chunks.
   render_magazine.py explicitly prepares:

       prepared["content"] = prepared["body_chunk"]

   Therefore the body chunk should be allowed to use the space allocated
   by the magazine template.
*/

.article-body,
.article-content,
.article-text {

    max-width: 100% !important;

    box-sizing: border-box !important;
}


/* =========================================================================
   ARTICLE PARAGRAPHS
   ========================================================================= */

.article-body p,
.article-content p,
.article-text p {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   ARTICLE HEADINGS
   ========================================================================= */

.article-body h1,
.article-body h2,
.article-body h3,
.article-body h4,
.article-content h1,
.article-content h2,
.article-content h3,
.article-content h4,
.article-text h1,
.article-text h2,
.article-text h3,
.article-text h4 {

    break-after: avoid !important;

    page-break-after: avoid !important;

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   SOURCE BOX
   ========================================================================= */

.source-box {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   IMAGES
   ========================================================================= */

.magazine-page img {

    max-width: 100% !important;

    box-sizing: border-box !important;

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   ARTICLE IMAGES
   ========================================================================= */

.article-image img {

    max-width: 100% !important;

    height: auto !important;

    display: block !important;
}


/* =========================================================================
   FIGURES
   ========================================================================= */

.magazine-page figure {

    max-width: 100% !important;

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   TABLES
   ========================================================================= */

.magazine-page table {

    width: 100% !important;

    max-width: 100% !important;

    border-collapse: collapse !important;

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   TABLE ROWS
   ========================================================================= */

.magazine-page tr {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   CHART PAGES
   ========================================================================= */

.chart-page {

    width: 210mm !important;

    height: 297mm !important;

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   CHART IMAGES
   ========================================================================= */

.chart-page .chart-image {

    display: block !important;

    max-width: 100% !important;

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   ANALYTICS
   ========================================================================= */

.analytics-page {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   CONTENTS / TOC
   ========================================================================= */

.contents-page,
.toc-page {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   SOURCE PAGE
   ========================================================================= */

.source-page {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   METHODOLOGY PAGE
   ========================================================================= */

.methodology-page {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   PIPELINE PAGE
   ========================================================================= */

.pipeline-page {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   BACK COVER
   ========================================================================= */

.back-cover {

    break-inside: avoid !important;

    page-break-inside: avoid !important;
}


/* =========================================================================
   PRINT-ONLY CONTROL
   ========================================================================= */

.no-print {

    display: none !important;
}


/* =========================================================================
   LINKS
   ========================================================================= */

a {

    text-decoration: none !important;
}


/* =========================================================================
   TEXT SAFETY
   ========================================================================= */

.magazine-page {

    overflow-wrap: break-word !important;

    word-wrap: break-word !important;
}


/* =========================================================================
   PREVENT HORIZONTAL OVERFLOW
   ========================================================================= */

.magazine-page > * {

    max-width: 100% !important;
}


/* =========================================================================
   PDF PAGE SAFETY
   ========================================================================= */

@media print {

    html,
    body {

        width: 210mm !important;

        margin: 0 !important;

        padding: 0 !important;
    }

    .magazine-page {

        width: 210mm !important;

        height: 297mm !important;

        margin: 0 !important;
    }
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


    # =========================================================================
    # LOGGING
    # =========================================================================

    @staticmethod
    def header(title: str):

        print(
            "\n" + "=" * 70,
            flush=True,
        )

        print(
            title,
            flush=True,
        )

        print(
            "=" * 70,
            flush=True,
        )


    # =========================================================================
    # LOAD HTML
    # =========================================================================

    def load_html(self):

        self.header(
            "CHECKING HTML INPUT"
        )

        if not self.html_path.exists():

            raise FileNotFoundError(
                "HTML input not found:\n"
                f"{self.html_path}"
            )

        self.html_content = (
            self.html_path.read_text(
                encoding="utf-8"
            )
        )

        size_kb = (
            self.html_path.stat().st_size
            / 1024
        )

        print(
            f"HTML input : {self.html_path}",
            flush=True,
        )

        print(
            f"HTML size  : {size_kb:.2f} KB",
            flush=True,
        )


    # =========================================================================
    # HTML STRUCTURE
    # =========================================================================

    def validate_html_pages(self):

        self.header(
            "VALIDATING HTML PAGE STRUCTURE"
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
            f"HTML logical pages: {count}",
            flush=True,
        )

        if count != self.expected_pages:

            raise ValueError(
                "\n"
                "HTML PAGE COUNT MISMATCH\n"
                f"Expected : {self.expected_pages}\n"
                f"Actual   : {count}\n"
            )

        print(
            "HTML page count: PASSED",
            flush=True,
        )


    # =========================================================================
    # ASSET HELPERS
    # =========================================================================

    @staticmethod
    def is_external_asset(
        asset: str,
    ) -> bool:

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

        asset = asset.split(
            "#",
            1,
        )[0]

        asset = asset.split(
            "?",
            1,
        )[0]

        asset = asset.replace(
            "%20",
            " ",
        )

        candidates = []

        path = Path(asset)

        if path.is_absolute():

            candidates.append(
                path
            )

        # ---------------------------------------------------------
        # FIRST:
        # Resolve relative to the generated HTML.
        #
        # Example:
        #
        # HTML:
        # data/output/northeast_sentinel_magazine.html
        #
        # src:
        # ../images/article_29/image.jpg
        #
        # resolves to:
        # data/images/article_29/image.jpg
        # ---------------------------------------------------------

        candidates.append(
            self.html_path.parent / asset
        )

        # ---------------------------------------------------------
        # SECOND:
        # Project-relative path.
        # ---------------------------------------------------------

        candidates.append(
            BASE_DIR / asset
        )

        # ---------------------------------------------------------
        # THIRD:
        # Remove leading ./ if present.
        # ---------------------------------------------------------

        candidates.append(
            BASE_DIR / asset.lstrip("./")
        )

        for candidate in candidates:

            if candidate.exists():

                return candidate.resolve()

        return None


    # =========================================================================
    # ASSET VALIDATION
    # =========================================================================

    def validate_assets(self):

        self.header(
            "VALIDATING HTML ASSETS"
        )

        if self.soup is None:

            raise RuntimeError(
                "HTML has not been parsed."
            )

        image_elements = (
            self.soup.find_all("img")
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

            resolved = self.resolve_asset(
                src
            )

            if resolved is None:

                missing_assets.append(
                    src
                )

        print(
            f"Image elements found : "
            f"{len(image_elements)}",
            flush=True,
        )

        print(
            f"Local assets checked : "
            f"{local_assets}",
            flush=True,
        )

        print(
            f"External/data assets : "
            f"{external_assets}",
            flush=True,
        )

        print(
            f"Missing assets       : "
            f"{len(missing_assets)}",
            flush=True,
        )

        if missing_assets:

            print(
                "\nMissing assets:",
                flush=True,
            )

            for asset in missing_assets:

                print(
                    f"  - {asset}",
                    flush=True,
                )

            raise FileNotFoundError(
                "Missing local HTML assets."
            )

        print(
            "Asset validation: PASSED",
            flush=True,
        )


    # =========================================================================
    # CSS INSPECTION
    # =========================================================================

    def inspect_original_css(self):

        self.header(
            "INSPECTING ORIGINAL HTML CSS"
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
            f"{'FOUND' if a4_found else 'NOT FOUND'}",
            flush=True,
        )

        print(
            "Original page-break CSS: "
            f"{'FOUND' if page_break_found else 'NOT FOUND'}",
            flush=True,
        )


    # =========================================================================
    # PREPARE PDF HTML
    # =========================================================================

    def prepare_pdf_html(self):

        self.header(
            "PREPARING PDF HTML"
        )

        if self.html_content is None:

            raise RuntimeError(
                "HTML has not been loaded."
            )

        html = self.html_content

        # ---------------------------------------------------------------------
        # Remove an older PDF stylesheet if the HTML already contains one.
        # This prevents multiple PDF normalization blocks from accumulating.
        # ---------------------------------------------------------------------

        html = re.sub(
            r'<style[^>]*id=["\']pdf-normalization["\'][^>]*>'
            r'.*?</style>',
            "",
            html,
            flags=(
                re.IGNORECASE
                | re.DOTALL
            ),
        )

        html = re.sub(
            r'<style[^>]*id=["\']pdf-magazine-normalization["\'][^>]*>'
            r'.*?</style>',
            "",
            html,
            flags=(
                re.IGNORECASE
                | re.DOTALL
            ),
        )

        # ---------------------------------------------------------------------
        # Add PDF CSS at the end of the document.
        #
        # It is deliberately limited so that the magazine template remains
        # responsible for the visual formatting.
        # ---------------------------------------------------------------------

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
            "PDF CSS normalization: APPLIED",
            flush=True,
        )


    # =========================================================================
    # GENERATE PDF
    # =========================================================================

    def generate_pdf(self):

        self.header(
            "GENERATING PDF WITH WEASYPRINT"
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
            f"Input HTML : {self.html_path}",
            flush=True,
        )

        print(
            f"Output PDF : {self.pdf_path}",
            flush=True,
        )

        print(
            "Creating WeasyPrint document...",
            flush=True,
        )

        try:

            # -------------------------------------------------------------
            # IMPORTANT:
            #
            # render_magazine.py converts:
            #
            # data/images/example.jpg
            #
            # into:
            #
            # ../images/example.jpg
            #
            # because the final HTML is stored in:
            #
            # data/output/
            #
            # Therefore the correct base_url is the HTML directory:
            #
            # data/output/
            # -------------------------------------------------------------

            document = HTML(
                string=self.pdf_html,
                base_url=str(
                    self.html_path.parent
                ),
            )

            print(
                "WeasyPrint document created.",
                flush=True,
            )

            print(
                "Writing PDF...",
                flush=True,
            )

            document.write_pdf(
                target=str(
                    self.pdf_path
                )
            )

            print(
                "WeasyPrint finished.",
                flush=True,
            )

        except Exception as exc:

            print(
                "\nWEASYPRINT ERROR",
                flush=True,
            )

            print(
                f"Error type: {type(exc).__name__}",
                flush=True,
            )

            print(
                f"Error     : {exc}",
                flush=True,
            )

            raise

        if not self.pdf_path.exists():

            raise RuntimeError(
                "PDF was not created:\n"
                f"{self.pdf_path}"
            )

        file_size_mb = (
            self.pdf_path.stat().st_size
            / (1024 * 1024)
        )

        if self.pdf_path.stat().st_size == 0:

            raise RuntimeError(
                "PDF file was created but is empty."
            )

        print(
            "\nPDF generated successfully.",
            flush=True,
        )

        print(
            f"PDF path : {self.pdf_path}",
            flush=True,
        )

        print(
            f"PDF size : {file_size_mb:.2f} MB",
            flush=True,
        )


    # =========================================================================
    # PDF FILE VALIDATION
    # =========================================================================

    def validate_pdf_file(self):

        self.header(
            "VALIDATING PDF FILE"
        )

        if not self.pdf_path.exists():

            raise FileNotFoundError(
                self.pdf_path
            )

        file_size = (
            self.pdf_path.stat().st_size
        )

        print(
            f"PDF file size: "
            f"{file_size / (1024 * 1024):.2f} MB",
            flush=True,
        )

        if file_size == 0:

            raise ValueError(
                "PDF file is empty."
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
            "PDF header: PASSED",
            flush=True,
        )


    # =========================================================================
    # PDF PAGE COUNT
    # =========================================================================

    def get_pdf_page_count(self):

        if PdfReader is None:

            raise RuntimeError(
                "pypdf is required for PDF validation."
            )

        reader = PdfReader(
            str(self.pdf_path)
        )

        return len(
            reader.pages
        )


    # =========================================================================
    # PAGE VALIDATION
    # =========================================================================

    def validate_pdf_pages(self):

        self.header(
            "VALIDATING PHYSICAL PDF PAGE COUNT"
        )

        page_count = (
            self.get_pdf_page_count()
        )

        print(
            "Page-count method: pypdf",
            flush=True,
        )

        print(
            f"Expected pages   : "
            f"{self.expected_pages}",
            flush=True,
        )

        print(
            f"Physical pages   : "
            f"{page_count}",
            flush=True,
        )

        if page_count != self.expected_pages:

            raise ValueError(
                "\n"
                "PDF PAGE COUNT MISMATCH\n"
                f"Expected : "
                f"{self.expected_pages}\n"
                f"Actual   : "
                f"{page_count}\n"
            )

        print(
            "PDF page count: PASSED",
            flush=True,
        )


    # =========================================================================
    # PDF DIAGNOSTIC
    # =========================================================================

    def diagnose_pdf(self):

        self.header(
            "PDF PAGE DIAGNOSTIC"
        )

        if PdfReader is None:

            print(
                "pypdf unavailable.",
                flush=True,
            )

            return

        reader = PdfReader(
            str(self.pdf_path)
        )

        actual_pages = len(
            reader.pages
        )

        print(
            f"Physical pages: "
            f"{actual_pages}",
            flush=True,
        )

        print(
            f"Expected pages : "
            f"{self.expected_pages}",
            flush=True,
        )

        print(
            "\nPhysical page mapping:",
            flush=True,
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

                preview = text[:180]

            except Exception as exc:

                preview = (
                    "<extraction error: "
                    f"{exc}>"
                )

            print(
                f"{number:03d} | "
                f"{preview}",
                flush=True,
            )


    # =========================================================================
    # OUTPUT INFORMATION
    # =========================================================================

    def print_output_information(self):

        self.header(
            "PDF OUTPUT"
        )

        print(
            f"HTML : {self.html_path}",
            flush=True,
        )

        print(
            f"PDF  : {self.pdf_path}",
            flush=True,
        )

        if self.pdf_path.exists():

            size_mb = (
                self.pdf_path.stat().st_size
                / (1024 * 1024)
            )

            print(
                f"Size : {size_mb:.2f} MB",
                flush=True,
            )


    # =========================================================================
    # COMPLETE PIPELINE
    # =========================================================================

    def run(self):

        self.header(
            "PHASE 16 — PDF GENERATION"
        )

        try:

            # -------------------------------------------------------------
            # 1. Load the HTML generated by render_magazine.py
            # -------------------------------------------------------------

            self.load_html()

            # -------------------------------------------------------------
            # 2. Verify that render_magazine.py produced 50 logical pages
            # -------------------------------------------------------------

            self.validate_html_pages()

            # -------------------------------------------------------------
            # 3. Verify all local image assets
            # -------------------------------------------------------------

            self.validate_assets()

            # -------------------------------------------------------------
            # 4. Inspect the existing HTML CSS
            # -------------------------------------------------------------

            self.inspect_original_css()

            # -------------------------------------------------------------
            # 5. Add minimal PDF-specific rules
            # -------------------------------------------------------------

            self.prepare_pdf_html()

            # -------------------------------------------------------------
            # 6. Generate physical PDF
            # -------------------------------------------------------------

            self.generate_pdf()

            # -------------------------------------------------------------
            # 7. Validate PDF header/file
            # -------------------------------------------------------------

            self.validate_pdf_file()

            # -------------------------------------------------------------
            # 8. Validate physical page count
            # -------------------------------------------------------------

            try:

                self.validate_pdf_pages()

            except ValueError:

                self.diagnose_pdf()

                raise

            # -------------------------------------------------------------
            # SUCCESS
            # -------------------------------------------------------------

            self.header(
                "PHASE 16 COMPLETE"
            )

            print(
                "PDF generation: SUCCESS",
                flush=True,
            )

            print(
                f"Logical pages : "
                f"{self.expected_pages}",
                flush=True,
            )

            print(
                f"Physical pages: "
                f"{self.expected_pages}",
                flush=True,
            )

            print(
                f"PDF output    : "
                f"{self.pdf_path}",
                flush=True,
            )

            self.print_output_information()

            return self.pdf_path

        except Exception as exc:

            print(
                "\n" + "=" * 70,
                flush=True,
            )

            print(
                "PHASE 16 FAILED",
                flush=True,
            )

            print(
                "=" * 70,
                flush=True,
            )

            print(
                f"Error type: "
                f"{type(exc).__name__}",
                flush=True,
            )

            print(
                f"Error: {exc}",
                flush=True,
            )

            raise


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():

    print(
        "\nStarting PDF generator...",
        flush=True,
    )

    print(
        f"Project root: {BASE_DIR}",
        flush=True,
    )

    print(
        f"HTML input  : {HTML_PATH}",
        flush=True,
    )

    print(
        f"PDF output  : {PDF_PATH}",
        flush=True,
    )

    generator = PDFGenerator()

    generator.run()


if __name__ == "__main__":

    main()