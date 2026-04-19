"""Embeddings OpenAI + chunking respectueux des sections."""
import logging

import tiktoken
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
MAX_INPUT_TOKENS = 8191
CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
_encoder = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_TOKENS,
               overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    """Découpe en chunks ~500 tokens avec overlap, en respectant les paragraphes."""
    if not text or not text.strip():
        return []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], []

    for para in paragraphs:
        para_tokens = _encoder.encode(para)
        if len(para_tokens) > chunk_size:
            if current:
                chunks.append(_encoder.decode(current))
                current = current[-overlap:] if overlap else []
            for i in range(0, len(para_tokens), chunk_size - overlap):
                chunks.append(_encoder.decode(para_tokens[i:i + chunk_size]))
            current = []
            continue
        if len(current) + len(para_tokens) > chunk_size:
            if current:
                chunks.append(_encoder.decode(current))
                current = current[-overlap:] if overlap else []
        if current:
            current.extend(_encoder.encode("\n\n"))
        current.extend(para_tokens)

    if current:
        chunks.append(_encoder.decode(current))
    return [c for c in chunks if c.strip()]


def _truncate(text: str, max_tokens: int) -> str:
    t = _encoder.encode(text)
    return _encoder.decode(t[:max_tokens]) if len(t) > max_tokens else text


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    all_emb = []
    for i in range(0, len(texts), 100):
        batch = [_truncate(t, MAX_INPUT_TOKENS) for t in texts[i:i + 100]]
        try:
            resp = await _client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
            all_emb.extend([item.embedding for item in resp.data])
        except Exception as e:
            logger.error(f"embeddings batch {i}: {e}")
            all_emb.extend([[0.0] * EMBEDDING_DIM] * len(batch))
    return all_emb


async def embed_query(query: str) -> list[float]:
    res = await generate_embeddings([query])
    return res[0] if res else [0.0] * EMBEDDING_DIM
