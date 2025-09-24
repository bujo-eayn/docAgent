# app/faiss_indexer.py
import faiss
import numpy as np
from sqlalchemy import create_engine, select, MetaData, Table

# Ensure this DB path matches the backend's DB path
engine = create_engine("sqlite:///./data/memory.db",
                       connect_args={"check_same_thread": False})
metadata = MetaData()
metadata.reflect(bind=engine)
images_tbl = Table("images", metadata, autoload_with=engine)


def build_index():
    """
    Build a FAISS index from embeddings stored in the images table.
    Returns: (index, ids_with_captions) or (None, None) if there are no embeddings.
    ids_with_captions: list of tuples (image_id, caption)
    """
    with engine.connect() as conn:
        rows = conn.execute(select(
            images_tbl.c.id, images_tbl.c.embedding, images_tbl.c.caption)).fetchall()

    ids, vectors, captions = [], [], []
    for r in rows:
        if r.embedding is None:
            continue
        try:
            vec = np.frombuffer(r.embedding, dtype=np.float32)
        except Exception:
            continue
        ids.append(r.id)
        captions.append(r.caption or "")
        vectors.append(vec)

    if not vectors:
        return None, None

    x = np.vstack(vectors).astype(np.float32)
    dim = x.shape[1]
    # Normalize for cosine / inner product similarity
    faiss.normalize_L2(x)
    index = faiss.IndexFlatIP(dim)
    index.add(x)
    ids_with_captions = list(zip(ids, captions))
    return index, ids_with_captions


def search_index(index, ids_with_caps, query_vec, top_k=3):
    """
    Search the provided FAISS index with query_vec (1D numpy array).
    Returns list of dicts: {"id": image_id, "caption": caption}
    """
    if index is None or ids_with_caps is None:
        return []

    q = query_vec.reshape(1, -1).astype(np.float32)
    faiss.normalize_L2(q)
    D, I = index.search(q, top_k)
    results = []
    for idx in I[0]:
        if idx < 0 or idx >= len(ids_with_caps):
            continue
        image_id, caption = ids_with_caps[idx]
        results.append({"id": image_id, "caption": caption})
    return results
