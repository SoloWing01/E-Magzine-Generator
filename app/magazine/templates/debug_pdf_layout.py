from pathlib import Path

from bs4 import BeautifulSoup
from weasyprint import HTML


BASE_DIR = Path(__file__).resolve().parents[3]

HTML_PATH = BASE_DIR / "data" / "output" / "northeast_sentinel_magazine.html"

print("=" * 70)
print("PDF LAYOUT DIAGNOSTIC")
print("=" * 70)

print(f"HTML: {HTML_PATH}")

if not HTML_PATH.exists():
    raise FileNotFoundError(f"HTML not found: {HTML_PATH}")

html_text = HTML_PATH.read_text(encoding="utf-8")

soup = BeautifulSoup(html_text, "html.parser")

logical_pages = soup.select(".magazine-page")

print(f"\nLogical HTML pages: {len(logical_pages)}")

for index, page in enumerate(logical_pages, 1):
    classes = page.get("class", [])
    page_type = page.get("data-page-type", "")
    text = " ".join(page.stripped_strings)

    print(
        f"{index:02d} | "
        f"class={classes} | "
        f"type={page_type} | "
        f"text={text[:100]}"
    )


print("\n" + "=" * 70)
print("RENDERING WITH WEASYPRINT")
print("=" * 70)

document = HTML(
    string=html_text,
    base_url=str(BASE_DIR),
).render()

print(f"Physical pages produced: {len(document.pages)}")


def walk_boxes(box, results):
    """
    Recursively inspect WeasyPrint layout boxes.
    """
    element = getattr(box, "element", None)

    if element is not None:
        classes = element.get("class", [])

        if "magazine-page" in classes:
            results.append(
                {
                    "box": box,
                    "element": element,
                    "height": getattr(box, "height", None),
                    "width": getattr(box, "width", None),
                    "x": getattr(box, "position_x", None),
                    "y": getattr(box, "position_y", None),
                }
            )

    for child in getattr(box, "children", []):
        walk_boxes(child, results)


print("\n" + "=" * 70)
print("PAGE BOX ANALYSIS")
print("=" * 70)

total_boxes = 0

for physical_page_number, page in enumerate(document.pages, 1):

    results = []

    walk_boxes(page._page_box, results)

    if not results:
        print(
            f"\nPDF PAGE {physical_page_number}: "
            f"NO .magazine-page BOX FOUND"
        )
        continue

    print(f"\nPDF PAGE {physical_page_number}")

    for item in results:

        total_boxes += 1

        element = item["element"]
        height = item["height"]
        width = item["width"]

        text = " ".join(
        part.strip()
        for part in element.itertext()
        if part.strip()
)

        print(
            f"  magazine-page"
            f" | height={height:.2f}px"
            f" | width={width:.2f}px"
            f" | x={item['x']:.2f}"
            f" | y={item['y']:.2f}"
        )

        print(f"  content: {text[:150]}")


print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Logical HTML pages : {len(logical_pages)}")
print(f"Physical PDF pages : {len(document.pages)}")
print(f"Magazine page boxes: {total_boxes}")

difference = len(document.pages) - len(logical_pages)

print(f"Pagination difference: {difference}")

if difference == 0:
    print("\nNO PAGINATION OVERFLOW DETECTED.")
else:
    print(
        "\nPAGINATION OVERFLOW DETECTED."
        "\nInspect the PDF PAGE entries above."
    )

print("=" * 70)
