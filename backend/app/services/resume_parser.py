"""
Resume parser service — framework-agnostic.

Supports PDF (via pdfplumber) and DOCX (via python-docx).
Extracts:
  - raw text
  - profile basics (name/headline/location, using conservative heuristics)
  - skills (matched against a curated keyword list)
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
    "python",
    "java",
    "javascript",
    "typescript",
    "go",
    "golang",
    "rust",
    "c++",
    "c#",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",
    "r",
    "matlab",
    # Web
    "react",
    "next.js",
    "nextjs",
    "vue",
    "angular",
    "svelte",
    "html",
    "css",
    "tailwind",
    "bootstrap",
    "jquery",
    "graphql",
    "rest",
    "fastapi",
    "django",
    "flask",
    "express",
    "spring",
    "rails",
    "laravel",
    # Data / ML
    "pytorch",
    "tensorflow",
    "keras",
    "scikit-learn",
    "sklearn",
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "huggingface",
    "langchain",
    "openai",
    "llm",
    "machine learning",
    "deep learning",
    "nlp",
    "computer vision",
    # Cloud / DevOps
    "aws",
    "gcp",
    "azure",
    "docker",
    "kubernetes",
    "k8s",
    "terraform",
    "ansible",
    "ci/cd",
    "github actions",
    "jenkins",
    "linux",
    "bash",
    # Databases
    "postgresql",
    "postgres",
    "mysql",
    "sqlite",
    "mongodb",
    "redis",
    "elasticsearch",
    "cassandra",
    "dynamodb",
    "snowflake",
    "bigquery",
    "api gateway",
    "lambda",
    # Other
    "git",
    "agile",
    "scrum",
    "jira",
    "kafka",
    "rabbitmq",
    "microservices",
    "rest api development",
    "sql",
    "nosql",
    "spark",
    "hadoop",
    "airflow",
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
    phrase_re = re.compile(
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)", re.IGNORECASE
    )
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

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _extract_text_from_txt(file_bytes: bytes) -> str:
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")


_SECTION_HEADINGS = {
    "summary",
    "profile",
    "objective",
    "experience",
    "work experience",
    "employment",
    "education",
    "skills",
    "technical skills",
    "projects",
    "certifications",
    "contact",
}

_ROLE_WORDS = (
    "engineer",
    "developer",
    "architect",
    "analyst",
    "scientist",
    "manager",
    "designer",
    "consultant",
    "specialist",
    "lead",
    "intern",
    "administrator",
)


def _clean_lines(text: str) -> list[str]:
    return [line.strip(" \t•*-|") for line in text.splitlines() if line.strip(" \t•*-|")]


def _line_value(text: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"^\s*(?:{label_pattern})\s*[:\-]\s*(.+)$", text, re.IGNORECASE | re.MULTILINE
    )
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _looks_like_contact(line: str) -> bool:
    return bool(
        re.search(r"@|https?://|linkedin\.com|github\.com|\+?\d[\d\s().-]{7,}", line, re.IGNORECASE)
    )


def _extract_resume_name(text: str) -> str | None:
    for line in _clean_lines(text)[:12]:
        lower = line.lower().rstrip(":")
        words = line.split()
        if lower in _SECTION_HEADINGS or _looks_like_contact(line):
            continue
        if not (2 <= len(words) <= 5):
            continue
        if any(ch.isdigit() for ch in line):
            continue
        if len(line) > 80 or re.search(r"[,;:]", line):
            continue
        if any(word.lower() in _ROLE_WORDS for word in words):
            continue
        return " ".join(word.capitalize() if word.isupper() else word for word in words)
    return None


def _extract_resume_headline(text: str, name: str | None) -> str | None:
    skipped_name = False
    for line in _clean_lines(text)[:18]:
        lower = line.lower().rstrip(":")
        if name and not skipped_name and line.lower() == name.lower():
            skipped_name = True
            continue
        if lower in _SECTION_HEADINGS or _looks_like_contact(line):
            continue
        if len(line) > 140:
            continue
        if any(word in lower for word in _ROLE_WORDS):
            return line
    return None


def _extract_resume_location(text: str) -> str | None:
    labeled = re.search(
        r"\b(?:location|based in|address)\s*[:\-]\s*([A-Za-z][A-Za-z\s.,-]{2,80})",
        text,
        re.IGNORECASE,
    )
    if labeled:
        return labeled.group(1).splitlines()[0].strip(" ,.-")
    if re.search(r"\bremote\b", text, re.IGNORECASE):
        return "Remote"
    city_state = re.search(r"\b([A-Z][a-zA-Z\s]{2,35},\s*[A-Z]{2})\b", text)
    if city_state:
        return city_state.group(1).strip()
    return None


def _extract_jd_title(text: str) -> str | None:
    labeled = _line_value(text, ("job title", "role name", "role", "position", "title"))
    if labeled and len(labeled) < 120:
        return labeled

    for pattern in [
        r"(?:job\s+title|position|role)\s*[:\-]\s*(.+)",
        r"^#+\s*(.{5,80})$",
    ]:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            title = m.group(1).strip().rstrip("*_#").strip()
            if 3 < len(title) < 120:
                return title
    for line in _clean_lines(text)[:12]:
        lower = line.lower().rstrip(":")
        if lower in _SECTION_HEADINGS or _looks_like_contact(line):
            continue
        if len(line) <= 120 and any(word in lower for word in _ROLE_WORDS):
            return line
    return None


def _extract_company_name(text: str) -> str | None:
    company = _line_value(text, ("company name", "company", "organization", "organisation"))
    if company and len(company) < 160:
        return company
    return None


def _extract_jd_location(text: str) -> str | None:
    labeled = _line_value(text, ("location", "job location", "work location"))
    if labeled:
        return labeled
    if re.search(r"\bremote\b", text, re.IGNORECASE):
        return "Remote"
    m = re.search(r"\b([A-Z][a-zA-Z\s]{2,25},\s*[A-Z]{2})\b", text)
    if m:
        return m.group(1).strip()
    return None


def _parse_salary_number(value: str) -> float | None:
    lowered = value.lower().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", lowered)
    if not match:
        return None

    amount = float(match.group(1))
    tail = lowered[match.end() : match.end() + 20]
    if re.search(r"\b(?:lpa|lakh|lakhs)\b", tail):
        amount *= 100000
    elif re.search(r"\b(?:k|thousand)\b", tail):
        amount *= 1000
    elif re.search(r"\b(?:m|million)\b", tail):
        amount *= 1000000
    return amount


def _extract_salary_range(text: str) -> tuple[float | None, float | None]:
    salary_line = _line_value(text, ("salary range", "salary", "compensation", "pay range"))
    if not salary_line:
        return None, None

    parts = re.split(r"\s*(?:-|–|—|to)\s*", salary_line, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) == 1:
        amount = _parse_salary_number(parts[0])
        return amount, None
    return _parse_salary_number(parts[0]), _parse_salary_number(parts[1])


def _extract_exp_range(text: str) -> tuple[float | None, float | None]:
    experience_line = _line_value(
        text,
        ("experience", "experience required", "required experience", "years of experience"),
    )
    if experience_line:
        line_min, line_max = _extract_exp_range(experience_line)
        if line_min is not None or line_max is not None:
            return line_min, line_max

    m = re.search(r"(\d+)\s*(?:[-–]|to)\s*(\d+)\s*\+?\s*years?", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(?:minimum|at\s+least|min\.?)\s+(\d+)\s*\+?\s*years?", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), None
    m = re.search(r"(\d+)\s*\+\s*years?", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), None
    m = re.search(r"(\d+)\s+years?\s+of\s+experience", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), None
    return None, None


def _extract_employment_type(text: str) -> str:
    t = text.lower()
    if "full-time" in t or "full time" in t:
        return "FULL_TIME"
    if "part-time" in t or "part time" in t:
        return "PART_TIME"
    if "contract" in t or "freelance" in t:
        return "CONTRACT"
    if "intern" in t:
        return "INTERNSHIP"
    return "FULL_TIME"


def _extract_jd_skills(text: str) -> list[str]:
    skills = {skill.lower(): skill for skill in _extract_skills(text)}
    block = re.search(
        r"^\s*(?:skills required|required skills|technical skills|skills)\s*[:\-]?\s*(.*?)(?=^\s*[A-Z][A-Za-z /&]+\s*[:\-]|\Z)",
        text,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if block:
        candidates = re.split(r"[,;\n]", block.group(1))
        for candidate in candidates:
            skill = candidate.strip(" \t•*-()")
            if 1 < len(skill) <= 60 and not re.search(
                r"\b(?:required|responsibilities|salary)\b", skill, re.IGNORECASE
            ):
                key = skill.lower()
                if key not in skills or skills[key].islower():
                    skills[key] = skill
    return sorted(skills.values(), key=str.lower)


def _build_jd_description(text: str) -> str:
    metadata_labels = (
        "company name",
        "company",
        "role name",
        "job title",
        "title",
        "salary range",
        "salary",
        "compensation",
        "location",
        "job location",
        "work location",
        "experience",
        "experience required",
        "required experience",
        "employment type",
        "job type",
        "skills required",
        "required skills",
        "technical skills",
    )
    label_pattern = "|".join(re.escape(label) for label in metadata_labels)
    cleaned = []
    skip_skill_items = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if skip_skill_items:
                continue
            cleaned.append(line)
            continue
        if re.match(rf"^(?:{label_pattern})\s*[:\-]", stripped, re.IGNORECASE):
            skip_skill_items = bool(
                re.match(
                    r"^(?:skills required|required skills|technical skills)",
                    stripped,
                    re.IGNORECASE,
                )
            )
            continue
        if skip_skill_items and re.match(r"^[•*\-]\s*", stripped):
            continue
        skip_skill_items = False
        cleaned.append(line)

    return "\n".join(cleaned).strip()


class ParsedJD:
    __slots__ = (
        "title",
        "company_name",
        "description",
        "skills",
        "location",
        "min_experience",
        "max_experience",
        "min_salary",
        "max_salary",
        "employment_type",
    )

    def __init__(
        self,
        title: str | None,
        company_name: str | None,
        description: str,
        skills: list[str],
        location: str | None,
        min_experience: float | None,
        max_experience: float | None,
        min_salary: float | None,
        max_salary: float | None,
        employment_type: str,
    ):
        self.title = title
        self.company_name = company_name
        self.description = description
        self.skills = skills
        self.location = location
        self.min_experience = min_experience
        self.max_experience = max_experience
        self.min_salary = min_salary
        self.max_salary = max_salary
        self.employment_type = employment_type


def parse_job_description(file_bytes: bytes, mime_type: str) -> ParsedJD:
    """
    Parse a job description file (PDF/DOCX/TXT) and return structured data
    suitable for auto-filling the job creation form.
    """
    if mime_type == "application/pdf":
        text = _extract_text_from_pdf(file_bytes)
    elif mime_type == _DOCX_MIME:
        text = _extract_text_from_docx(file_bytes)
    else:
        text = _extract_text_from_txt(file_bytes)

    title = _extract_jd_title(text)
    company_name = _extract_company_name(text)
    skills = _extract_jd_skills(text)
    location = _extract_jd_location(text)
    min_exp, max_exp = _extract_exp_range(text)
    min_salary, max_salary = _extract_salary_range(text)
    emp_type = _extract_employment_type(text)
    description = _build_jd_description(text)
    if not description:
        role = title or "Open role"
        company = f" at {company_name}" if company_name else ""
        skill_text = f" Required skills: {', '.join(skills)}." if skills else ""
        description = f"{role}{company}.{skill_text}"

    logger.info(
        "JD parsed",
        mime_type=mime_type,
        text_len=len(text),
        skills_count=len(skills),
    )
    return ParsedJD(
        title=title,
        company_name=company_name,
        description=description,
        skills=skills,
        location=location,
        min_experience=min_exp,
        max_experience=max_exp,
        min_salary=min_salary,
        max_salary=max_salary,
        employment_type=emp_type,
    )


class ParsedResume:
    __slots__ = ("text", "skills", "experience_years", "full_name", "headline", "location")

    def __init__(
        self,
        text: str,
        skills: list[str],
        experience_years: float | None,
        full_name: str | None,
        headline: str | None,
        location: str | None,
    ):
        self.text = text
        self.skills = skills
        self.experience_years = experience_years
        self.full_name = full_name
        self.headline = headline
        self.location = location


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
    elif mime_type == _DOCX_MIME:
        text = _extract_text_from_docx(file_bytes)
    else:
        logger.warning("Unsupported MIME type for resume parsing", mime_type=mime_type)
        text = ""

    skills = _extract_skills(text)
    experience_years = _extract_experience_years(text)
    full_name = _extract_resume_name(text)
    headline = _extract_resume_headline(text, full_name)
    location = _extract_resume_location(text)

    logger.info(
        "Resume parsed",
        mime_type=mime_type,
        text_len=len(text),
        skills_count=len(skills),
        experience_years=experience_years,
        has_name=bool(full_name),
        has_headline=bool(headline),
        has_location=bool(location),
    )
    return ParsedResume(
        text=text,
        skills=skills,
        experience_years=experience_years,
        full_name=full_name,
        headline=headline,
        location=location,
    )
