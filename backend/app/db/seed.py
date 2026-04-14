"""
Idempotent seed script — meaningful sample data for TalentBridge demo.
Safe to re-run on every container start.
"""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.candidate_profile import CandidateProfile
from app.models.company import Company
from app.models.job import EmploymentType, Job, JobStatus
from app.models.user import Role, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

SEED_USERS = [
    {"email": settings.SEED_HR_EMAIL,        "password": settings.SEED_HR_PASSWORD,        "role": Role.HR},
    {"email": settings.SEED_CANDIDATE_EMAIL, "password": settings.SEED_CANDIDATE_PASSWORD, "role": Role.CANDIDATE},
    # Extra candidates for realistic match data
    {"email": "priya.patel@example.com",   "password": "Priya@1234",   "role": Role.CANDIDATE},
    {"email": "marcus.johnson@example.com","password": "Marcus@1234",  "role": Role.CANDIDATE},
    {"email": "sarah.chen@example.com",    "password": "Sarah@1234",   "role": Role.CANDIDATE},
    {"email": "david.kim@example.com",     "password": "David@1234",   "role": Role.CANDIDATE},
    {"email": "alex.rodriguez@example.com","password": "Alex@1234",    "role": Role.CANDIDATE},
]

# ---------------------------------------------------------------------------
# Companies & Jobs  (posted by HR user)
# ---------------------------------------------------------------------------

SEED_COMPANIES_JOBS = [
    {
        "company": {
            "name": "Stripe",
            "website": "https://stripe.com",
            "description": "Stripe builds economic infrastructure for the internet.",
        },
        "jobs": [
            {
                "title": "Senior Frontend Engineer",
                "description": (
                    "Join Stripe's Dashboard team to build the web interfaces that millions of businesses "
                    "use to manage their payments. You will own large parts of our React/TypeScript frontend, "
                    "collaborate with product designers, and drive technical decisions around performance and "
                    "accessibility. We move fast and ship weekly — your work goes live to real users quickly."
                ),
                "required_skills": ["React", "TypeScript", "Next.js", "CSS", "GraphQL"],
                "min_experience": 4, "max_experience": 8,
                "min_salary": 160000, "max_salary": 220000,
                "location": "San Francisco, CA",
                "employment_type": EmploymentType.FULL_TIME,
            },
            {
                "title": "Data Engineer",
                "description": (
                    "Stripe processes hundreds of billions of dollars a year for businesses of all sizes. "
                    "As a Data Engineer you will design and maintain the pipelines that power our analytics "
                    "and fraud-detection systems. You will work with Python, Apache Spark, dbt, and our "
                    "internal data platform built on top of AWS."
                ),
                "required_skills": ["Python", "Apache Spark", "dbt", "SQL", "AWS", "Airflow"],
                "min_experience": 3, "max_experience": 6,
                "min_salary": 140000, "max_salary": 190000,
                "location": "Seattle, WA",
                "employment_type": EmploymentType.FULL_TIME,
            },
        ],
    },
    {
        "company": {
            "name": "Airbnb",
            "website": "https://airbnb.com",
            "description": "Airbnb creates a world where anyone can belong anywhere.",
        },
        "jobs": [
            {
                "title": "Full Stack Software Engineer",
                "description": (
                    "Work on Airbnb's core booking and search platform. Our stack is Python (Django/FastAPI) "
                    "on the backend and React on the frontend, backed by PostgreSQL and Elasticsearch. "
                    "You will design APIs, optimise slow queries, and build the features that guests and "
                    "hosts interact with every day."
                ),
                "required_skills": ["Python", "React", "PostgreSQL", "Django", "Elasticsearch", "Docker"],
                "min_experience": 3, "max_experience": 7,
                "min_salary": 150000, "max_salary": 210000,
                "location": "San Francisco, CA",
                "employment_type": EmploymentType.FULL_TIME,
            },
            {
                "title": "iOS Engineer",
                "description": (
                    "Build the Airbnb iOS app used by tens of millions of travellers worldwide. "
                    "You will implement new features using Swift and UIKit/SwiftUI, write robust unit "
                    "and UI tests, and partner closely with our design system team to ship pixel-perfect "
                    "experiences. Experience with Objective-C and performance profiling is a plus."
                ),
                "required_skills": ["Swift", "SwiftUI", "UIKit", "Xcode", "CocoaPods", "REST APIs"],
                "min_experience": 3, "max_experience": 7,
                "min_salary": 145000, "max_salary": 200000,
                "location": "San Francisco, CA",
                "employment_type": EmploymentType.FULL_TIME,
            },
        ],
    },
    {
        "company": {
            "name": "Anthropic",
            "website": "https://anthropic.com",
            "description": "Anthropic is an AI safety company working to build reliable, interpretable, and steerable AI systems.",
        },
        "jobs": [
            {
                "title": "Machine Learning Engineer",
                "description": (
                    "Join the team training and deploying large language models. You will implement "
                    "novel training techniques, write high-performance CUDA kernels, and work on "
                    "distributed training infrastructure across thousands of GPUs. Strong Python and "
                    "PyTorch skills are required; experience with JAX or Triton is a bonus."
                ),
                "required_skills": ["Python", "PyTorch", "CUDA", "Distributed Training", "Transformers", "Linux"],
                "min_experience": 4, "max_experience": 10,
                "min_salary": 200000, "max_salary": 350000,
                "location": "San Francisco, CA",
                "employment_type": EmploymentType.FULL_TIME,
            },
            {
                "title": "Security Engineer",
                "description": (
                    "Protect Anthropic's infrastructure and AI systems. You will conduct threat modelling, "
                    "lead penetration tests, build internal security tooling in Python and Go, and respond "
                    "to incidents. You will also work on model security — understanding and mitigating "
                    "adversarial inputs and prompt injection risks."
                ),
                "required_skills": ["Python", "Go", "Penetration Testing", "AWS Security", "Zero Trust", "Incident Response"],
                "min_experience": 5, "max_experience": 12,
                "min_salary": 180000, "max_salary": 280000,
                "location": "San Francisco, CA",
                "employment_type": EmploymentType.FULL_TIME,
            },
        ],
    },
    {
        "company": {
            "name": "Netflix",
            "website": "https://netflix.com",
            "description": "Netflix is the world's leading streaming entertainment service.",
        },
        "jobs": [
            {
                "title": "Platform Engineer",
                "description": (
                    "Netflix runs one of the world's largest microservices platforms. As a Platform Engineer "
                    "you will work on the infrastructure that underpins hundreds of services — building "
                    "internal tooling in Go, managing Kubernetes clusters, and improving the developer "
                    "experience for 2,000+ engineers. Experience with service meshes (Istio/Envoy) is a plus."
                ),
                "required_skills": ["Go", "Kubernetes", "Docker", "Terraform", "AWS", "gRPC"],
                "min_experience": 4, "max_experience": 9,
                "min_salary": 170000, "max_salary": 240000,
                "location": "Los Gatos, CA",
                "employment_type": EmploymentType.FULL_TIME,
            },
            {
                "title": "Backend Engineer — Streaming",
                "description": (
                    "Work on the systems that deliver video to 260 million subscribers globally. "
                    "Our backend is primarily Java and Kotlin, with heavy use of Apache Kafka for "
                    "event streaming and Cassandra for low-latency reads. You will optimise stream "
                    "startup times, implement adaptive bitrate logic, and design resilient services."
                ),
                "required_skills": ["Java", "Kotlin", "Apache Kafka", "Cassandra", "Microservices", "AWS"],
                "min_experience": 3, "max_experience": 8,
                "min_salary": 155000, "max_salary": 220000,
                "location": "Los Gatos, CA",
                "employment_type": EmploymentType.FULL_TIME,
            },
        ],
    },
    {
        "company": {
            "name": "Shopify",
            "website": "https://shopify.com",
            "description": "Shopify powers over a million businesses in more than 175 countries.",
        },
        "jobs": [
            {
                "title": "DevOps / Infrastructure Engineer",
                "description": (
                    "Shopify's infrastructure team keeps the platform running for millions of merchants "
                    "during peak events like Black Friday. You will manage Kubernetes clusters on GCP, "
                    "write Terraform modules, build GitOps pipelines, and improve our observability stack "
                    "(Prometheus, Grafana, OpenTelemetry)."
                ),
                "required_skills": ["Kubernetes", "Terraform", "GCP", "Docker", "Prometheus", "Grafana", "Python"],
                "min_experience": 3, "max_experience": 7,
                "min_salary": 130000, "max_salary": 180000,
                "location": "Remote",
                "employment_type": EmploymentType.FULL_TIME,
            },
            {
                "title": "React Native Engineer",
                "description": (
                    "Build Shopify's merchant mobile apps used by hundreds of thousands of business owners "
                    "to manage their stores on the go. Our app is built in React Native with TypeScript. "
                    "You will implement new commerce features, optimise app performance, and work closely "
                    "with our design and product teams."
                ),
                "required_skills": ["React Native", "TypeScript", "React", "iOS", "Android", "REST APIs"],
                "min_experience": 2, "max_experience": 6,
                "min_salary": 120000, "max_salary": 170000,
                "location": "Remote",
                "employment_type": EmploymentType.FULL_TIME,
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Candidate profiles
# ---------------------------------------------------------------------------

SEED_PROFILES = [
    {
        "email": settings.SEED_CANDIDATE_EMAIL,
        "full_name": "Alex Jordan",
        "headline": "Full Stack Engineer — React & Python",
        "location": "San Francisco, CA",
        "bio": "5 years building web products at early-stage startups. Strong in React and FastAPI. Passionate about developer tooling and clean APIs.",
        "years_experience": 5,
        "current_salary": 140000,
        "expected_salary": 170000,
        "notice_period_days": 30,
        "skills": ["React", "TypeScript", "Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "REST APIs"],
    },
    {
        "email": "priya.patel@example.com",
        "full_name": "Priya Patel",
        "headline": "Senior Frontend Engineer — React & Next.js",
        "location": "San Francisco, CA",
        "bio": "6 years of frontend engineering with a focus on design systems and performance. Led the migration of a SaaS product from Angular to Next.js. Comfortable with GraphQL and accessibility (WCAG 2.1).",
        "years_experience": 6,
        "current_salary": 155000,
        "expected_salary": 190000,
        "notice_period_days": 21,
        "skills": ["React", "Next.js", "TypeScript", "GraphQL", "CSS", "Figma", "Jest", "Accessibility"],
    },
    {
        "email": "marcus.johnson@example.com",
        "full_name": "Marcus Johnson",
        "headline": "Full Stack Engineer — Python & React",
        "location": "Austin, TX",
        "bio": "4 years building data-heavy applications at a fintech startup. Experience with Django and FastAPI on the backend, React on the frontend. Strong SQL skills and experience with data pipelines.",
        "years_experience": 4,
        "current_salary": 130000,
        "expected_salary": 155000,
        "notice_period_days": 14,
        "skills": ["Python", "Django", "React", "PostgreSQL", "SQL", "Elasticsearch", "Docker", "dbt"],
    },
    {
        "email": "sarah.chen@example.com",
        "full_name": "Sarah Chen",
        "headline": "ML Engineer — LLMs & Distributed Training",
        "location": "San Francisco, CA",
        "bio": "5 years in ML with the last 3 focused on large language models. Published researcher with work on efficient training and RLHF. Proficient in PyTorch and CUDA kernel optimisation.",
        "years_experience": 5,
        "current_salary": 190000,
        "expected_salary": 250000,
        "notice_period_days": 30,
        "skills": ["Python", "PyTorch", "CUDA", "Transformers", "Distributed Training", "Linux", "JAX", "RLHF"],
    },
    {
        "email": "david.kim@example.com",
        "full_name": "David Kim",
        "headline": "DevOps / Platform Engineer — Kubernetes & Terraform",
        "location": "Remote",
        "bio": "7 years in infrastructure and platform engineering. Managed multi-region Kubernetes clusters on AWS and GCP, built GitOps pipelines, and set up full observability stacks. AWS Certified Solutions Architect.",
        "years_experience": 7,
        "current_salary": 150000,
        "expected_salary": 175000,
        "notice_period_days": 30,
        "skills": ["Kubernetes", "Terraform", "Docker", "AWS", "GCP", "Prometheus", "Grafana", "Python", "Go"],
    },
    {
        "email": "alex.rodriguez@example.com",
        "full_name": "Alex Rodriguez",
        "headline": "Backend Engineer — Java & Kafka",
        "location": "Los Angeles, CA",
        "bio": "4 years building high-throughput backend services. Experience with event-driven architectures using Kafka and real-time data pipelines. Strong in Java and Kotlin with microservices on AWS.",
        "years_experience": 4,
        "current_salary": 135000,
        "expected_salary": 160000,
        "notice_period_days": 21,
        "skills": ["Java", "Kotlin", "Apache Kafka", "Microservices", "AWS", "Cassandra", "Spring Boot", "Docker"],
    },
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

async def _seed_users(session: AsyncSession) -> dict[str, User]:
    users: dict[str, User] = {}
    for spec in SEED_USERS:
        result = await session.execute(select(User).where(User.email == spec["email"]))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(spec["password"]),
                role=spec["role"],
                is_active=True,
            )
            session.add(user)
            await session.flush()
            logger.info("Seeded user: %s (%s)", spec["email"], spec["role"].value)
        else:
            logger.info("User exists, skipping: %s", spec["email"])
        users[spec["email"]] = user
    return users


async def _seed_jobs(session: AsyncSession, hr_user: User) -> None:
    for entry in SEED_COMPANIES_JOBS:
        # Upsert company
        result = await session.execute(
            select(Company).where(Company.name == entry["company"]["name"])
        )
        company = result.scalar_one_or_none()
        if company is None:
            company = Company(
                name=entry["company"]["name"],
                website=entry["company"].get("website"),
                description=entry["company"].get("description"),
                created_by_user_id=hr_user.id,
            )
            session.add(company)
            await session.flush()
            logger.info("Seeded company: %s", company.name)

        # Upsert jobs by title + company
        for jspec in entry["jobs"]:
            result = await session.execute(
                select(Job).where(Job.title == jspec["title"], Job.company_id == company.id)
            )
            job = result.scalar_one_or_none()
            if job is None:
                job = Job(
                    company_id=company.id,
                    posted_by_user_id=hr_user.id,
                    title=jspec["title"],
                    description=jspec["description"],
                    required_skills=jspec["required_skills"],
                    min_experience=jspec.get("min_experience"),
                    max_experience=jspec.get("max_experience"),
                    min_salary=jspec.get("min_salary"),
                    max_salary=jspec.get("max_salary"),
                    location=jspec.get("location"),
                    employment_type=jspec.get("employment_type", EmploymentType.FULL_TIME),
                    status=JobStatus.OPEN,
                )
                session.add(job)
                logger.info("Seeded job: %s @ %s", jspec["title"], company.name)


async def _seed_profiles(session: AsyncSession, users: dict[str, User]) -> None:
    for pspec in SEED_PROFILES:
        user = users.get(pspec["email"])
        if user is None:
            continue
        result = await session.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = CandidateProfile(
                user_id=user.id,
                full_name=pspec.get("full_name"),
                headline=pspec.get("headline"),
                location=pspec.get("location"),
                bio=pspec.get("bio"),
                years_experience=pspec.get("years_experience"),
                current_salary=pspec.get("current_salary"),
                expected_salary=pspec.get("expected_salary"),
                notice_period_days=pspec.get("notice_period_days"),
                skills=pspec.get("skills"),
            )
            session.add(profile)
            logger.info("Seeded profile: %s", pspec["full_name"])
        else:
            logger.info("Profile exists, skipping: %s", pspec["email"])


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        users = await _seed_users(session)
        await session.commit()

        hr_user = users[settings.SEED_HR_EMAIL]
        await _seed_jobs(session, hr_user)
        await session.commit()

        await _seed_profiles(session, users)
        await session.commit()

    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
