const API_URL =
    window.location.port === "5500"
        ? "http://127.0.0.1:8000"
        : "/api";

const $ = id => document.getElementById(id);


// =========================================================
// ELEMENTS
// =========================================================

const fileInput = $("fileInput");
const dropZone = $("dropZone");

const documentsList = $("documentsList");
const documentCount = $("documentCount");

const viewAllDocuments = $("viewAllDocuments");
const documentsModal = $("documentsModal");
const closeDocuments = $("closeDocuments");
const allDocumentsList = $("allDocumentsList");

const questionInput = $("questionInput");
const askBtn = $("askBtn");

const chatArea = $("chatArea");

const followupInput = $("followupInput");
const followupBtn = $("followupBtn");

const clearChat = $("clearChat");

const loadingOverlay = $("loadingOverlay");
const loadingText = $("loadingText");

const historyNav = $("historyNav");
const pdfNav = $("pdfNav");
const settingsNav = $("settingsNav");

const historyModal = $("historyModal");
const closeHistory = $("closeHistory");
const historyList = $("historyList");


// =========================================================
// STATE
// =========================================================

let documents = [];
let chatHistory = [];
let suggestedQuestions = [];
let isProcessing = false;


// =========================================================
// LOAD CHAT HISTORY
// =========================================================

try {

    const saved = localStorage.getItem(
        "documind_chat_history"
    );

    chatHistory = saved
        ? JSON.parse(saved)
        : [];

    if (!Array.isArray(chatHistory)) {
        chatHistory = [];
    }

} catch {

    chatHistory = [];

}


// =========================================================
// INITIAL LOAD
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        await loadDocuments();

        await loadSuggestedQuestions();

    }
);


// =========================================================
// DOCUMENTS
// =========================================================

async function loadDocuments() {

    try {

        const response = await fetch(
            `${API_URL}/documents`
        );

        if (!response.ok) {

            throw new Error(
                "Backend connection failed."
            );

        }

        const data =
            await response.json();

        documents =
            Array.isArray(data.documents)
                ? data.documents
                : [];

    } catch (error) {

        console.warn(
            "Document loading:",
            error
        );

        documents = [];

    }

    renderDocuments();

}


// =========================================================
// RENDER DOCUMENTS
// =========================================================

function renderDocuments() {

    if (!documentCount) {
        return;
    }

    documentCount.textContent =
        `${documents.length} document${documents.length === 1 ? "" : "s"}`;

    documentsList.innerHTML = "";

    if (!documents.length) {

        documentsList.innerHTML = `
            <div class="no-documents">
                No documents uploaded yet.
            </div>
        `;

        return;

    }

    documents
        .slice(0, 3)
        .forEach(doc => {

            documentsList.appendChild(
                createDocumentCard(doc)
            );

        });

}


// =========================================================
// DOCUMENT CARD
// =========================================================

function createDocumentCard(doc) {

    const card =
        document.createElement("div");

    card.className =
        "document-card";

    card.innerHTML = `

        <div class="pdf-icon">
            PDF
        </div>

        <div class="document-info">

            <h3 title="${esc(doc.filename)}">
                ${esc(doc.filename)}
            </h3>

            <div class="document-meta">

                <span>
                    ${size(doc.size)}
                </span>

                <span>•</span>

                <span>
                    ${doc.pages || "?"} pages
                </span>

                <span>•</span>

                <span>
                    ${doc.chunks || "?"} chunks
                </span>

            </div>

        </div>

        <div class="document-status">

            <span class="status-dot"></span>

            Processed

        </div>

        <button
            class="delete-btn"
            title="Delete document"
            type="button"
        >
            🗑
        </button>

    `;

    const deleteButton =
        card.querySelector(
            ".delete-btn"
        );

    deleteButton.onclick = () =>
        deleteDocument(doc.id);

    return card;

}


// =========================================================
// VIEW ALL DOCUMENTS
// =========================================================

if (viewAllDocuments) {

    viewAllDocuments.onclick = () => {

        renderAllDocuments();

        documentsModal.style.display =
            "flex";

    };

}


if (closeDocuments) {

    closeDocuments.onclick = () => {

        documentsModal.style.display =
            "none";

    };

}


if (documentsModal) {

    documentsModal.onclick = event => {

        if (
            event.target ===
            documentsModal
        ) {

            documentsModal.style.display =
                "none";

        }

    };

}


function renderAllDocuments() {

    allDocumentsList.innerHTML = "";

    if (!documents.length) {

        allDocumentsList.innerHTML = `
            <div class="no-documents">
                No documents uploaded yet.
            </div>
        `;

        return;

    }

    documents.forEach(doc => {

        allDocumentsList.appendChild(
            createDocumentCard(doc)
        );

    });

}


// =========================================================
// DELETE DOCUMENT
// =========================================================

async function deleteDocument(id) {

    const doc =
        documents.find(
            item => item.id === id
        );

    if (!confirm(
        `Delete "${doc?.filename || "this document"}"?`
    )) {

        return;

    }

    showLoading(
        "Deleting document..."
    );

    try {

        const response =
            await fetch(
                `${API_URL}/documents/${id}`,
                {
                    method: "DELETE"
                }
            );

        const data =
            await jsonResponse(
                response
            );

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Delete failed."
            );

        }

        documents =
            documents.filter(
                item => item.id !== id
            );

        renderDocuments();
        renderAllDocuments();

        clearChatArea();

        await loadSuggestedQuestions();

    } catch (error) {

        console.error(error);

        alert(
            error.message ||
            "Unable to delete document."
        );

    } finally {

        hideLoading();

    }

}


// =========================================================
// FILE INPUT
// =========================================================

if (fileInput) {

    fileInput.onchange = () => {

        const file =
            fileInput.files[0];

        if (file) {

            validateAndUpload(file);

        }

    };

}


// =========================================================
// DRAG & DROP
// =========================================================

if (dropZone) {

    dropZone.ondragover = event => {

        event.preventDefault();

        dropZone.classList.add(
            "dragover"
        );

    };


    dropZone.ondragleave = () => {

        dropZone.classList.remove(
            "dragover"
        );

    };


    dropZone.ondrop = event => {

        event.preventDefault();

        dropZone.classList.remove(
            "dragover"
        );

        const file =
            [...event.dataTransfer.files]
                .find(file =>
                    file.type ===
                        "application/pdf" ||
                    file.name
                        .toLowerCase()
                        .endsWith(".pdf")
                );

        if (file) {

            validateAndUpload(file);

        } else {

            alert(
                "Only PDF files are supported."
            );

        }

    };

}


// =========================================================
// VALIDATE UPLOAD
// =========================================================

function validateAndUpload(file) {

    if (
        file.size >
        50 * 1024 * 1024
    ) {

        alert(
            "Maximum file size is 50MB."
        );

        return;

    }

    if (
        !file.name
            .toLowerCase()
            .endsWith(".pdf")
    ) {

        alert(
            "Please select a PDF file."
        );

        return;

    }

    uploadDocument(file);

}


// =========================================================
// UPLOAD DOCUMENT
// =========================================================

async function uploadDocument(file) {

    if (isProcessing) {
        return;
    }

    isProcessing = true;

    const form =
        new FormData();

    form.append(
        "file",
        file
    );

    showLoading(
        "Processing PDF, creating embeddings and generating questions..."
    );

    try {

        const response =
            await fetch(
                `${API_URL}/upload`,
                {
                    method: "POST",
                    body: form
                }
            );

        const data =
            await jsonResponse(
                response
            );

        if (!response.ok) {

            throw new Error(
                data.detail ||
                data.message ||
                "Upload failed."
            );

        }


        // -------------------------------------------------
        // Add uploaded document
        // -------------------------------------------------

        if (data.document) {

            documents =
                documents.filter(
                    item =>
                        item.id !==
                        data.document.id
                );

            documents.unshift(
                data.document
            );

        } else {

            await loadDocuments();

        }

        renderDocuments();
        renderAllDocuments();


        // -------------------------------------------------
        // Update suggested questions
        // -------------------------------------------------

        if (
            Array.isArray(
                data.suggested_questions
            )
        ) {

            suggestedQuestions =
                data.suggested_questions;

            renderSuggestedQuestions();

        } else {

            await loadSuggestedQuestions();

        }


        // -------------------------------------------------
        // Clear previous conversation
        // -------------------------------------------------

        clearChatArea();


    } catch (error) {

        console.error(
            "Upload error:",
            error
        );

        alert(
            `Could not process the document.\n\n${error.message}`
        );

    } finally {

        hideLoading();

        isProcessing = false;

        if (fileInput) {
            fileInput.value = "";
        }

    }

}


// =========================================================
// LOAD SUGGESTED QUESTIONS
// =========================================================

async function loadSuggestedQuestions() {

    try {

        const response =
            await fetch(
                `${API_URL}/suggestions`
            );

        if (!response.ok) {

            throw new Error(
                "Could not load suggestions."
            );

        }

        const data =
            await response.json();

        suggestedQuestions =
            Array.isArray(
                data.suggested_questions
            )
                ? data.suggested_questions
                : [];

    } catch (error) {

        console.warn(
            "Suggestion loading:",
            error
        );

        suggestedQuestions = [];

    }

    renderSuggestedQuestions();

}


// =========================================================
// RENDER SUGGESTED QUESTIONS
// =========================================================

function renderSuggestedQuestions() {

    const container =
        document.querySelector(
            ".suggested-grid"
        );

    if (!container) {
        return;
    }

    container.innerHTML = "";


    if (!suggestedQuestions.length) {

        container.innerHTML = `

            <div
                class="no-suggestions"
                style="
                    grid-column:1/-1;
                    text-align:center;
                    padding:14px;
                    color:#8190a5;
                    font-size:11px;
                "
            >
                Upload a document to generate
                document-specific questions.
            </div>

        `;

        return;

    }


    suggestedQuestions
        .slice(0, 4)
        .forEach(question => {

            const button =
                document.createElement(
                    "button"
                );

            button.type = "button";

            button.className =
                "suggestion";

            button.textContent =
                question;

            button.onclick = () => {

                questionInput.value =
                    question;

                askQuestion(
                    question
                );

            };

            container.appendChild(
                button
            );

        });

}


// =========================================================
// ASK BUTTON
// =========================================================

if (askBtn) {

    askBtn.onclick = () => {

        askQuestion(
            questionInput.value
        );

    };

}


// =========================================================
// QUESTION INPUT
// =========================================================

if (questionInput) {

    questionInput.onkeydown =
        event => {

            if (
                event.key ===
                "Enter"
            ) {

                event.preventDefault();

                askQuestion(
                    questionInput.value
                );

            }

        };

}


// =========================================================
// ASK QUESTION
// =========================================================

async function askQuestion(
    question
) {

    question =
        String(
            question || ""
        ).trim();

    if (!question) {
        return;
    }

    if (isProcessing) {
        return;
    }

    if (!documents.length) {

        alert(
            "Please upload a PDF first."
        );

        return;

    }


    isProcessing = true;


    const empty =
        chatArea.querySelector(
            ".empty-chat"
        );

    if (empty) {
        empty.remove();
    }


    addUserMessage(
        question
    );


    questionInput.value = "";


    showLoading(
        "Searching documents and generating an answer..."
    );


    try {

        const response =
            await fetch(
                `${API_URL}/ask?question=${encodeURIComponent(question)}`,
                {
                    method: "POST"
                }
            );

        const data =
            await jsonResponse(
                response
            );

        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Unable to generate answer."
            );

        }


        addAIMessage(
            data.answer,
            data.sources || []
        );


        saveHistory(
            question,
            data.answer,
            data.sources || []
        );


    } catch (error) {

        console.error(
            "Question error:",
            error
        );

        addAIMessage(
            `⚠️ ${
                error.message ||
                "The AI service could not generate an answer."
            }`,
            []
        );

    } finally {

        hideLoading();

        isProcessing = false;

    }

}


// =========================================================
// CHAT - USER MESSAGE
// =========================================================

function addUserMessage(
    text
) {

    const message =
        document.createElement(
            "div"
        );

    message.className =
        "message user";

    message.innerHTML = `

        <div class="message-content">
            ${esc(text)}
        </div>

        <div class="message-icon user-icon">
            👤
        </div>

    `;

    chatArea.appendChild(
        message
    );

    scrollChat();

}


// =========================================================
// CHAT - AI MESSAGE
// =========================================================

function addAIMessage(
    answer,
    sources
) {

    const message =
        document.createElement(
            "div"
        );

    message.className =
        "message ai";


    const box =
        document.createElement(
            "div"
        );

    box.className =
        "answer-with-sources";


    box.innerHTML = `

        <div class="message-content">
            ${formatAnswer(answer)}
        </div>

        ${
            sources.length
                ? `
                    <button
                        class="sources-toggle"
                        type="button"
                    >
                        📚 ${sources.length}
                        Source${sources.length === 1 ? "" : "s"} ▼
                    </button>

                    <div
                        class="inline-sources"
                        style="display:none"
                    ></div>
                `
                : ""
        }

    `;


    message.innerHTML = `

        <div class="message-icon ai-icon">
            🤖
        </div>

    `;


    message.appendChild(
        box
    );

    chatArea.appendChild(
        message
    );


    // -----------------------------------------------------
    // Render sources
    // -----------------------------------------------------

    if (sources.length) {

        const toggle =
            box.querySelector(
                ".sources-toggle"
            );

        const list =
            box.querySelector(
                ".inline-sources"
            );


        sources.forEach(
            (source, index) => {

                const text =
                    typeof source === "string"
                        ? source
                        : source.text || "";


                const item =
                    document.createElement(
                        "div"
                    );

                item.className =
                    "inline-source";


                const documentName =
                    typeof source === "object"
                        ? source.document_name ||
                          "Document"
                        : "Document";


                const page =
                    typeof source === "object"
                        ? source.page ||
                          "N/A"
                        : "N/A";


                item.innerHTML = `

                    <div class="source-number">
                        ${index + 1}
                    </div>

                    <div class="source-body">

                        <strong>
                            Document Source
                        </strong>

                        <div
                            class="source-file"
                            title="${esc(documentName)}"
                        >
                            📄 ${esc(documentName)}
                        </div>

                        <div class="source-preview">

                            ${esc(
                                text.slice(
                                    0,
                                    150
                                )
                            )}

                            ${
                                text.length > 150
                                    ? "..."
                                    : ""
                            }

                        </div>

                    </div>

                    <div class="source-page">
                        Page ${page}
                    </div>

                `;


                list.appendChild(
                    item
                );

            }
        );


        // -------------------------------------------------
        // Source toggle
        // -------------------------------------------------

        toggle.onclick = () => {

            const hidden =
                list.style.display ===
                "none";


            list.style.display =
                hidden
                    ? "block"
                    : "none";


            toggle.innerHTML =
                hidden
                    ? `
                        📚 ${sources.length}
                        Source${sources.length === 1 ? "" : "s"} ▲
                    `
                    : `
                        📚 ${sources.length}
                        Source${sources.length === 1 ? "" : "s"} ▼
                    `;

        };

    }


    scrollChat();

}


// =========================================================
// FOLLOW-UP QUESTION
// =========================================================

if (followupBtn) {

    followupBtn.onclick = () => {

        const question =
            followupInput.value.trim();

        if (!question) {
            return;
        }

        followupInput.value = "";

        askQuestion(
            question
        );

    };

}


if (followupInput) {

    followupInput.onkeydown =
        event => {

            if (
                event.key ===
                "Enter"
            ) {

                event.preventDefault();

                followupBtn.click();

            }

        };

}


// =========================================================
// CLEAR CHAT
// =========================================================

if (clearChat) {

    clearChat.onclick =
        clearChatArea;

}


function clearChatArea() {

    chatArea.innerHTML = `

        <div class="empty-chat">

            <div class="empty-icon">
                🤖
            </div>

            <h3>
                Ask your first question
            </h3>

            <p>
                Upload a document and ask a question
                to start the conversation.
            </p>

        </div>

    `;

}


// =========================================================
// CHAT HISTORY
// =========================================================

function saveHistory(
    question,
    answer,
    sources
) {

    chatHistory.unshift({

        question,
        answer,
        sources,

        timestamp:
            new Date().toISOString()

    });


    chatHistory =
        chatHistory.slice(
            0,
            50
        );


    localStorage.setItem(
        "documind_chat_history",
        JSON.stringify(
            chatHistory
        )
    );

}


// =========================================================
// HISTORY MODAL
// =========================================================

if (historyNav) {

    historyNav.onclick = () => {

        renderHistory();

        historyModal.style.display =
            "flex";

    };

}


if (closeHistory) {

    closeHistory.onclick = () => {

        historyModal.style.display =
            "none";

    };

}


if (historyModal) {

    historyModal.onclick = event => {

        if (
            event.target ===
            historyModal
        ) {

            historyModal.style.display =
                "none";

        }

    };

}


// =========================================================
// RENDER HISTORY
// =========================================================

function renderHistory() {

    historyList.innerHTML = "";


    if (!chatHistory.length) {

        historyList.innerHTML = `

            <div class="history-empty">
                No chat history yet.
            </div>

        `;

        return;

    }


    chatHistory.forEach(
        item => {

            const element =
                document.createElement(
                    "div"
                );

            element.className =
                "history-item";


            const answer =
                String(
                    item.answer || ""
                );


            element.innerHTML = `

                <strong>
                    ${esc(item.question)}
                </strong>

                <p>
                    ${esc(
                        answer.slice(
                            0,
                            280
                        )
                    )}

                    ${
                        answer.length > 280
                            ? "..."
                            : ""
                    }
                </p>

                <small>
                    ${
                        item.timestamp
                            ? new Date(
                                item.timestamp
                              ).toLocaleString()
                            : ""
                    }
                </small>

            `;


            historyList.appendChild(
                element
            );

        }
    );

}


// =========================================================
// NAVIGATION
// =========================================================

if (pdfNav) {

    pdfNav.onclick = () => {

        document
            .querySelectorAll(
                ".nav-item"
            )
            .forEach(
                item =>
                    item.classList.remove(
                        "active"
                    )
            );

        pdfNav.classList.add(
            "active"
        );

        const dashboard =
            $("dashboard");

        if (dashboard) {

            dashboard.scrollIntoView({
                behavior: "smooth"
            });

        }

    };

}


if (settingsNav) {

    settingsNav.onclick = () => {

        const answerModel =
            localStorage.getItem(
                "documind_answer_model"
            ) ||
            "Gemini 3.5 Flash-Lite";


        alert(

            "DocuMind AI Settings\n\n" +

            `API Backend: ${API_URL}\n` +

            "Vector Search: FAISS\n" +

            "Embeddings: all-MiniLM-L6-v2\n" +

            `AI Model: ${answerModel}`

        );

    };

}


// =========================================================
// HELPERS
// =========================================================

async function jsonResponse(
    response
) {

    try {

        return await response.json();

    } catch {

        throw new Error(
            "The backend returned an invalid response."
        );

    }

}


// =========================================================
// LOADING
// =========================================================

function showLoading(
    text
) {

    if (!loadingOverlay) {
        return;
    }

    loadingText.textContent =
        text;

    loadingOverlay.style.display =
        "flex";

}


function hideLoading() {

    if (!loadingOverlay) {
        return;
    }

    loadingOverlay.style.display =
        "none";

}


// =========================================================
// CHAT SCROLL
// =========================================================

function scrollChat() {

    if (!chatArea) {
        return;
    }

    requestAnimationFrame(() => {

        chatArea.scrollTop =
            chatArea.scrollHeight;

    });

}


// =========================================================
// FILE SIZE
// =========================================================

function size(
    bytes
) {

    bytes =
        Number(bytes) || 0;


    if (bytes < 1024) {

        return `${bytes} B`;

    }


    if (
        bytes <
        1024 * 1024
    ) {

        return `${(
            bytes / 1024
        ).toFixed(1)} KB`;

    }


    if (
        bytes <
        1024 * 1024 * 1024
    ) {

        return `${(
            bytes /
            (1024 * 1024)
        ).toFixed(1)} MB`;

    }


    return `${(
        bytes /
        (1024 * 1024 * 1024)
    ).toFixed(1)} GB`;

}


// =========================================================
// HTML ESCAPE
// =========================================================

function esc(
    text
) {

    const element =
        document.createElement(
            "div"
        );

    element.textContent =
        String(
            text ?? ""
        );

    return element.innerHTML;

}


// =========================================================
// FORMAT ANSWER
// =========================================================

function formatAnswer(
    text
) {

    return esc(text)

        .replace(
            /\n\n/g,
            "<br><br>"
        )

        .replace(
            /\n/g,
            "<br>"
        );

}