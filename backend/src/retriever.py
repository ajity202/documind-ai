import json
import os
import re

import faiss
import numpy as np


class Retriever:

    def __init__(
        self,
        folder="vectorstore/faiss_index"
    ):

        self.folder = folder

        self.index = None
        self.records = []
        self.documents = []

        os.makedirs(
            self.folder,
            exist_ok=True
        )

        self.index_path = os.path.join(
            self.folder,
            "index.faiss"
        )

        self.records_path = os.path.join(
            self.folder,
            "records.json"
        )

        self.embeddings_path = os.path.join(
            self.folder,
            "embeddings.npy"
        )

        self.documents_path = os.path.join(
            self.folder,
            "documents.json"
        )

        self.load()

    # =====================================================
    # LOAD VECTORSTORE
    # =====================================================

    def load(self):

        if (
            os.path.exists(self.index_path)
            and os.path.exists(self.records_path)
            and os.path.exists(self.embeddings_path)
        ):

            try:

                self.index = faiss.read_index(
                    self.index_path
                )

                with open(
                    self.records_path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    self.records = json.load(file)

                if os.path.exists(
                    self.documents_path
                ):

                    with open(
                        self.documents_path,
                        "r",
                        encoding="utf-8"
                    ) as file:

                        self.documents = json.load(
                            file
                        )

                return True

            except Exception as error:

                print(
                    f"Could not load vectorstore: {error}"
                )

                self.index = None
                self.records = []
                self.documents = []

        return False

    # =====================================================
    # BUILD INDEX
    # =====================================================

    def build_index(
        self,
        embeddings,
        chunks
    ):

        embeddings = np.asarray(
            embeddings,
            dtype="float32"
        )

        if len(embeddings) == 0:

            raise ValueError(
                "No embeddings were provided."
            )

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(
            dimension
        )

        self.index.add(
            embeddings
        )

        self.records = []

        for chunk in chunks:

            if isinstance(
                chunk,
                dict
            ):

                self.records.append({
                    "document_id":
                        chunk.get(
                            "document_id"
                        ),

                    "document_name":
                        chunk.get(
                            "document_name",
                            "Document"
                        ),

                    "page":
                        chunk.get(
                            "page"
                        ),

                    "text":
                        chunk.get(
                            "text",
                            ""
                        )
                })

            else:

                self.records.append({
                    "document_id": None,
                    "document_name": "Document",
                    "page": None,
                    "text": str(chunk)
                })

        np.save(
            self.embeddings_path,
            embeddings
        )

        faiss.write_index(
            self.index,
            self.index_path
        )

        with open(
            self.records_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.records,
                file,
                ensure_ascii=False,
                indent=2
            )

    # =====================================================
    # SAVE
    # =====================================================

    def save(
        self,
        embeddings
    ):

        embeddings = np.asarray(
            embeddings,
            dtype="float32"
        )

        if len(embeddings) == 0:

            self.index = None

            return

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(
            dimension
        )

        self.index.add(
            embeddings
        )

        faiss.write_index(
            self.index,
            self.index_path
        )

        np.save(
            self.embeddings_path,
            embeddings
        )

        with open(
            self.records_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.records,
                file,
                ensure_ascii=False,
                indent=2
            )

        with open(
            self.documents_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.documents,
                file,
                ensure_ascii=False,
                indent=2
            )

    # =====================================================
    # ADD DOCUMENT
    # =====================================================

    def add_document(
        self,
        document_id,
        filename,
        file_size,
        chunks,
        embeddings,
        page_count
    ):

        for chunk in chunks:

            self.records.append({
                "document_id":
                    document_id,

                "document_name":
                    filename,

                "page":
                    chunk["page"],

                "text":
                    chunk["text"]
            })

        self.documents.append({
            "id":
                document_id,

            "filename":
                filename,

            "size":
                file_size,

            "pages":
                page_count,

            "chunks":
                len(chunks),

            "path":
                os.path.join(
                    "data",
                    "uploads",
                    f"{document_id}_{filename}"
                )
        })

        existing_embeddings = (
            self._load_embeddings()
        )

        new_embeddings = np.asarray(
            embeddings,
            dtype="float32"
        )

        if existing_embeddings is None:

            combined = new_embeddings

        else:

            combined = np.vstack([
                existing_embeddings,
                new_embeddings
            ])

        self.save(
            combined
        )

    # =====================================================
    # NORMALIZE TEXT
    # =====================================================

    def _normalize_text(
        self,
        text
    ):

        text = str(
            text or ""
        ).lower()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # =====================================================
    # REMOVE DUPLICATE RESULTS
    # =====================================================

    def _remove_duplicate_results(
        self,
        results
    ):

        unique_results = []

        seen_text = set()

        for result in results:

            text = self._normalize_text(
                result.get(
                    "text",
                    ""
                )
            )

            if not text:
                continue

            # Exact duplicate
            if text in seen_text:
                continue

            seen_text.add(
                text
            )

            unique_results.append(
                result
            )

        return unique_results

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query_embedding,
        top_k=5
    ):

        if (
            self.index is None
            or not self.records
        ):

            return []

        query = np.asarray(
            [query_embedding],
            dtype="float32"
        )

        # -------------------------------------------------
        # Retrieve more candidates than needed.
        # This gives us room to remove duplicates.
        # -------------------------------------------------

        candidate_k = min(
            max(
                top_k * 3,
                10
            ),
            len(self.records)
        )

        distances, indices = (
            self.index.search(
                query,
                candidate_k
            )
        )

        candidates = []

        for distance, index in zip(
            distances[0],
            indices[0]
        ):

            if not (
                0 <= index
                < len(self.records)
            ):

                continue

            item = dict(
                self.records[index]
            )

            item["distance"] = float(
                distance
            )

            candidates.append(
                item
            )

        # -------------------------------------------------
        # Remove duplicate chunks
        # -------------------------------------------------

        candidates = (
            self._remove_duplicate_results(
                candidates
            )
        )

        # -------------------------------------------------
        # Return only requested number
        # -------------------------------------------------

        return candidates[:top_k]

    # =====================================================
    # GET DOCUMENT
    # =====================================================

    def get_document(
        self,
        document_id
    ):

        for document in self.documents:

            if document["id"] == document_id:

                return document

        return None

    # =====================================================
    # LIST DOCUMENTS
    # =====================================================

    def list_documents(
        self
    ):

        return self.documents

    # =====================================================
    # DELETE DOCUMENT
    # =====================================================

    def delete_document(
        self,
        document_id
    ):

        keep_indices = [
            i
            for i, record
            in enumerate(
                self.records
            )
            if record["document_id"]
            != document_id
        ]

        embeddings = (
            self._load_embeddings()
        )

        if embeddings is None:

            remaining_embeddings = None

        else:

            remaining_embeddings = (
                embeddings[
                    keep_indices
                ]
            )

        self.records = [
            record
            for record in self.records
            if record["document_id"]
            != document_id
        ]

        self.documents = [
            document
            for document in self.documents
            if document["id"]
            != document_id
        ]

        if not self.records:

            self.index = None

            for path in [
                self.index_path,
                self.records_path,
                self.embeddings_path,
                self.documents_path
            ]:

                if os.path.exists(path):

                    os.remove(
                        path
                    )

            return

        self.save(
            remaining_embeddings
        )

    # =====================================================
    # LOAD EMBEDDINGS
    # =====================================================

    def _load_embeddings(
        self
    ):

        if not os.path.exists(
            self.embeddings_path
        ):

            return None

        return np.load(
            self.embeddings_path
        )