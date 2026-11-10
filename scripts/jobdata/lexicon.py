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
    "Go": ["golang", r"\bgo\b(?= (?:language|developer|engineer|services?))", r"(?-i:\bGo\b)(?=\s*[,/|;)])"],
    "Rust": [r"\brust\b(?! (?:removal|prevention|proofing|repair))"], "Java": [r"\bjava\b(?!script)"], "C#": ["c#", "csharp"], "SQL": [r"\bsql\b"],
    "Ruby": ["ruby"], "PHP": [r"\bphp\b"], "Kotlin": ["kotlin"], "Swift": [r"(?-i:\bSwift\b)(?! (?:delivery|response|resolution|action|turnaround))", "swiftui"],
    "C++": ["c++"], "HTML": ["html", "html5"], "CSS": ["css", "css3"], ".NET": [r"(?<![a-z0-9])\.net\b", "dotnet", "asp.net"],
    # web / app
    "React": [r"(?-i:\bReact\b)", "react.js", "reactjs", r"\breact\b(?=\s*(?:[,/|;)]|native|hooks?|components?|apps?))"], "Next.js": ["next.js", "nextjs"],
    "Node.js": ["node.js", "nodejs", r"(?-i:\bNode\b)", r"\bnode\b(?=\s*[,/|;)])"], "Angular": ["angular"], "Vue": [r"\bvue\b", "vue.js"],
    "Tailwind CSS": ["tailwind"], "GraphQL": ["graphql"], "REST APIs": ["rest api", "restful", r"(?-i:\bREST\b)"],
    "FastAPI": ["fastapi"], "Django": ["django"], "Flask": ["flask"], "Ruby on Rails": ["rails"],
    "Accessibility (WCAG)": ["accessibility", "wcag", "a11y"],
    # data
    "PostgreSQL": ["postgres", "postgresql"], "MySQL": ["mysql"], "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"], "Snowflake": ["snowflake"], "Databricks": ["databricks"], "dbt": [r"\bdbt\b"],
    "Apache Spark": ["apache spark", "pyspark", r"(?-i:\bSpark\b)", "spark sql", "spark streaming"], "Apache Kafka": ["kafka"], "Airflow": ["airflow"],
    "BigQuery": ["bigquery"], "pandas": ["pandas"], "Data modeling": ["data model"],
    "ETL / ELT": [r"\betl\b", r"\belt\b", "data pipeline"],
    # AI engineering
    "LLMs": [r"\bllms?\b", "large language model"], "RAG": [r"\brag\b", "retrieval-augmented", "retrieval augmented"],
    "AI agents": ["agentic", "ai agent", "ai agents", "llm agent", "llm agents", "multi-agent", "autonomous agent",
                  "autonomous agents", r"\bagents?\b(?= (?:sdk|framework|orchestration|workflows?))"], "LangChain": ["langchain"], "LangGraph": ["langgraph"],
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
    "Docker": ["docker", r"containeri[sz]", r"\bcontainers?\b(?= (?:orchestration|images?|registry|runtime))"], "Kubernetes": ["kubernetes", r"\bk8s\b"], "Terraform": ["terraform"],
    "CI/CD": ["ci/cd", "continuous integration", "github actions", "gitlab ci", "jenkins"],
    "Linux": ["linux"], "Git": [r"\bgit\b", r"(?<![/.@\w])git(?:hub|lab)\b(?!\.(?:com|io)| actions| ci)"],
    "Serverless": ["serverless", "aws lambda", r"(?-i:\bLambda\b)", "cloud run", "cloud functions"],
    "Observability": ["observability", "opentelemetry", "datadog", "new relic", "prometheus", "grafana"],
    # practices
    "Testing": [r"\b(?:unit|integration|automated|end-to-end|e2e|regression)(?: (?:and|or) \w+)? test(?:s|ing)?\b", "pytest", "jest", "playwright", "cypress", "test-driven", r"\btdd\b"],
    "System design": ["system design", "systems design", "distributed system"], "Microservices": ["microservice"],
    "Security": [r"(?<!social )(?<!secret )\bsecurity\b(?! (?:clearance|forces|guard|officer|police|deposit|number))",
                 "owasp", "oauth", "authentication"], "Agile": ["agile", "scrum"], "Jira": ["jira"], "NoSQL": ["nosql"], "XML": [r"\bxml\b"],
    "Spring": ["spring boot", "spring framework", r"(?-i:\bSpring\b)(?= (?:mvc|cloud|security|data))"],
}

# O*NET examples lead with the vendor ("Atlassian JIRA", "Microsoft Azure software"); resumes don't.
_VENDORS = r"^(?:microsoft|atlassian|apache|oracle|amazon|google|ibm|adobe|red hat|the)\s+"
# A quantity, not a digit inside a name: "40%", "10,000", "$2M", "3x" count; "S3", "EC2", "OAuth2", "24/7" don't.
_NUMBER = re.compile(r"(?<![\w.#/-])\$?\d[\d,]*(?:\.\d+)?(?:%|\+|x|k|m|b|ms|s|gb|mb|tb)?(?![\w/])", re.I)


def has_number(text: str) -> bool:
    return bool(_NUMBER.search(text or ""))

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
            aliases = [core.lower()]
            short = re.sub(_VENDORS, "", core, flags=re.I).strip()
            if len(short) >= 3 and short.lower() != core.lower():
                aliases.append(short.lower())
            # "Extensible markup language XML": the trailing acronym is what people write
            m = re.search(r"\s([A-Z][A-Z0-9+#.]{1,})$", core)
            if m and " " in core:
                aliases.append(m.group(1).lower())
            vocab[name] = aliases
            known.add(name.lower())
    return vocab


def find_skills(text: str, vocab: dict[str, list[str]]) -> set[str]:
    # Search the text as written: a few aliases are case-sensitive ("REST", "Go", "React")
    return {canon for canon, aliases in vocab.items() if any(_pattern(a).search(text) for a in aliases)}


def count_in_docs(docs: list[str], vocab: dict[str, list[str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for d in docs:
        for s in find_skills(d, vocab):
            counts[s] = counts.get(s, 0) + 1
    return counts
