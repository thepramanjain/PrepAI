# PrepAI

**AI-Powered Mock Interview & Career Preparation Platform**

PrepAI is an intelligent interview preparation platform that uses AI to help users practice and improve their interview skills. It generates tailored questions, conducts mock interviews (text and voice), evaluates responses, and provides actionable feedback — all powered by Google Gemini.

---

## Project Overview

PrepAI helps job seekers prepare for interviews by:

- Generating role-specific interview questions using AI
- Conducting interactive text-based mock interviews
- Conducting voice-based mock interviews using LiveKit Agents
- Evaluating responses and providing detailed feedback
- Analyzing resumes to generate targeted questions
- Tracking performance over time with analytics
- Creating personalized preparation plans

---

## Features

| Feature                          | Status         |
| -------------------------------- | -------------- |
| User Registration & Login        | 🟡 Planned     |
| Create Personalized Interviews   | 🟡 Planned     |
| AI Question Generation (Gemini)  | 🟡 Planned     |
| Text-Based Mock Interviews       | 🟡 Planned     |
| Voice-Based Interviews (LiveKit) | 🟡 Planned     |
| Interview Transcript Storage     | 🟡 Planned     |
| AI-Powered Evaluation            | 🟡 Planned     |
| Scores & Recommendations         | 🟡 Planned     |
| Resume Analysis                  | 🟡 Planned     |
| Performance Analytics            | 🟡 Planned     |
| Personalized Preparation Plans   | 🟡 Planned     |
| Agentic AI Workflow (LangGraph)  | 🟡 Planned     |

> **Note:** No features are implemented yet. This is the initial project scaffold.

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
- **Motor / PyMongo** — MongoDB driver
- **JWT** — Authentication tokens
- **bcrypt / passlib** — Password hashing

### AI
- **Google Gemini API** — Question generation, evaluation, recommendations
- **Prompt Engineering** — Centralized prompt templates
- **LangGraph** — Agentic AI workflow (future)

### Voice
- **LiveKit Agents** — Real-time voice interviews
- **Gemini Live** — Real-time voice AI (future)

### Database
- **MongoDB** — Document database

### Resume Processing
- **PyMuPDF** — PDF parsing
- **python-docx** — DOCX parsing

### Development
- **Git & GitHub** — Version control
- **Postman** — API testing
- **Docker** — Containerization (optional)

---

## System Architecture

```
┌─────────────┐     REST API     ┌─────────────┐     ┌─────────────┐
│   Frontend   │ ◄──────────────► │   Backend   │ ◄──►│   MongoDB   │
│  (React +    │                  │  (FastAPI)   │     └─────────────┘
│   Vite)      │                  │              │
└─────────────┘                  │   ┌─────────┐│
                                  │   │ AI Layer ││◄──► Google Gemini API
                                  │   └─────────┘│
                                  └──────────────┘
                                         ▲
┌─────────────┐                          │
│ Voice Agent  │ ◄───────────────────────┘
│  (LiveKit)   │◄──► LiveKit Server
└─────────────┘
```

- **Frontend** communicates with **Backend** via REST APIs only.
- **Backend** handles authentication, database, AI orchestration, and interview logic.
- **Voice Agent** runs as a separate Python service.
- **AI prompts** are centralized in the `ai/` directory.
- All secrets are loaded from environment variables — never hardcoded.

---

## Project Structure

```
PrepAI/
├── frontend/           # React + Vite frontend application
├── backend/            # FastAPI backend application
├── voice-agent/        # LiveKit voice interview agent
├── ai/                 # Centralized AI prompts and schemas
├── docs/               # Project documentation
├── tests/              # Integration and E2E tests
├── .gitignore
├── .env.example        # Environment variable template
├── README.md           # This file
└── docker-compose.yml  # Docker services (future)
```

---

## Development Roadmap

### Phase 1 — Foundation
- [ ] React frontend scaffold with Vite + Tailwind
- [ ] FastAPI backend scaffold
- [ ] MongoDB connection
- [ ] Health check endpoint
- [ ] Basic project structure

### Phase 2 — Authentication
- [ ] User registration
- [ ] User login with JWT
- [ ] Protected routes (frontend + backend)
- [ ] Auth context & middleware

### Phase 3 — Interview System
- [ ] Create interview flow
- [ ] AI question generation with Gemini
- [ ] Text-based interview interface
- [ ] Response storage

### Phase 4 — Evaluation & Feedback
- [ ] AI-powered response evaluation
- [ ] Score generation
- [ ] Strengths, weaknesses, recommendations
- [ ] Feedback display UI

### Phase 5 — Resume Analysis
- [ ] Resume upload (PDF/DOCX)
- [ ] Resume text extraction
- [ ] AI-powered resume analysis
- [ ] Resume-specific question generation

### Phase 6 — Voice Interviews
- [ ] LiveKit Agent setup
- [ ] Voice interview flow
- [ ] Transcript generation
- [ ] Voice-to-text evaluation

### Phase 7 — Analytics & Dashboard
- [ ] Performance tracking
- [ ] Charts and visualizations
- [ ] Interview history
- [ ] Preparation plans

### Phase 8 — Advanced AI
- [ ] LangGraph agentic workflow
- [ ] Adaptive interviewer
- [ ] Multi-step reasoning
- [ ] Improved recommendation engine

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp .env.example .env
```

| Variable              | Description                        |
| --------------------- | ---------------------------------- |
| `MONGODB_URI`         | MongoDB connection string          |
| `JWT_SECRET`          | Secret key for JWT token signing   |
| `GEMINI_API_KEY`      | Google Gemini API key              |
| `GEMINI_MODEL`        | Gemini model name                  |
| `LIVEKIT_URL`         | LiveKit server URL                 |
| `LIVEKIT_API_KEY`     | LiveKit API key                    |
| `LIVEKIT_API_SECRET`  | LiveKit API secret                 |
| `FRONTEND_URL`        | Frontend URL (for CORS)            |
| `VITE_API_URL`        | Backend API URL (used by frontend) |
| `VITE_LIVEKIT_URL`    | LiveKit URL (used by frontend)     |

> ⚠️ **Never commit real API keys.** Only `.env.example` with empty placeholders is committed.

---

## Local Development

### Prerequisites
- Node.js 18+
- Python 3.10+
- MongoDB (local or Atlas free tier)
- Google Gemini API key (free tier)

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Voice Agent
```bash
cd voice-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python agent.py
```

---

## Future Enhancements

- 🟡 **LangGraph Integration** — Agentic AI workflow for adaptive interviews
- 🟡 **Multi-language Support** — Interviews in multiple languages
- 🟡 **Video Interviews** — Camera-based interview simulation
- 🟡 **Collaborative Interviews** — Panel interview simulation
- 🟡 **Job Board Integration** — Pull job descriptions for targeted prep
- 🟡 **Mobile App** — React Native or PWA
- 🟡 **Admin Dashboard** — Usage analytics and management

---

## License

This project is for educational and personal use.

---

*Built with ❤️ using React, FastAPI, Google Gemini, and LiveKit.*
