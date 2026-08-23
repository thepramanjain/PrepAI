# AI Prompts & Schemas

Centralized directory for all AI prompt templates and structured output schemas used across the PrepAI platform.

## Structure

```
ai/
├── prompts/          # Prompt templates for Gemini
│   ├── question_generation.txt
│   ├── interview_system.txt
│   ├── follow_up_question.txt
│   ├── evaluation.txt
│   ├── resume_analysis.txt
│   └── recommendation.txt
│
├── schemas/          # JSON schemas for structured AI output
│   ├── question_schema.json
│   ├── evaluation_schema.json
│   └── recommendation_schema.json
│
└── README.md
```

## Usage

- **Prompts** are loaded by `backend/app/utils/prompts.py` and used by the AI layer.
- **Schemas** define the expected JSON structure of AI responses for type safety.
- Keep prompts version-controlled for reproducibility.

## Status

🟡 **Planned** — Placeholder templates only. Production prompts will be written during implementation.
