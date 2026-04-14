"""
Embedding service — generates 384-dim sentence embeddings.

Uses sentence-transformers all-MiniLM-L6-v2 (singleton, lazy loaded).
Model is pre-cached during Docker build so there's no runtime download.
"""
import asyncio
import structlog

logger = structlog.get_logger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model", model=_MODEL_NAME)
        _model = SentenceTransformer(_MODEL_NAME)
        logger.info("Model loaded")
    return _model


def embed_text_sync(text: str) -> list[float]:
    """Synchronous embedding — run via executor to avoid blocking the event loop."""
    model = _load_model()
    vec = model.encode(text.strip(), normalize_embeddings=True)
    return vec.tolist()


async def embed_text(text: str) -> list[float]:
    """Async wrapper — offloads CPU work to a thread pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embed_text_sync, text)


# ---------------------------------------------------------------------------
# Text builders — what goes into each embedding
# ---------------------------------------------------------------------------


def build_job_text(title: str, description: str, required_skills: list[str]) -> str:
    skills_str = ", ".join(required_skills) if required_skills else ""
    parts = [title, description]
    if skills_str:
        parts.append(f"Required skills: {skills_str}")
    return ". ".join(parts)


def build_candidate_text(
    headline: str | None,
    bio: str | None,
    skills: list[str] | None,
    years_experience: float | None,
) -> str:
    parts: list[str] = []
    if headline:
        parts.append(headline)
    if bio:
        parts.append(bio)
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")
    if years_experience is not None:
        parts.append(f"{years_experience} years of experience")
    return ". ".join(parts) if parts else "candidate profile"
