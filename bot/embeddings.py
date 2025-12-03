import hashlib
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
from docx import Document
from openai import AsyncOpenAI

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingIndex:
    chunks: List[str]
    embeddings: np.ndarray
    meta: Dict[str, str]
    normalized_embeddings: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.normalized_embeddings is None:
            norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            self.normalized_embeddings = self.embeddings / np.clip(norms, 1e-10, None)

    def top_k(self, query_embedding: np.ndarray, k: int) -> List[tuple[str, float]]:
        """Return top-k chunks by cosine similarity."""
        query_norm = np.linalg.norm(query_embedding)
        if query_norm == 0 or self.normalized_embeddings is None:
            return []
        normalized_query = query_embedding / query_norm
        sims = self.normalized_embeddings @ normalized_query
        top_indices = np.argsort(-sims)[:k]
        return [(self.chunks[i], float(sims[i])) for i in top_indices]


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_docx(path: Path) -> List[str]:
    document = Document(path)
    paragraphs = [para.text.strip() for para in document.paragraphs if para.text.strip()]
    return paragraphs


def _chunk_paragraphs(paragraphs: List[str], max_chars: int = 1200, overlap: int = 150) -> List[str]:
    """Merge paragraphs into chunks with small overlap for better embedding recall."""
    chunks: List[str] = []
    buffer: List[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) + 1 > max_chars and buffer:
            chunk = "\n".join(buffer)
            chunks.append(chunk)
            # Keep a small overlap to maintain context.
            overlap_text = chunk[-overlap:]
            buffer = [overlap_text, para]
            current_len = len(overlap_text) + len(para)
        else:
            buffer.append(para)
            current_len += len(para) + 1

    if buffer:
        chunks.append("\n".join(buffer))
    return chunks


def _load_cache(cache_path: Path, expected_hash: str, model: str) -> EmbeddingIndex | None:
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("rb") as f:
            data = pickle.load(f)
        meta = data.get("meta", {})
        if meta.get("doc_hash") != expected_hash or meta.get("model") != model:
            return None
        embeddings = np.array(data["embeddings"], dtype=np.float32)
        return EmbeddingIndex(chunks=data["chunks"], embeddings=embeddings, meta=meta)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load embedding cache: %s", exc)
        return None


def _save_cache(cache_path: Path, index: EmbeddingIndex) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"chunks": index.chunks, "embeddings": index.embeddings, "meta": index.meta}
    with cache_path.open("wb") as f:
        pickle.dump(payload, f)


async def build_or_load_embeddings(config: Config, client: AsyncOpenAI) -> EmbeddingIndex:
    """Load cached embeddings or build them from the DOCX file."""
    if not config.doc_path.exists():
        raise FileNotFoundError(f"Document not found at {config.doc_path}")

    paragraphs = _read_docx(config.doc_path)
    if not paragraphs:
        raise ValueError("The provided DOCX file is empty.")

    chunks = _chunk_paragraphs(paragraphs, max_chars=config.max_context_chars)
    raw_text = "\n".join(paragraphs)
    doc_hash = _hash_text(raw_text)

    cached = _load_cache(config.embeddings_cache, expected_hash=doc_hash, model=config.embedding_model)
    if cached:
        logger.info("Loaded cached embeddings from %s", config.embeddings_cache)
        return cached

    logger.info("No valid cache found. Building embeddings from %s ...", config.doc_path)
    embeddings: List[List[float]] = []
    for idx, chunk in enumerate(chunks, start=1):
        response = await client.embeddings.create(model=config.embedding_model, input=chunk)
        embeddings.append(response.data[0].embedding)
        logger.debug("Embedded chunk %d/%d", idx, len(chunks))

    index = EmbeddingIndex(
        chunks=chunks,
        embeddings=np.array(embeddings, dtype=np.float32),
        meta={"doc_hash": doc_hash, "model": config.embedding_model, "source": str(config.doc_path)},
    )
    _save_cache(config.embeddings_cache, index)
    logger.info("Saved embeddings cache to %s", config.embeddings_cache)
    return index
