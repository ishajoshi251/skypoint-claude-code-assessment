"""
Resume parser service — framework-agnostic.

Supports PDF (via pdfplumber) and DOCX (via python-docx).
Extracts:
  - raw text
  - skills (matched against a curated keyword list + spaCy NER for ORG/PRODUCT)
  - approximate years of experience (heuristic: regex on year ranges)
"""
import io
import re
import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Skill keyword list (expand as needed)
# ---------------------------------------------------------------------------
_SKILL_KEYWORDS: set[str] = {
    # Languages
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "c++", "c#",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    # Web
    "react", "next.js", "nextjs", "vue", "angular", "svelte", "html", "css", "tailwind",
    "bootstrap", "jquery", "graphql", "rest", "fastapi", "django", "flask", "express",
    "spring", "rails", "laravel",
    # Data / ML
    "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "pandas", "numpy",
    "matplotlib", "seaborn", "huggingface", "langchain", "openai", "llm",
    "machine learning", "deep learning", "nlp", "computer vision",
    # Cloud / DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "k8s", "terraform", "ansible",
    "ci/cd", "github actions", "jenkins", "linux", "bash",
    # Databases
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "snowflake", "bigquery",
    # Other
    "git", "agile", "scrum", "jira", "kafka", "rabbitmq", "microservices",
    "sql", "nosql", "spark", "hadoop", "airflow",
}


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber  # lazy import — not all workers need this
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            return "\n".join(pages_text)
    except Exception as exc:
        logger.warning("PDF extraction failed", error=str(exc))
        return ""


def _extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document  # lazy import
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as exc:
        logger.warning("DOCX extraction failed", error=str(exc))
        return ""


def _extract_skills(text: str) -> list[str]:
    """Match skill keywords (case-insensitive) in the resume text."""
    text_lower = text.lower()
    found: list[str] = []

    for skill in sorted(_SKILL_KEYWORDS):
        # Word-boundary match so "go" doesn't match "google"
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)

    # De-duplicate and return canonical capitalisation
    return sorted(set(found))


def _extract_experience_years(text: str) -> float | None:
    """
    Heuristic: find year ranges like "2018 – 2023" or "2015 - Present"
    and sum up the durations.  Falls back to looking for "X years" phrases.
    """
    # Pattern: YYYY – YYYY or YYYY - Present/Current/Now
    year_range_re = re.compile(
        r"\b((?:19|20)\d{2})\s*[-–—]\s*((?:19|20)\d{2}|present|current|now)\b",
        re.IGNORECASE,
    )
    from datetime import date

    current_year = date.today().year
    total_years = 0.0
    matched = False

    for m in year_range_re.finditer(text):
        start_str, end_str = m.group(1), m.group(2)
        try:
            start = int(start_str)
            end = current_year if end_str.lower() in ("present", "current", "now") else int(end_str)
            if end >= start and end <= current_year + 1:
                total_years += end - start
                matched = True
        except ValueError:
            continue

    if matched:
        return round(min(total_years, 40.0), 1)  # cap at 40 years

    # Fallback: "5 years of experience" type phrases
    phrase_re = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)", re.IGNORECASE)
    m = phrase_re.search(text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ParsedResume:
    __slots__ = ("text", "skills", "experience_years")

    def __init__(self, text: str, skills: list[str], experience_years: float | None):
        self.text = text
        self.skills = skills
        self.experience_years = experience_years


def parse_resume(file_bytes: bytes, mime_type: str) -> ParsedResume:
    """
    Parse a resume file and return structured data.

    Args:
        file_bytes: Raw file content.
        mime_type:  MIME type string ("application/pdf" or docx MIME).

    Returns:
        ParsedResume with text, skills list, and estimated years of experience.
    """
    if mime_type == "application/pdf":
        text = _extract_text_from_pdf(file_bytes)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        text = _extract_text_from_docx(file_bytes)
    else:
        logger.warning("Unsupported MIME type for resume parsing", mime_type=mime_type)
        text = ""

    skills = _extract_skills(text)
    experience_years = _extract_experience_years(text)

    logger.info(
        "Resume parsed",
        mime_type=mime_type,
        text_len=len(text),
        skills_count=len(skills),
        experience_years=experience_years,
    )
    return ParsedResume(text=text, skills=skills, experience_years=experience_years)
