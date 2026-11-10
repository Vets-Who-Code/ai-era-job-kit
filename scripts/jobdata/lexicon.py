"""Skill matching.

O*NET's Technology Skills list misses many tools that get people hired right
now (LangGraph, pgvector, evals, MCP ...). So matching uses two vocabularies:

  1. The occupation's own O*NET Technology Skills examples (pulled live).
  2. A curated, versioned list of current tools and practices below, with
     aliases. Posting frequency, not this list, decides how much each one
     matters: a term only scores when real postings ask for it.

Edit CURATED freely; it is plain data. Keep canonical names short.
"""

from __future__ import annotations

import re

CURATED: dict[str, list[str]] = {
    # languages
    "Python": ["python"], "TypeScript": ["typescript"], "JavaScript": ["javascript", "ecmascript"],
    "Go": ["golang", r"\bgo\b(?= (?:language|developer|engineer|services?))"],
    "Rust": ["rust"], "Java": [r"\bjava\b(?!script)"], "C#": ["c#", "csharp"], "SQL": [r"\bsql\b"],
    "Ruby": ["ruby"], "PHP": [r"\bphp\b"], "Kotlin": ["kotlin"], "Swift": [r"\bswift\b"],
    # web / app
    "React": ["react", "react.js", "reactjs"], "Next.js": ["next.js", "nextjs"],
    "Node.js": ["node.js", "nodejs", r"\bnode\b"], "Angular": ["angular"], "Vue": [r"\bvue\b", "vue.js"],
    "Tailwind CSS": ["tailwind"], "GraphQL": ["graphql"], "REST APIs": ["rest api", "restful", r"\brest\b"],
    "FastAPI": ["fastapi"], "Django": ["django"], "Flask": ["flask"], "Ruby on Rails": ["rails"],
    "Accessibility (WCAG)": ["accessibility", "wcag", "a11y"],
    # data
    "PostgreSQL": ["postgres", "postgresql"], "MySQL": ["mysql"], "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"], "Snowflake": ["snowflake"], "Databricks": ["databricks"], "dbt": [r"\bdbt\b"],
    "Apache Spark": ["spark", "pyspark"], "Apache Kafka": ["kafka"], "Airflow": ["airflow"],
    "BigQuery": ["bigquery"], "pandas": ["pandas"], "Data modeling": ["data model"],
    "ETL / ELT": [r"\betl\b", r"\belt\b", "data pipeline"],
    # AI engineering
    "LLMs": [r"\bllms?\b", "large language model"], "RAG": [r"\brag\b", "retrieval-augmented", "retrieval augmented"],
    "AI agents": ["agentic", "ai agent", r"\bagents\b"], "LangChain": ["langchain"], "LangGraph": ["langgraph"],
    "LlamaIndex": ["llamaindex", "llama index"], "Model Context Protocol (MCP)": [r"\bmcp\b", "model context protocol"],
    "Evals": [r"\bevals?\b", "llm evaluation", "evaluation framework"], "Prompt engineering": ["prompt engineering"],
    "Fine-tuning": ["fine-tun", "finetun", r"\blora\b"], "Vector databases": ["vector database", "vector store", "vector db"],
    "pgvector": ["pgvector"], "Embeddings": ["embedding"], "OpenAI API": ["openai"], "Anthropic API": ["anthropic", "claude"],
    "Gemini API": ["gemini"], "Hugging Face": ["hugging face", "huggingface"], "PyTorch": ["pytorch"],
    "TensorFlow": ["tensorflow"], "scikit-learn": ["scikit-learn", "sklearn"], "MLOps": ["mlops"],
    "LLM observability": ["langfuse", "langsmith", "arize", "llm observability"],
    "Guardrails / AI safety": ["guardrail", "red team", "responsible ai"],
    # cloud / platform
    "AWS": [r"\baws\b", "amazon web services"], "Azure": ["azure"], "Google Cloud": ["gcp", "google cloud"],
    "Docker": ["docker", "container"], "Kubernetes": ["kubernetes", r"\bk8s\b"], "Terraform": ["terraform"],
    "CI/CD": ["ci/cd", "continuous integration", "github actions", "gitlab ci", "jenkins"],
    "Linux": ["linux"], "Git": [r"\bgit\b", "github", "gitlab"], "Serverless": ["serverless", "lambda", "cloud run"],
    "Observability": ["observability", "opentelemetry", "datadog", "new relic", "prometheus", "grafana"],
    # practices
    "Testing": ["unit test", "integration test", "pytest", "jest", "playwright", "cypress", "test-driven", r"\btdd\b"],
    "System design": ["system design", "distributed system", "scalab"], "Microservices": ["microservice"],
    "Security": ["security", "owasp", "oauth", "authentication"], "Agile": ["agile", "scrum"],
}

_cache: dict[str, re.Pattern] = {}


def _pattern(term: str) -> re.Pattern:
    if term not in _cache:
        if any(ch in term for ch in r"\(?["):
            src = term  # already a regex
        else:
            src = r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])"
        _cache[term] = re.compile(src, re.I)
    return _cache[term]


def build_vocab(onet_skills: list[str] | None = None) -> dict[str, list[str]]:
    vocab = {k: list(v) for k, v in CURATED.items()}
    known = {k.lower() for k in vocab}
    for s in onet_skills or []:
        name = s.strip()
        if not name or name.lower() in known:
            continue
        # O*NET examples are product names ("Microsoft Azure software").
        core = re.sub(r"\b(software|platform|language|framework)\b", "", name, flags=re.I).strip(" ,")
        if len(core) >= 2:
            vocab[name] = [core.lower()]
            known.add(name.lower())
    return vocab


def find_skills(text: str, vocab: dict[str, list[str]]) -> set[str]:
    t = text.lower()
    return {canon for canon, aliases in vocab.items() if any(_pattern(a).search(t) for a in aliases)}


def count_in_docs(docs: list[str], vocab: dict[str, list[str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in docs:
        for s in find_skills(d, vocab):
            counts[s] = counts.get(s, 0) + 1
    return counts
