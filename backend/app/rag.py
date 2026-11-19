from functools import lru_cache
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .config import CHROMA_DIR, EMBEDDING_MODEL

@lru_cache(maxsize=1)
def embedder():
    return SentenceTransformer(EMBEDDING_MODEL)

@lru_cache(maxsize=1)
def client():
    return chromadb.PersistentClient(path=str(CHROMA_DIR))

def collection(name):
    return client().get_or_create_collection(name=name, metadata={"hnsw:space":"cosine"})

def chunks(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=850, chunk_overlap=120)
    return [x for x in splitter.split_text(text) if x.strip()]

def add(collection_name, texts, metas, ids):
    if not texts:
        return
    vectors = embedder().encode(texts, normalize_embeddings=True).tolist()
    collection(collection_name).upsert(ids=ids, documents=texts, embeddings=vectors, metadatas=metas)

def index_project(pid, filename, text):
    parts = chunks(text)
    if not parts:
        raise ValueError("No readable text found.")
    add("project_chunks", parts,
        [{"project_id":pid,"filename":filename,"chunk":i} for i in range(len(parts))],
        [f"{pid}_{i}" for i in range(len(parts))])
    return len(parts)

def retrieve(query, pid, n=4):
    vector = embedder().encode([query], normalize_embeddings=True)[0].tolist()
    found = []
    for name, where in [("project_chunks", {"project_id":pid}), ("reference_chunks", None)]:
        try:
            col = collection(name)
            available = col.count()
            if available == 0:
                continue
            args = {"query_embeddings":[vector], "n_results":min(n, available)}
            if where:
                args["where"] = where
            result = col.query(**args)
            for doc, meta, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
                found.append({"source_type":name,"text":doc,"source":meta.get("filename","reference"),"chunk":meta.get("chunk"),"distance":dist})
        except Exception:
            pass
    return sorted(found, key=lambda x:x["distance"])[:n*2]

def ingest_reference_folder(folder):
    from .document_loader import extract_text
    total = 0
    for p in Path(folder).rglob("*"):
        if p.is_file() and p.suffix.lower() in {".pdf",".docx",".txt"}:
            try:
                parts = chunks(extract_text(str(p)))
                add("reference_chunks", parts,
                    [{"filename":p.name,"chunk":i} for i in range(len(parts))],
                    [f"ref_{p.stem}_{i}" for i in range(len(parts))])
                total += len(parts)
            except Exception as exc:
                print("Skipped", p.name, exc)
    return total
