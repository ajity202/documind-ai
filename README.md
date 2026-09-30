# DocuMind AI V2

## Features
- Multiple PDF documents
- Persistent FAISS vector index
- Page-aware chunks and sources
- OCR fallback for scanned PDFs
- Document deletion
- Persistent browser chat history
- Gemini 3.5 Flash-Lite
- 429 quota and 503 retry handling

## Run backend

```bash
uvicorn backend.main:app --reload
```

## Run frontend

From the project root:

```bash
python -m http.server 5500 --directory frontend
```

Open:

http://127.0.0.1:5500

## OCR note

The Python package `pytesseract` requires the Tesseract OCR application to be installed on Windows for scanned PDFs. Normal text PDFs do not require OCR.
