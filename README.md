# PrepAI

**AI-Powered Mock Interview & Career Preparation Platform**

PrepAI is an intelligent interview preparation platform that uses Agentic AI to help users practice and improve their interview skills. It generates tailored questions, conducts mock interviews (text and voice), evaluates responses, and provides actionable feedback — powered by a hybrid architecture of Google Gemini and a LangGraph + GPT-4o orchestrator.

---

## Project Overview

PrepAI helps job seekers prepare for interviews by:

- Generating role-specific interview questions using AI.
- Conducting interactive text-based mock interviews.
- Conducting voice-based mock interviews using LiveKit Agents.
- Evaluating responses and providing detailed feedback and scores.
- Analyzing resumes to generate targeted, personalized questions.
- Tracking performance over time with visual analytics.
- Using a team of LangGraph-powered specialized AI Agents (Coach, Interviewer, Evaluator, Analyst) for deep conversational insights.

---

## Features

| Phase | Feature                          | Status         |
| ----- | -------------------------------- | -------------- |
| 1     | Foundation & Setup               | 🟢 Completed   |
| 2     | User Registration & Login (JWT)  | 🟢 Completed   |
| 3     | Interview Management System      | 🟢 Completed   |
| 4     | Resume Upload & Parsing          | 🟢 Completed   |
| 5     | AI Question Generation (Gemini)  | 🟢 Completed   |
| 6     | Text-Based Mock Interviews       | 🟢 Completed   |
| 7     | AI-Powered Evaluation & Feedback | 🟢 Completed   |
| 8     | Performance Analytics & Charts   | 🟢 Completed   |
| 9     | Voice-Based Interviews (LiveKit) | 🟢 Completed   |
| 10    | Agentic AI Workflow (LangGraph)  | 🟢 Completed   |

---

## Technology Stack

### Frontend
- **React** — UI library
- **Vite** — Build tool & dev server
- **Tailwind CSS** — Utility-first CSS framework
- **shadcn/ui** — Accessible component primitives
- **React Router** — Client-side routing
- **Axios** — HTTP client
- **Recharts** — Charting library

### Backend
- **Python** — Server language
- **FastAPI** — Web framework
- **Pydantic** — Data validation
- **Motor / PyMongo** — Asynchronous MongoDB driver
- **JWT** — Authentication tokens
- **bcrypt / passlib** — Password hashing

### AI & Agents (The Brain)
- **LangGraph** — Agentic AI orchestrator for multi-agent workflows
- **OpenRouter (GPT-4o)** — Core intelligence for LangGraph specialized agents
- **Google Gemini API** — Core generation, fast evaluation, and recommendations
- **Prompt Engineering** — Centralized instruction sets for specialized agents

### Voice
- **LiveKit Agents** — Real-time voice interviews
- **Silero VAD / Deepgram** — Speech-to-Text & Voice Activity Detection integration (via LiveKit)

### Database
- **MongoDB** — NoSQL Document database

### Resume Processing
- **PyMuPDF / pdfminer** — PDF text extraction
- **python-docx** — DOCX parsing

---

## System Architecture

```text
┌─────────────┐     REST API     ┌────────────────────────┐     ┌─────────────┐
│   Frontend   │ ◄──────────────► │        Backend         │ ◄──►│   MongoDB   │
│  (React +    │                  │       (FastAPI)        │     └─────────────┘
│   Vite)      │                  │                        │
└─────────────┘                  │  ┌──────────────────┐  │
                                  │  │ LangGraph AI     │  │◄──► OpenRouter (GPT-4o)
                                  │  │ Orchestrator     │  │
                                  │  └──────────────────┘  │
                                  │           ▲            │
                                  │           │            │
                                  │  ┌──────────────────┐  │
                                  │  │ Legacy AI Layer  │  │◄──► Google Gemini API
                                  │  └──────────────────┘  │
                                  └────────────────────────┘
                                          ▲
┌─────────────┐                           │
│ Voice Agent  │ ◄────────────────────────┘
│  (LiveKit)   │◄──► LiveKit Server
└─────────────┘
```

- **Frontend** communicates with **Backend** via REST APIs.
- **Backend** handles authentication, database connections, Agentic AI orchestration, and tool execution.
- **Agentic Layer (Phase 10)** uses LangGraph to route queries between specialized agents (Interviewer, Coach, Evaluator, Analyst) which securely invoke backend tools using the authenticated user's context.
- **Voice Agent** runs as a separate Python service connecting to LiveKit.
- All secrets are loaded from environment variables and are never hardcoded.

---

## Project Structure

```text
PrepAI/
├── frontend/           # React + Vite frontend application
├── backend/            # FastAPI backend application
│   ├── app/
│   │   ├── agents/     # LangGraph specialized agents (Coach, Evaluator, etc.)
│   │   ├── graph/      # LangGraph state and workflow compilation
│   │   ├── tools/      # Tool registry for Agentic AI
│   │   ├── ai/         # Gemini and OpenRouter integrations
│   │   ├── routes/     # FastAPI endpoint routers
│   │   ├── models/     # MongoDB data models
│   │   └── schemas/    # Pydantic validation schemas
│   └── tests/          # Pytest backend tests
├── voice-agent/        # LiveKit voice interview agent
├── ai/                 # Centralized AI prompts and templates
├── docs/               # Detailed project documentation
├── .gitignore
├── .env.example        # Environment variable template
├── README.md           # This file
└── docker-compose.yml  # Docker services
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values for each respective component.

| Variable              | Description                        |
| --------------------- | ---------------------------------- |
| `MONGODB_URI`         | MongoDB connection string          |
| `JWT_SECRET`          | Secret key for JWT token signing   |
| `GEMINI_API_KEY`      | Google Gemini API key              |
| `OPENROUTER_API_KEY`  | OpenRouter API key (GPT-4o)        |
| `LIVEKIT_URL`         | LiveKit server URL                 |
| `LIVEKIT_API_KEY`     | LiveKit API key                    |
| `LIVEKIT_API_SECRET`  | LiveKit API secret                 |
| `FRONTEND_URL`        | Frontend URL (for CORS)            |

> ⚠️ **Security Note:** Never commit `.env` files. OpenRouter and Gemini API keys must remain strictly on the backend and are never exposed to the frontend.

---

## Local Development

### Prerequisites
- Node.js 18+
- Python 3.10+
- MongoDB (local or Atlas free tier)
- OpenRouter API key
- Google Gemini API key
- LiveKit Cloud account (or local server)

### 1. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 3. Voice Agent
```bash
cd voice-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python agent.py start
```

---

## Testing

The backend comes with an extensive test suite (50+ tests passing) using `pytest`.

```bash
cd backend
python -m pytest tests/ -v
```

---

## License

This project is for educational and personal use.

---

*Built with ❤️ using React, FastAPI, LangGraph, Google Gemini, OpenRouter, and LiveKit.*
