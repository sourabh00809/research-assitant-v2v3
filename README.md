---
title: Research Assistant
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
---

# Research Assistant

Citation-grounded research intelligence platform. Ask a research question, and the platform runs autonomous agents to search, rank, extract evidence, critique methodologies, and produce a structured research brief.

**Live site:** [https://sourabh00809-research-assistant.hf.space](https://sourabh00809-research-assistant.hf.space)

## Tech Stack

- **Frontend:** Next.js 14 (App Router), Clerk auth, Tailwind CSS
- **Backend:** FastAPI, PostgreSQL (Supabase), Redis, Celery
- **AI:** Groq, Tavily search, HuggingFace embeddings, sentence-transformers
- **Infrastructure:** Docker, Caddy reverse proxy, Hugging Face Spaces

## Features

- Autonomous literature search and evidence extraction
- Citation-grounded research briefs with Markdown and TeX export
- Structured evidence panels and methodology comparison matrices
- Baseline critique and statistical validation
- Experiment planning with domain-specific templates
- Persistent research memory with tagged manual capture
- Research graph connecting questions, briefs, evidence, and plans
- Source library with PDF upload and ingestion
- Multi-user support with role-based access (admin/user)
- Email notifications for agent approvals and run completion
