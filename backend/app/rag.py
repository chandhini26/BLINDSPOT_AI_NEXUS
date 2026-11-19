
import json
import math
import re
import threading
from pathlib import Path
from collections import Counter

from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import CHROMA_DIR

# Lightweight keyword-based document retrieval.
# No ChromaDB, PyTorch or SentenceTransformer required.

INDEX_FILE = Path(CHROMA_DIR) / "keyword_index.json"
INDEX_LOCK = threading.Lock()


def chunks(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=850,
        chunk_overlap=120
    )
    return [x for x in splitter.split_text(text) if x.strip()]


def load_index():
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not INDEX_FILE.exists():
        return {}

    try:
        with INDEX_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_index(data):
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = INDEX_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    temp_file.replace(INDEX_FILE)


def add(collection_name, texts, metas, ids):
    if not texts:
        return

    with INDEX_LOCK:
        data = load_index()
        collection = data.setdefault(collection_name, {})

        for text, meta, item_id in zip(texts, metas, ids):
            collection[item_id] = {
                "text": text,
                "metadata": meta
            }

        save_index(data)


def index_project(pid, filename, text):
    parts = chunks(text)

    if not parts:
        raise ValueError("No readable text found.")

    add(
        "project_chunks",
        parts,
        [
            {
                "project_id": pid,
                "filename": filename,
                "chunk": i
            }
            for i in range(len(parts))
        ],
        [f"{pid}_{i}" for i in range(len(parts))]
    )

    return len(parts)


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve(query, pid, n=4):
    query_words = tokenize(query)

    if not query_words:
        return []

    with INDEX_LOCK:
        data = load_index()

    documents = []

    for collection_name in ("project_chunks", "reference_chunks"):
        collection = data.get(collection_name, {})

        for item in collection.values():
            meta = item.get("metadata", {})

            if collection_name == "project_chunks":
                if str(meta.get("project_id")) != str(pid):
                    continue

            text = item.get("text", "")
            words = tokenize(text)

            if not words:
                continue

            documents.append({
                "source_type": collection_name,
                "text": text,
                "source": meta.get("filename", "reference"),
                "chunk": meta.get("chunk"),
                "words": words
            })

    if not documents:
        return []

    # Lightweight BM25 keyword ranking
    total_docs = len(documents)
    avg_length = sum(len(d["words"]) for d in documents) / total_docs

    document_frequency = Counter()

    for doc in documents:
        document_frequency.update(set(doc["words"]))

    query_counts = Counter(query_words)
    results = []

    k1 = 1.5
    b = 0.75

    for doc in documents:
        word_counts = Counter(doc["words"])
        doc_length = len(doc["words"])
        score = 0.0

        for word, query_count in query_counts.items():
            frequency = word_counts.get(word, 0)

            if frequency == 0:
                continue

            df = document_frequency[word]

            idf = math.log(
                1 + (total_docs - df + 0.5) / (df + 0.5)
            )

            denominator = frequency + k1 * (
                1 - b + b * doc_length / max(avg_length, 1)
            )

            score += (
                idf
                * frequency
                * (k1 + 1)
                / denominator
                * query_count
            )

        if score > 0:
            results.append({
                "source_type": doc["source_type"],
                "text": doc["text"],
                "source": doc["source"],
                "chunk": doc["chunk"],
                "distance": 1 / (1 + score)
            })

    results.sort(key=lambda x: x["distance"])

    return results[:n * 2]


def ingest_reference_folder(folder):
    from .document_loader import extract_text

    total = 0

    for p in Path(folder).rglob("*"):
        if p.is_file() and p.suffix.lower() in {
            ".pdf", ".docx", ".txt"
        }:
            try:
                parts = chunks(extract_text(str(p)))

                add(
                    "reference_chunks",
                    parts,
                    [
                        {
                            "filename": p.name,
                            "chunk": i
                        }
                        for i in range(len(parts))
                    ],
                    [
                        f"ref_{p.stem}_{i}"
                        for i in range(len(parts))
                    ]
                )

                total += len(parts)

            except Exception as exc:
                print("Skipped", p.name, exc)

    return total
