from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import os
import sys
import uuid

# =========================================================
# PYTHON PATH
# =========================================================

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# =========================================================
# LOCAL MODULES
# =========================================================

from src.pdf_reader import extract_pages_from_pdf
from src.chunker import chunk_text
from src.embeddings import create_embeddings
from src.retriever import Retriever
from src.qa import generate_answer, generate_document_suggestions


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Intelligent Document QA"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

UPLOAD_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "uploads"
)

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# =========================================================
# RETRIEVER
# =========================================================

retriever = Retriever()


# =========================================================
# CURRENT DOCUMENT SUGGESTIONS
# =========================================================

suggested_questions = []


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message": "Document QA API is running"
    }


# =========================================================
# UPLOAD DOCUMENT
# =========================================================

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    global suggested_questions

    # -----------------------------------------------------
    # Validate file
    # -----------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # -----------------------------------------------------
    # Generate document ID
    # -----------------------------------------------------

    document_id = str(
        uuid.uuid4()
    )

    original_filename = file.filename

    saved_filename = (
        f"{document_id}_{original_filename}"
    )

    file_path = os.path.join(
        UPLOAD_DIR,
        saved_filename
    )

    # -----------------------------------------------------
    # Save uploaded PDF
    # -----------------------------------------------------

    file_data = await file.read()

    file_size = len(file_data)

    with open(
        file_path,
        "wb"
    ) as buffer:

        buffer.write(file_data)

    # -----------------------------------------------------
    # Extract pages + OCR
    # -----------------------------------------------------

    pages = extract_pages_from_pdf(
        file_path
    )

    if not pages:

        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract text from the PDF. "
                "The document may be empty or unreadable."
            )
        )

    # -----------------------------------------------------
    # Create page-aware chunks
    # -----------------------------------------------------

    chunk_records = []
    chunk_texts = []

    for page in pages:

        page_number = page["page"]
        page_text = page["text"]

        page_chunks = chunk_text(
            page_text
        )

        for chunk in page_chunks:

            chunk = chunk.strip()

            if not chunk:
                continue

            chunk_records.append({
                "document_id": document_id,
                "document_name": original_filename,
                "page": page_number,
                "text": chunk
            })

            chunk_texts.append(
                chunk
            )

    if not chunk_records:

        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=400,
            detail="No usable text chunks were created."
        )

    # -----------------------------------------------------
    # Create Gemini embeddings
    # -----------------------------------------------------

    embeddings = create_embeddings(
        chunk_texts
    )

    # -----------------------------------------------------
    # Add document to vectorstore
    # -----------------------------------------------------

    retriever.add_document(
        document_id=document_id,
        filename=original_filename,
        file_size=file_size,
        chunks=chunk_records,
        embeddings=embeddings,
        page_count=len(pages)
    )

    # -----------------------------------------------------
    # Generate suggested questions
    # -----------------------------------------------------

    print(
        "Generating suggested questions..."
    )

    suggested_questions = (
        generate_document_suggestions(
            chunk_texts
        )
    )

    print(
        "Suggested questions:",
        suggested_questions
    )

    # -----------------------------------------------------
    # Get saved document
    # -----------------------------------------------------

    document = retriever.get_document(
        document_id
    )

    # -----------------------------------------------------
    # Return response
    # -----------------------------------------------------

    return {
        "message": "Document processed successfully",
        "document": document,
        "suggested_questions": suggested_questions
    }


# =========================================================
# GET ALL DOCUMENTS
# =========================================================

@app.get("/documents")
def get_documents():

    return {
        "documents": retriever.list_documents()
    }


# =========================================================
# GET SINGLE DOCUMENT
# =========================================================

@app.get("/documents/{document_id}")
def get_document(
    document_id: str
):

    document = retriever.get_document(
        document_id
    )

    if document is None:

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return {
        "document": document
    }


# =========================================================
# DELETE DOCUMENT
# =========================================================

@app.delete("/documents/{document_id}")
def delete_document(
    document_id: str
):

    global suggested_questions

    document = retriever.get_document(
        document_id
    )

    if document is None:

        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    # -----------------------------------------------------
    # Delete physical PDF
    # -----------------------------------------------------

    file_path = document.get(
        "path"
    )

    if file_path:

        if not os.path.isabs(file_path):

            file_path = os.path.join(
                PROJECT_ROOT,
                file_path
            )

        if os.path.exists(file_path):

            os.remove(
                file_path
            )

    # -----------------------------------------------------
    # Remove from vectorstore
    # -----------------------------------------------------

    retriever.delete_document(
        document_id
    )

    # -----------------------------------------------------
    # Clear suggestions
    # -----------------------------------------------------

    if not retriever.list_documents():

        suggested_questions = []

    return {
        "message": "Document deleted successfully",
        "document_id": document_id
    }


# =========================================================
# GET SUGGESTED QUESTIONS
# =========================================================

@app.get("/suggestions")
def get_suggestions():

    return {
        "suggested_questions": suggested_questions
    }


# =========================================================
# ASK QUESTION
# =========================================================

@app.post("/ask")
async def ask_question(
    question: str
):

    # -----------------------------------------------------
    # Validate question
    # -----------------------------------------------------

    if not question.strip():

        return {
            "question": question,
            "answer": "Please enter a question.",
            "sources": []
        }

    # -----------------------------------------------------
    # Check vectorstore
    # -----------------------------------------------------

    if retriever.index is None:

        return {
            "question": question,
            "answer": "Please upload a document first.",
            "sources": []
        }

    # -----------------------------------------------------
    # Create question embedding
    # -----------------------------------------------------

    question_embedding = create_embeddings(
        [question]
    )[0]

    # -----------------------------------------------------
    # Search relevant chunks
    # -----------------------------------------------------

    results = retriever.search(
        question_embedding,
        top_k=5
    )

    if not results:

        return {
            "question": question,
            "answer": (
                "I could not find relevant information "
                "in the documents."
            ),
            "sources": []
        }

    # -----------------------------------------------------
    # Create structured context
    # -----------------------------------------------------

    context_parts = []

    for result in results:

        context_parts.append(
            f"""
DOCUMENT: {result["document_name"]}

PAGE: {result["page"]}

CONTENT:
{result["text"]}
"""
        )

    context = "\n\n".join(
        context_parts
    )

    # -----------------------------------------------------
    # Generate answer
    # -----------------------------------------------------

    answer = generate_answer(
        question,
        context
    )

    # -----------------------------------------------------
    # Return response
    # -----------------------------------------------------

    return {
        "question": question,
        "answer": answer,
        "sources": results
    }