"""Embeddings OpenAI + chunking respectueux des sections."""
import logging

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
MAX_INPUT_TOKENS = 8191
CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class _FallbackEncoder:
    """Encodeur de secours hors-ligne.

    tiktoken télécharge son fichier d'encodage (cl100k_base) au premier appel.
    Si le réseau est indisponible (cold start, politique réseau restrictive en
    prod), on bascule sur cet encodeur caractère-par-caractère. Le round-trip
    encode→decode reste lossless, donc le chunking et la troncature continuent
    de fonctionner ; la granularité est simplement plus fine (≈1 caractère par
    « token »), ce qui reste sûr vis-à-vis de la limite de l'API d'embeddings.
    """

    def encode(self, text: str) -> list[int]:
        return [ord(c) for c in text]

    def decode(self, tokens: list[int]) -> str:
        return "".join(chr(t) for t in tokens)


_encoder = None


def _get_encoder():
    """Charge tiktoken paresseusement avec fallback hors-ligne résilient."""
    global _encoder
    if _encoder is not None:
        return _encoder
    try:
        import tiktoken

        _encoder = tiktoken.get_encoding("cl100k_base")
    except Exception as exc:  # réseau bloqué, tiktoken absent, etc.
        logger.warning(
            "tiktoken indisponible (%s) — bascule sur l'encodeur de secours.", exc
        )
        _encoder = _FallbackEncoder()
    return _encoder


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_TOKENS,
               overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    """Découpe en chunks ~500 tokens avec overlap, en respectant les paragraphes."""
    if not text or not text.strip():
        return []
    encoder = _get_encoder()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], []

    for para in paragraphs:
        para_tokens = encoder.encode(para)
        if len(para_tokens) > chunk_size:
            if current:
                chunks.append(encoder.decode(current))
                current = current[-overlap:] if overlap else []
            for i in range(0, len(para_tokens), chunk_size - overlap):
                chunks.append(encoder.decode(para_tokens[i:i + chunk_size]))
            current = []
            continue
        if len(current) + len(para_tokens) > chunk_size:
            if current:
                chunks.append(encoder.decode(current))
                current = current[-overlap:] if overlap else []
        if current:
            current.extend(encoder.encode("\n\n"))
        current.extend(para_tokens)

    if current:
        chunks.append(encoder.decode(current))
    return [c for c in chunks if c.strip()]


def _truncate(text: str, max_tokens: int) -> str:
    encoder = _get_encoder()
    t = encoder.encode(text)
    return encoder.decode(t[:max_tokens]) if len(t) > max_tokens else text


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
