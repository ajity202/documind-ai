import io

import pymupdf

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None


# =========================================================
# EXTRACT PAGES FROM PDF
# =========================================================

def extract_pages_from_pdf(pdf_path):

    document = pymupdf.open(pdf_path)

    pages = []

    for page_number, page in enumerate(
        document,
        start=1
    ):

        # Try normal PDF text extraction first
        text = page.get_text("text").strip()

        # OCR fallback for scanned/image-only pages
        if not text and pytesseract and Image:

            try:

                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2)
                )

                image_bytes = pixmap.tobytes("png")

                image = Image.open(
                    io.BytesIO(image_bytes)
                )

                text = (
                    pytesseract
                    .image_to_string(image)
                    .strip()
                )

            except Exception as error:

                print(
                    f"OCR failed on page "
                    f"{page_number}: {error}"
                )

        if text:

            pages.append({
                "page": page_number,
                "text": text
            })

    document.close()

    return pages


# =========================================================
# EXTRACT COMPLETE TEXT FROM PDF
# =========================================================

def extract_text_from_pdf(pdf_path):

    pages = extract_pages_from_pdf(
        pdf_path
    )

    text_parts = []

    for page in pages:

        text_parts.append(
            page["text"]
        )

    return "\n\n".join(
        text_parts
    )