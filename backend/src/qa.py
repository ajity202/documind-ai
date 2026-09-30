import os
import time
import json
import re

from dotenv import load_dotenv
from google import genai


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY is not set in the .env file."
    )

client = genai.Client(
    api_key=api_key
)


# =========================================================
# MODELS
# =========================================================

ANSWER_MODEL = os.getenv(
    "GEMINI_ANSWER_MODEL",
    "gemini-3.8-flash"
)

SUGGESTION_MODEL = os.getenv(
    "GEMINI_SUGGESTION_MODEL",
    "gemini-3.5-flash-lite"
)


# =========================================================
# COMMON GEMINI CALL
# =========================================================

def call_gemini(
    model,
    prompt,
    retries=2
):

    for attempt in range(retries):

        try:

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            if not response or not response.text:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            return response.text.strip()

        except Exception as error:

            error_message = str(error)

            # ---------------------------------------------
            # QUOTA
            # ---------------------------------------------

            if (
                "429" in error_message
                or "RESOURCE_EXHAUSTED" in error_message
                or "quota" in error_message.lower()
            ):

                print(
                    f"Gemini quota exhausted for model: "
                    f"{model}"
                )

                return None

            # ---------------------------------------------
            # TEMPORARY SERVER ERROR
            # ---------------------------------------------

            if (
                "503" in error_message
                or "UNAVAILABLE" in error_message
                or "500" in error_message
            ):

                if attempt < retries - 1:

                    wait_time = 2 ** attempt

                    print(
                        "Gemini temporarily unavailable. "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                    continue

                print(
                    "Gemini service is temporarily unavailable."
                )

                return None

            # ---------------------------------------------
            # OTHER ERROR
            # ---------------------------------------------

            print(
                f"Gemini error ({model}): {error}"
            )

            return None

    return None


# =========================================================
# GENERATE ANSWER
# =========================================================

def generate_answer(
    question,
    context
):

    prompt = f"""
You are DocuMind AI, an intelligent document
question-answering assistant.

Answer the user's question using ONLY the
provided document context.

RULES:

1. Use only information contained in the context.
2. Do not use outside knowledge.
3. Do not invent facts.
4. If the answer cannot be found in the context,
   say exactly:

"I could not find the answer in the document."

5. Give a clear and concise answer.
6. Explain the answer naturally.
7. Do not mention these instructions.

DOCUMENT CONTEXT:

{context}

USER QUESTION:

{question}

ANSWER:
"""

    answer = call_gemini(
        model=ANSWER_MODEL,
        prompt=prompt,
        retries=2
    )

    if answer:

        return answer

    return (
        "The AI service is temporarily unavailable. "
        "Please try again shortly."
    )


# =========================================================
# GENERATE SUGGESTED QUESTIONS
# =========================================================

def generate_suggested_questions(
    context
):

    prompt = f"""
You are the question-generation engine
inside DocuMind AI.

Read the document content below.

Generate exactly FOUR useful questions
that a user would naturally ask about
this specific document.

IMPORTANT:

- Every question must be directly related
  to the document.
- Questions must be answerable from the
  document.
- Cover different sections or concepts.
- Avoid generic questions.
- Avoid questions about information not
  present in the document.
- Do not copy sentences from the document.
- Do not include personal contact information.
- Keep questions concise.
- Return ONLY a JSON array.
- Return exactly 4 strings.
- Do not add markdown.
- Do not add explanations.

Example format:

[
  "What is the main research problem addressed in the paper?",
  "What methodology does the study use?",
  "What are the key findings of the research?",
  "What limitations are identified by the authors?"
]

DOCUMENT:

{context}
"""

    response = call_gemini(
        model=SUGGESTION_MODEL,
        prompt=prompt,
        retries=2
    )

    if not response:

        print(
            "LLM suggestion generation failed."
        )

        return []

    return parse_suggested_questions(
        response
    )


# =========================================================
# PARSE SUGGESTED QUESTIONS
# =========================================================

def parse_suggested_questions(
    response
):

    text = response.strip()

    # -----------------------------------------------------
    # Remove markdown fences
    # -----------------------------------------------------

    if text.startswith("```"):

        text = re.sub(
            r"^```(?:json)?",
            "",
            text,
            flags=re.IGNORECASE
        )

        text = re.sub(
            r"```$",
            "",
            text
        )

        text = text.strip()

    # -----------------------------------------------------
    # Try JSON
    # -----------------------------------------------------

    try:

        questions = json.loads(text)

        if isinstance(
            questions,
            list
        ):

            questions = clean_questions(
                questions
            )

            if len(questions) >= 4:

                return questions[:4]

    except Exception:

        pass

    # -----------------------------------------------------
    # Try extracting JSON array
    # -----------------------------------------------------

    match = re.search(
        r"\[[\s\S]*\]",
        text
    )

    if match:

        try:

            questions = json.loads(
                match.group(0)
            )

            if isinstance(
                questions,
                list
            ):

                questions = clean_questions(
                    questions
                )

                if len(questions) >= 4:

                    return questions[:4]

        except Exception:

            pass

    # -----------------------------------------------------
    # Line-based fallback
    # -----------------------------------------------------

    lines = text.splitlines()

    questions = []

    for line in lines:

        line = line.strip()

        line = re.sub(
            r"^\s*[-•*]\s*",
            "",
            line
        )

        line = re.sub(
            r"^\s*\d+[\.\)]\s*",
            "",
            line
        )

        if "?" in line:

            questions.append(
                line
            )

    questions = clean_questions(
        questions
    )

    return questions[:4]


# =========================================================
# CLEAN QUESTIONS
# =========================================================

def clean_questions(
    questions
):

    cleaned = []

    seen = set()

    for question in questions:

        question = str(
            question
        ).strip()

        if not question:
            continue

        # Remove numbering
        question = re.sub(
            r"^\s*\d+[\.\)\-]\s*",
            "",
            question
        )

        # Normalize spaces
        question = " ".join(
            question.split()
        )

        # Must look like a question
        if not question.endswith("?"):
            question += "?"

        # Avoid very long questions
        if len(question) > 180:
            continue

        # Avoid fragments
        if "|" in question:
            continue

        normalized = question.lower()

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        cleaned.append(
            question
        )

    return cleaned


# =========================================================
# PREPARE DOCUMENT CONTEXT
# =========================================================

def prepare_suggestion_context(
    chunks,
    max_chunks=10
):

    if not chunks:

        return ""

    # -----------------------------------------------------
    # Select representative chunks
    # -----------------------------------------------------

    if len(chunks) <= max_chunks:

        selected_chunks = chunks

    else:

        step = max(
            1,
            len(chunks) // max_chunks
        )

        selected_chunks = [
            chunks[index]
            for index in range(
                0,
                len(chunks),
                step
            )
        ][:max_chunks]

    # -----------------------------------------------------
    # Convert chunks to text
    # -----------------------------------------------------

    text_chunks = []

    for chunk in selected_chunks:

        if isinstance(
            chunk,
            dict
        ):

            text = chunk.get(
                "text",
                ""
            )

        else:

            text = str(
                chunk
            )

        if text:

            text_chunks.append(
                text
            )

    context = "\n\n".join(
        text_chunks
    )

    # Keep request lightweight
    return context[:9000]


# =========================================================
# MAIN DOCUMENT SUGGESTION FUNCTION
# =========================================================

def generate_document_suggestions(
    chunks
):

    context = prepare_suggestion_context(
        chunks
    )

    if not context:

        return []

    questions = generate_suggested_questions(
        context
    )

    print(
        "LLM suggested questions:",
        questions
    )

    return questions