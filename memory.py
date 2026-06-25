import hashlib
from datetime import datetime
from pathlib import Path

try:
    import chromadb
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - exercised when optional deps are unavailable
    chromadb = None
    SentenceTransformer = None

BASE_DIR = Path(__file__).resolve().parent
PERSIST_DIR = BASE_DIR / "jerry_memory" / "chroma_db"
PERSIST_DIR.mkdir(parents=True, exist_ok=True)

_FALLBACK_STORE = []

if chromadb is not None:
    _client = chromadb.PersistentClient(path=str(PERSIST_DIR))
    _collection = _client.get_or_create_collection(name="jerry_memories")
else:
    _client = None
    _collection = None

if SentenceTransformer is not None:
    _model = SentenceTransformer("all-MiniLM-L6-v2")
else:
    _model = None


def _embed_text(text: str):
    if _model is not None:
        return _model.encode(text, convert_to_numpy=True).tolist()

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [float(byte) / 255.0 for byte in digest[:8]]


def store_memory(content: str, tag: str, name: str = None) -> str:
    """Store a memory entry in ChromaDB and return a confirmation string."""
    memory_id = f"{tag}_{datetime.now().timestamp()}"
    metadata = {"tag": tag}
    if name is not None:
        metadata["name"] = name

    if _collection is not None:
        _collection.add(
            ids=[memory_id],
            documents=[content],
            embeddings=[_embed_text(content)],
            metadatas=[metadata],
        )
    else:
        _FALLBACK_STORE.append({"id": memory_id, "content": content, "tag": tag, "name": name})

    return f"Stored memory for {tag}."


def retrieve_memory(tag: str, query: str, name: str = None, top_k: int = 3) -> str:
    """Retrieve memory entries matching the given tag and optional name."""
    if _collection is not None:
        where_filter = {"tag": tag}
        if name is not None:
            where_filter = {"$and": [{"tag": tag}, {"name": name}]}

        results = _collection.query(
            query_embeddings=[_embed_text(query)],
            n_results=top_k,
            where=where_filter,
        )

        documents = results.get("documents", [[]])[0]
        if not documents:
            return "No memory found"

        return "\n".join(documents)

    matches = [
        item["content"]
        for item in _FALLBACK_STORE
        if item.get("tag") == tag and (name is None or item.get("name") == name)
    ]
    if not matches:
        return "No memory found"
    return "\n".join(matches[:top_k])
