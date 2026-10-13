"""
Generate dummy resumes and job descriptions for testing.
Run once: python data_generator.py
"""

import json
import os

RESUMES_DIR = "data/resumes"
JD_DIR = "data/job_descriptions"

RESUMES = [
    {
        "id": "r001",
        "name": "Alice Chen",
        "email": "alice.chen@email.com",
        "phone": "+1-555-0101",
        "location": "San Francisco, CA",
        "years_experience": 5,
        "current_title": "Senior Frontend Developer",
        "summary": "Experienced frontend developer specialising in React and TypeScript. Led teams of 4 engineers, delivered high-traffic e-commerce platforms.",
        "skills": ["React", "TypeScript", "JavaScript", "HTML", "CSS", "Redux", "GraphQL", "Jest", "Webpack", "Node.js"],
        "education": [
            {"degree": "B.Sc. Computer Science", "institution": "UC Berkeley", "year": 2018}
        ],
        "experience": [
            {
                "title": "Senior Frontend Developer",
                "company": "ShopFast Inc.",
                "years": 3,
                "description": "Built and maintained React-based storefront serving 2M users. Reduced page load time by 40% through code splitting and lazy loading."
            },
            {
                "title": "Frontend Developer",
                "company": "StartupXYZ",
                "years": 2,
                "description": "Developed React dashboard for IoT data visualisation using D3.js and WebSockets."
            }
        ]
    },
    {
        "id": "r002",
        "name": "Bob Martinez",
        "email": "bob.martinez@email.com",
        "phone": "+1-555-0102",
        "location": "Austin, TX",
        "years_experience": 3,
        "current_title": "Full Stack Developer",
        "summary": "Full stack developer with strong React skills and backend experience in Python/Django.",
        "skills": ["React", "Python", "Django", "JavaScript", "PostgreSQL", "Docker", "REST APIs", "Git"],
        "education": [
            {"degree": "B.Sc. Software Engineering", "institution": "UT Austin", "year": 2020}
        ],
        "experience": [
            {
                "title": "Full Stack Developer",
                "company": "TechCorp",
                "years": 3,
                "description": "Built React frontend and Django REST API for a SaaS analytics platform."
            }
        ]
    },
    {
        "id": "r003",
        "name": "Carol Johnson",
        "email": "carol.j@email.com",
        "phone": "+1-555-0103",
        "location": "New York, NY",
        "years_experience": 7,
        "current_title": "Lead Frontend Engineer",
        "summary": "Lead frontend engineer with deep expertise in React, performance optimisation, and design systems. Mentored 6 junior developers.",
        "skills": ["React", "TypeScript", "JavaScript", "Next.js", "Tailwind CSS", "Storybook", "Cypress", "AWS", "CI/CD", "Redux Toolkit"],
        "education": [
            {"degree": "M.Sc. Computer Science", "institution": "Columbia University", "year": 2016}
        ],
        "experience": [
            {
                "title": "Lead Frontend Engineer",
                "company": "FinTech Solutions",
                "years": 4,
                "description": "Architected design system used across 5 product teams. Improved Core Web Vitals scores from 60 to 95."
            },
            {
                "title": "Frontend Developer",
                "company": "Media Group",
                "years": 3,
                "description": "Built React-based CMS and article rendering engine handling 10M page views daily."
            }
        ]
    },
    {
        "id": "r004",
        "name": "David Park",
        "email": "david.park@email.com",
        "phone": "+1-555-0104",
        "location": "Seattle, WA",
        "years_experience": 2,
        "current_title": "Junior Frontend Developer",
        "summary": "Junior developer with React knowledge gained through bootcamp and personal projects. Eager to grow in a production environment.",
        "skills": ["React", "JavaScript", "HTML", "CSS", "Git", "Bootstrap"],
        "education": [
            {"degree": "B.A. Information Technology", "institution": "Seattle Pacific University", "year": 2022}
        ],
        "experience": [
            {
                "title": "Junior Frontend Developer",
                "company": "WebAgency LLC",
                "years": 2,
                "description": "Developed marketing landing pages and small React applications for clients."
            }
        ]
    },
    {
        "id": "r005",
        "name": "Emily Rodriguez",
        "email": "emily.r@email.com",
        "phone": "+1-555-0105",
        "location": "Chicago, IL",
        "years_experience": 4,
        "current_title": "Data Scientist",
        "summary": "Data scientist with expertise in machine learning, Python, and NLP. Built models deployed to production serving millions of predictions daily.",
        "skills": ["Python", "scikit-learn", "TensorFlow", "PyTorch", "SQL", "Pandas", "NumPy", "NLP", "Spark", "Tableau"],
        "education": [
            {"degree": "M.Sc. Data Science", "institution": "University of Chicago", "year": 2019}
        ],
        "experience": [
            {
                "title": "Data Scientist",
                "company": "InsureTech Co.",
                "years": 4,
                "description": "Built fraud detection model reducing false positives by 30%. Developed NLP pipeline to classify customer complaints automatically."
            }
        ]
    },
    {
        "id": "r006",
        "name": "Frank Liu",
        "email": "frank.liu@email.com",
        "phone": "+1-555-0106",
        "location": "Boston, MA",
        "years_experience": 6,
        "current_title": "Senior Data Scientist",
        "summary": "Senior data scientist specialising in deep learning and computer vision. Published 3 research papers. Experienced with large-scale ML pipelines.",
        "skills": ["Python", "PyTorch", "TensorFlow", "Computer Vision", "MLflow", "Kubernetes", "SQL", "AWS SageMaker", "A/B Testing", "Feature Engineering"],
        "education": [
            {"degree": "Ph.D. Machine Learning", "institution": "MIT", "year": 2018}
        ],
        "experience": [
            {
                "title": "Senior Data Scientist",
                "company": "HealthAI",
                "years": 4,
                "description": "Led computer vision project for medical image analysis with 94% accuracy. Built MLflow-based experiment tracking platform."
            },
            {
                "title": "Data Scientist",
                "company": "AdTech Corp",
                "years": 2,
                "description": "Developed recommendation engine increasing click-through rate by 18%."
            }
        ]
    },
    {
        "id": "r007",
        "name": "Grace Kim",
        "email": "grace.kim@email.com",
        "phone": "+1-555-0107",
        "location": "Portland, OR",
        "years_experience": 5,
        "current_title": "Backend Python Engineer",
        "summary": "Backend engineer with strong Python and FastAPI experience. Built high-throughput microservices and designed scalable data pipelines.",
        "skills": ["Python", "FastAPI", "Django", "PostgreSQL", "Redis", "Celery", "Docker", "Kubernetes", "AWS", "RabbitMQ"],
        "education": [
            {"degree": "B.Sc. Computer Science", "institution": "Oregon State University", "year": 2019}
        ],
        "experience": [
            {
                "title": "Backend Python Engineer",
                "company": "LogiTech Startup",
                "years": 3,
                "description": "Built FastAPI microservices handling 50k requests/second. Designed async Celery pipeline for real-time logistics tracking."
            },
            {
                "title": "Python Developer",
                "company": "DataFlow Inc.",
                "years": 2,
                "description": "Developed Django REST API and ETL pipelines for financial data aggregation."
            }
        ]
    },
    {
        "id": "r008",
        "name": "Henry Patel",
        "email": "henry.patel@email.com",
        "phone": "+1-555-0108",
        "location": "Denver, CO",
        "years_experience": 8,
        "current_title": "Principal Backend Engineer",
        "summary": "Principal backend engineer with 8 years in Python. Expert in system design, database optimisation, and distributed systems.",
        "skills": ["Python", "Go", "PostgreSQL", "MongoDB", "Redis", "Kafka", "Docker", "AWS", "System Design", "gRPC"],
        "education": [
            {"degree": "B.Sc. Computer Engineering", "institution": "Colorado State University", "year": 2016}
        ],
        "experience": [
            {
                "title": "Principal Backend Engineer",
                "company": "CloudScale",
                "years": 5,
                "description": "Designed distributed event streaming platform processing 1B events/day using Kafka and Python. Reduced database query latency by 70%."
            },
            {
                "title": "Senior Backend Developer",
                "company": "E-Commerce Giant",
                "years": 3,
                "description": "Led backend for checkout service handling Black Friday peak of 50k transactions/minute."
            }
        ]
    },
    {
        "id": "r009",
        "name": "Irene Walsh",
        "email": "irene.walsh@email.com",
        "phone": "+1-555-0109",
        "location": "Miami, FL",
        "years_experience": 4,
        "current_title": "DevOps Engineer",
        "summary": "DevOps engineer experienced in CI/CD, infrastructure as code, and Kubernetes cluster management.",
        "skills": ["Kubernetes", "Docker", "Terraform", "AWS", "GitHub Actions", "Jenkins", "Python", "Bash", "Prometheus", "Grafana"],
        "education": [
            {"degree": "B.Sc. Information Systems", "institution": "Florida International University", "year": 2020}
        ],
        "experience": [
            {
                "title": "DevOps Engineer",
                "company": "CloudOps Ltd.",
                "years": 4,
                "description": "Managed Kubernetes clusters running 200+ microservices. Built Terraform modules for multi-region AWS deployments."
            }
        ]
    },
    {
        "id": "r010",
        "name": "James Thompson",
        "email": "james.t@email.com",
        "phone": "+1-555-0110",
        "location": "Los Angeles, CA",
        "years_experience": 6,
        "current_title": "Product Manager",
        "summary": "Product manager with a technical background, experienced in leading cross-functional teams and delivering B2B SaaS products.",
        "skills": ["Product Strategy", "Agile", "Scrum", "SQL", "Figma", "Jira", "A/B Testing", "Data Analysis", "Roadmap Planning", "Stakeholder Management"],
        "education": [
            {"degree": "MBA", "institution": "UCLA Anderson", "year": 2018},
            {"degree": "B.Sc. Computer Science", "institution": "USC", "year": 2016}
        ],
        "experience": [
            {
                "title": "Senior Product Manager",
                "company": "SaaS Platform Co.",
                "years": 4,
                "description": "Launched 3 major product features generating $2M ARR. Defined roadmap for API product serving 500 enterprise customers."
            },
            {
                "title": "Product Manager",
                "company": "Mobile App Startup",
                "years": 2,
                "description": "Grew user base from 10k to 250k through data-driven feature prioritisation."
            }
        ]
    }
]

JOB_DESCRIPTIONS = [
    {
        "filename": "senior_react_developer.json",
        "data": {
            "id": "jd001",
            "title": "Senior React Developer",
            "company": "TechVision Inc.",
            "location": "San Francisco, CA (Hybrid)",
            "salary_range": "$130,000 - $160,000",
            "text": """We are looking for a Senior React Developer to join our product team.

Role Overview:
You will lead frontend development for our core SaaS platform, mentor junior developers, and drive technical decisions.

Must-Have Requirements:
- 4+ years of experience with React
- Proficiency in TypeScript
- Experience with state management (Redux or similar)
- Strong JavaScript fundamentals
- Experience writing unit and integration tests (Jest, Cypress)
- Familiarity with CI/CD pipelines

Nice-to-Have:
- Experience with Next.js
- GraphQL knowledge
- Design system experience
- AWS or cloud deployment experience

Responsibilities:
- Build and maintain React components and application architecture
- Conduct code reviews and mentor junior team members
- Collaborate with design and backend teams
- Optimise application performance

We value candidates who have worked on high-traffic applications and have a track record of mentoring others."""
        }
    },
    {
        "filename": "data_scientist.json",
        "data": {
            "id": "jd002",
            "title": "Senior Data Scientist",
            "company": "DataDriven Labs",
            "location": "Boston, MA (Remote-friendly)",
            "salary_range": "$140,000 - $170,000",
            "text": """We're hiring a Senior Data Scientist to expand our AI/ML team.

Role Overview:
You will build and deploy machine learning models, design experiments, and communicate findings to stakeholders.

Must-Have Requirements:
- 4+ years of hands-on data science experience
- Strong Python skills (scikit-learn, Pandas, NumPy)
- Experience with deep learning frameworks (PyTorch or TensorFlow)
- SQL proficiency
- Ability to deploy models to production

Nice-to-Have:
- PhD or advanced degree in a quantitative field
- Experience with MLflow or similar experiment tracking
- NLP or computer vision specialisation
- Cloud ML platforms (AWS SageMaker, GCP Vertex AI)
- A/B testing experience

Responsibilities:
- Develop, train, and evaluate machine learning models
- Collaborate with engineering to deploy models at scale
- Design and analyse A/B tests
- Present findings to non-technical stakeholders"""
        }
    },
    {
        "filename": "backend_python_engineer.json",
        "data": {
            "id": "jd003",
            "title": "Senior Backend Python Engineer",
            "company": "ScaleUp Systems",
            "location": "Remote (US only)",
            "salary_range": "$125,000 - $155,000",
            "text": """We need a Senior Backend Python Engineer to build scalable services.

Role Overview:
Join our backend platform team to design and build high-performance Python services and APIs.

Must-Have Requirements:
- 4+ years of Python backend development
- Experience with FastAPI or Django REST Framework
- PostgreSQL or similar relational database experience
- Docker and containerisation
- Understanding of async programming in Python

Nice-to-Have:
- Kubernetes experience
- Message queue experience (Kafka, RabbitMQ, Celery)
- Redis or caching layer expertise
- AWS experience
- Go or another systems language

Responsibilities:
- Design and implement RESTful and gRPC APIs
- Optimise database queries and data access patterns
- Write comprehensive tests and documentation
- Participate in on-call rotations"""
        }
    }
]


def generate():
    os.makedirs(RESUMES_DIR, exist_ok=True)
    os.makedirs(JD_DIR, exist_ok=True)

    for resume in RESUMES:
        path = os.path.join(RESUMES_DIR, f"{resume['id']}.json")
        with open(path, "w") as f:
            json.dump(resume, f, indent=2)

    for jd in JOB_DESCRIPTIONS:
        path = os.path.join(JD_DIR, jd["filename"])
        with open(path, "w") as f:
            json.dump(jd["data"], f, indent=2)

    print(f"Generated {len(RESUMES)} resumes in {RESUMES_DIR}/")
    print(f"Generated {len(JOB_DESCRIPTIONS)} job descriptions in {JD_DIR}/")


if __name__ == "__main__":
    generate()
